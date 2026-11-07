import pytest

from parser import collect, replay
from utils.archive import read_json
from utils.extract import LIST_ID, TABS_ID
from utils.site import DETAIL_URL, LIST_URL, TRACKING_URL

REDIRECT = '<partial-response><changes><update id="j_id1:javax.faces.ViewState:0"><![CDATA[next]]></update></changes><redirect url="/remaju"/></partial-response>'
EMPTY_PAGE = f'<partial-response><changes><update id="{LIST_ID}"><![CDATA[]]></update></changes></partial-response>'
TRACKING_HTML = """<html><body><form id="formSeguimiento" name="formSeguimiento">
<input type="hidden" name="formSeguimiento" value="formSeguimiento"/>
<input type="hidden" name="javax.faces.ViewState" value="tracking"/>
<h3>Detalle de seguimiento</h3>
<div class="ui-g"><div class="text-bold">N° Expediente</div><div>15700-2023</div></div>
<div id="formSeguimiento:dgListaConvocatoria_content"><div class="card gris">
<div class="ui-g"><div class="text-bold">N° Convocatoria</div><div>PRIMERA</div></div>
<div class="ui-g"><div class="text-bold">Fecha de registro</div><div>01/02/2026</div></div>
</div></div>
<button id="formSeguimiento:j_idt40" type="submit"><span>Regresar</span></button>
</form></body></html>"""


class Response:
    status_code = 200

    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self) -> None:
        pass


class Source:
    def __init__(self, list_html, list_xml, detail_html, inmuebles_xml, cronograma_xml, broken: set[str] = frozenset()):
        self.pages = {"list": list_html, "page": list_xml, "detail": detail_html, "inmuebles": inmuebles_xml, "cronograma": cronograma_xml}
        self.broken = broken
        self.calls: list[tuple[str, str, str]] = []
        self.selected = ""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def request(self, method, url, data=None, **kwargs):
        source = (data or {}).get("javax.faces.source", "")
        self.calls.append((method, url, source))
        return Response(self.respond(method, url, data or {}, source))

    def respond(self, method: str, url: str, data: dict[str, str], source: str) -> str:
        if method == "GET":
            if url == LIST_URL:
                return self.pages["list"]
            if url == DETAIL_URL:
                return "<html><form id='formInicio'></form></html>" if self.selected in self.broken else self.pages["detail"]
            return TRACKING_HTML
        if source == LIST_ID:
            return self.pages["page"] if data[f"{LIST_ID}_first"] == "0" else EMPTY_PAGE
        if source == TABS_ID:
            return self.pages["inmuebles" if data[f"{TABS_ID}_newTab"].endswith("tbInmuebles") else "cronograma"]
        if url == LIST_URL:
            self.selected = source
        return REDIRECT


@pytest.fixture
def source(list_html, list_xml, detail_html, inmuebles_xml, cronograma_xml):
    return Source(list_html, list_xml, detail_html, inmuebles_xml, cronograma_xml)


def test_sample_walks_listing_details_tabs_and_tracking(tmp_path, source):
    report = collect(tmp_path, "sample", source, lambda: None)
    run_dir = tmp_path / report["run_id"]
    auctions = read_json(run_dir / "auctions.json")
    assert report["status"] == "partial"
    assert report["count"] == 4
    assert report["advertised_total"] == 197
    assert report["pages_complete"] is False
    assert report["details_complete"] is True
    assert read_json(run_dir / "run.json") == report
    assert [auction["numero_remate"] for auction in auctions] == ["22096", "22095", "22094", "22093"]
    assert auctions[0]["detail"]["remate_tab"]["expediente"] == "15700-2023-0-1817-JR-CO-07"
    assert len(auctions[0]["detail"]["cronograma_tab"]["fases"]) == 5
    assert auctions[0]["seguimiento"]["eventos"][0]["nro_convocatoria"] == "PRIMERA"
    first_auction = [(method, url.rsplit("/", 1)[-1], action) for method, url, action in source.calls[:10]]
    assert first_auction == [
        ("GET", "remateExterno.xhtml", ""),
        ("POST", "remateExterno.xhtml", LIST_ID),
        ("POST", "remateExterno.xhtml", "formBuscarRemateExterno:listaRemate:0:j_idt169"),
        ("GET", "mostrarDetalleRemate.xhtml", ""),
        ("POST", "mostrarDetalleRemate.xhtml", TABS_ID),
        ("POST", "mostrarDetalleRemate.xhtml", TABS_ID),
        ("POST", "mostrarDetalleRemate.xhtml", "formDetalleRemate:j_idt171"),
        ("POST", "remateExterno.xhtml", "formBuscarRemateExterno:listaRemate:0:j_idt168"),
        ("GET", "mostrarSeguimientoRemate.xhtml", ""),
        ("POST", "mostrarSeguimientoRemate.xhtml", "formSeguimiento:j_idt40"),
    ]


def test_live_run_stops_at_empty_page(tmp_path, source):
    report = collect(tmp_path, "live", source, lambda: None)
    assert report["pages_complete"] is True
    assert report["status"] == "complete"
    assert report["scope"] == "all-phases"


def test_failed_detail_is_recorded_and_collection_continues(tmp_path, list_html, list_xml, detail_html, inmuebles_xml, cronograma_xml):
    broken = Source(list_html, list_xml, detail_html, inmuebles_xml, cronograma_xml, {"formBuscarRemateExterno:listaRemate:1:j_idt169"})
    report = collect(tmp_path, "live", broken, lambda: None)
    assert report["status"] == "partial"
    assert report["details_complete"] is False
    assert [failure["numero_remate"] for failure in report["failures"]] == ["22095"]
    assert report["count"] == 3


def test_challenge_fails_run_without_auctions(tmp_path):
    class Blocked(Source):
        def respond(self, *args):
            return "<div class='h-captcha'></div>"

    report = collect(tmp_path, "sample", Blocked("", "", "", "", ""), lambda: None)
    assert report["status"] == "failed"
    assert not (tmp_path / report["run_id"] / "auctions.json").exists()


def test_replay_fixture_is_not_publishable(sample_data_dir):
    result = replay(sample_data_dir)
    assert result["count"] == 4
    assert result["publishable"] is False
    assert result["auctions"][0]["numero_remate"] == "22096"


def test_replay_rejects_missing_update(tmp_path):
    (tmp_path / "page1_list.xml").write_text("<partial-response><changes/></partial-response>")
    with pytest.raises(ValueError, match="listing update"):
        replay(tmp_path)
