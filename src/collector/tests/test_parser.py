import re
from dataclasses import replace

import pytest
import requests

from parser import collect, replay
from utils.archive import read_json, write_json
from utils.debugger import Trace
from utils.extract import LIST_ID, TABS_ID, cards, list_cards
from utils.jsf import VIEW_STATE, form_session
from utils.site import DETAIL_URL, LIST_FORM, LIST_URL, TRACKING_URL, RemajuSite
from utils.publication import publish_run

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


def redirect(url: str) -> str:
    return f'<partial-response><redirect url="{url}"/></partial-response>'


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
            return redirect(DETAIL_URL if source.endswith("j_idt169") else TRACKING_URL)
        return redirect(LIST_URL)


class StatefulSource(Source):
    def __init__(self, *args):
        super().__init__(*args)
        self.revision = 0
        self.expected_state = ""
        self.actions: dict[str, str] = {}
        self.pagination: list[tuple[int, int]] = []
        self.inserted = 0
        self.total: int | None = None

    def respond(self, method: str, url: str, data: dict[str, str], source: str) -> str:
        if method == "GET" and url == LIST_URL:
            self.revision += 1
            self.expected_state = f"listing-{self.revision}"
            self.actions = {}
            html = self.pages["list"]
            return html.replace(form_session(html, LIST_FORM).state, self.expected_state)
        if method == "POST" and url == LIST_URL:
            assert data[VIEW_STATE] == self.expected_state
            if source == LIST_ID:
                first, rows = int(data[f"{LIST_ID}_first"]), int(data[f"{LIST_ID}_rows"])
                self.pagination.append((first, rows))
                self.expected_state = f"listing-{self.revision}-page-{first}"
                templates = list_cards(self.pages["page"])
                numbers = [card.listing.numero_remate for card in cards(self.pages["page"])]
                content = []
                for index in range(rows if self.total is None else min(rows, self.total - first)):
                    offset = first + index - self.inserted
                    template = offset % len(templates)
                    html = templates[template].html.replace(numbers[template], str(int(numbers[0]) - offset))
                    html = re.sub(rf"{LIST_ID}:\d+:", f"{LIST_ID}:{first + index}:", html)
                    html = html.replace("j_idt169", f"j_idt{self.revision}169").replace("j_idt168", f"j_idt{self.revision}168")
                    content.append(html)
                xml = f'<partial-response><changes><update id="{LIST_ID}"><![CDATA[{"".join(content)}]]></update><update id="{VIEW_STATE}">{self.expected_state}</update></changes></partial-response>'
                self.actions = {card.detail_id: DETAIL_URL for card in cards(xml)}
                self.actions.update({card.tracking_id: TRACKING_URL for card in cards(xml) if card.tracking_id})
                return xml
            assert source in self.actions
            self.selected = source
            return redirect(self.actions[source])
        if method == "POST" and url in {DETAIL_URL, TRACKING_URL} and source != TABS_ID:
            self.expected_state = ""
            self.actions = {}
        return super().respond(method, url, data, source)


@pytest.fixture
def source(list_html, list_xml, detail_html, inmuebles_xml, cronograma_xml):
    return Source(list_html, list_xml, detail_html, inmuebles_xml, cronograma_xml)


@pytest.fixture
def stateful_source(list_html, list_xml, detail_html, inmuebles_xml, cronograma_xml):
    return StatefulSource(list_html, list_xml, detail_html, inmuebles_xml, cronograma_xml)


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
    first_auction = [(method, url.rsplit("/", 1)[-1], action) for method, url, action in source.calls[:14]]
    assert first_auction == [
        ("GET", "remateExterno.xhtml", ""),
        ("POST", "remateExterno.xhtml", LIST_ID),
        ("POST", "remateExterno.xhtml", "formBuscarRemateExterno:listaRemate:0:j_idt169"),
        ("GET", "mostrarDetalleRemate.xhtml", ""),
        ("POST", "mostrarDetalleRemate.xhtml", TABS_ID),
        ("POST", "mostrarDetalleRemate.xhtml", TABS_ID),
        ("POST", "mostrarDetalleRemate.xhtml", "formDetalleRemate:j_idt171"),
        ("GET", "remateExterno.xhtml", ""),
        ("POST", "remateExterno.xhtml", LIST_ID),
        ("POST", "remateExterno.xhtml", "formBuscarRemateExterno:listaRemate:0:j_idt168"),
        ("GET", "mostrarSeguimientoRemate.xhtml", ""),
        ("POST", "mostrarSeguimientoRemate.xhtml", "formSeguimiento:j_idt40"),
        ("GET", "remateExterno.xhtml", ""),
        ("POST", "remateExterno.xhtml", LIST_ID),
    ]


def test_live_run_stops_at_empty_page(tmp_path, source):
    report = collect(tmp_path, "live", source, lambda: None)
    assert report["pages_complete"] is True
    assert report["status"] == "partial"
    assert report["scope"] == "all-phases"


def test_live_run_with_page_limit_is_partial(tmp_path, source):
    report = collect(tmp_path, "live", source, lambda: None, max_pages=1)
    assert report["count"] == 4
    assert report["max_pages"] == 1
    assert report["scope"] == "partial"
    assert report["status"] == "partial"


def test_failed_detail_stops_collection_and_preserves_progress(tmp_path, list_html, list_xml, detail_html, inmuebles_xml, cronograma_xml, capsys):
    broken = Source(list_html, list_xml, detail_html, inmuebles_xml, cronograma_xml, {"formBuscarRemateExterno:listaRemate:1:j_idt169"})
    report = collect(tmp_path, "live", broken, lambda: None)
    assert report["status"] == "failed"
    assert report["details_complete"] is False
    assert [failure["numero_remate"] for failure in report["failures"]] == ["22095"]
    assert report["count"] == 1
    assert report["stop_reason"] == "collection-error"
    assert report["pages_complete"] is False
    assert report["error"]["response"]["action"] == "detail-page"
    run_dir = tmp_path / report["run_id"]
    assert read_json(run_dir / "run.json") == report
    assert len(read_json(run_dir / "auctions.json")) == 1
    assert (run_dir / "ids.txt").read_text().splitlines() == ["22096", "22095"]
    assert broken.calls[-1] == ("GET", DETAIL_URL, "")
    assert sum(url == LIST_URL and method == "GET" for method, url, _ in broken.calls) == 3
    assert "22095" in capsys.readouterr().err


@pytest.mark.parametrize("kind", ["redirect", "challenge", "timeout", "http-error"])
def test_request_error_stops_without_recovery_and_preserves_baseline(tmp_path, source, monkeypatch, kind):
    monkeypatch.setattr("utils.site.advertised_total", lambda _: 4)
    cache = tmp_path / "cache"
    collect(tmp_path / "runs", "live", source, lambda: None, cache_dir=cache)
    baseline = {path.name: path.read_bytes() for path in cache.iterdir()}
    original = source.request
    source.calls.clear()

    def fail(method, url, **kwargs):
        if method == "GET" and url == DETAIL_URL:
            source.calls.append((method, url, ""))
            if kind == "timeout":
                raise requests.Timeout("Source timed out")
            response = requests.Response()
            response.status_code = {"redirect": 302, "challenge": 200, "http-error": 503}[kind]
            response.headers["Location"] = "/challenge;jsessionid=secret?token=secret"
            response.headers["Content-Type"] = "text/html"
            response._content = b'<div class="h-captcha"></div>' if kind == "challenge" else b"Source response"
            return response
        return original(method, url, **kwargs)

    source.request = fail
    report = collect(tmp_path / "runs", "live", source, lambda: None, cache_dir=cache, cache_max_age_hours=0)
    assert report["status"] == "failed"
    assert report["count"] == 0
    assert report["details_complete"] is False
    assert len(report["failures"]) == 1
    assert report["failures"][0]["numero_remate"] == "22096"
    assert source.calls[-1] == ("GET", DETAIL_URL, "")
    assert len(source.calls) == 4
    assert {path.name: path.read_bytes() for path in cache.iterdir()} == baseline
    run_dir = tmp_path / "runs" / report["run_id"]
    assert read_json(run_dir / "run.json") == report
    assert '"state": "failed"' in (run_dir / "events.jsonl").read_text()
    response = report["error"]["response"]
    if kind == "timeout":
        assert response is None
    else:
        assert response["challenge_detected"] is (kind == "challenge")
        assert "secret" not in response["location"]
        assert (run_dir / response["body_file"]).is_file()


def test_listing_error_retains_a_failed_run_report(tmp_path, source):
    source.pages["page"] = "invalid XML"
    report = collect(tmp_path, "live", source, lambda: None)
    assert report["status"] == "failed"
    assert report["count"] == 0
    assert report["error"]["response"]["action"] == "list-page"
    assert len(source.calls) == 2


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


def test_complete_run_creates_baseline_and_reuses_details(tmp_path, source, monkeypatch):
    monkeypatch.setattr("utils.site.advertised_total", lambda _: 4)
    cache = tmp_path / "cache"
    first = collect(tmp_path / "runs", "live", source, lambda: None, cache_dir=cache)
    assert first["status"] == "complete"
    assert first["details_fetched"] == 4
    numbers = (cache / "ids.txt").read_text().splitlines()
    assert numbers == ["22096", "22095", "22094", "22093"]
    source.calls.clear()
    second = collect(tmp_path / "runs", "live", source, lambda: None, cache_dir=cache)
    assert second["status"] == "complete"
    assert second["details_reused"] == 4
    assert second["details_fetched"] == 0
    assert second["detail_checked_at"] == first["detail_checked_at"]
    assert len(source.calls) == 2


def test_stopping_at_known_window_does_not_overwrite_baseline(tmp_path, source, monkeypatch):
    monkeypatch.setattr("utils.site.advertised_total", lambda _: 4)
    cache = tmp_path / "cache"
    collect(tmp_path / "runs", "live", source, lambda: None, cache_dir=cache)
    baseline = (cache / "auctions.json").read_bytes()
    report = collect(tmp_path / "runs", "live", source, lambda: None, cache_dir=cache, stop_window=2)
    assert report["status"] == "partial"
    assert report["scope"] == "partial"
    assert report["stop_reason"] == "known-consecutive-window"
    assert report["matched_window"] == ["22096", "22095"]
    assert report["count"] == 2
    assert (cache / "auctions.json").read_bytes() == baseline


def test_force_refresh_and_changed_summaries_fetch_again(tmp_path, source, monkeypatch):
    monkeypatch.setattr("utils.site.advertised_total", lambda _: 4)
    cache = tmp_path / "cache"
    collect(tmp_path / "runs", "live", source, lambda: None, cache_dir=cache)
    forced = collect(tmp_path / "runs", "live", source, lambda: None, cache_dir=cache, cache_max_age_hours=0)
    assert forced["details_fetched"] == 4
    cached = read_json(cache / "auctions.json")
    cached["records"]["22096"]["auction"]["list_data"]["descripcion"] = "different"
    write_json(cache / "auctions.json", cached)
    changed = collect(tmp_path / "runs", "live", source, lambda: None, cache_dir=cache)
    assert changed["details_fetched"] == 1
    assert changed["details_reused"] == 3


def test_incomplete_run_preserves_baseline(tmp_path, source, monkeypatch):
    monkeypatch.setattr("utils.site.advertised_total", lambda _: 4)
    cache = tmp_path / "cache"
    collect(tmp_path / "runs", "live", source, lambda: None, cache_dir=cache)
    baseline = (cache / "auctions.json").read_bytes()
    monkeypatch.setattr("utils.site.advertised_total", lambda _: 197)
    report = collect(tmp_path / "runs", "live", source, lambda: None, cache_dir=cache)
    assert report["status"] == "partial"
    assert (cache / "auctions.json").read_bytes() == baseline


def test_unexpected_page_size_cannot_skip_records(tmp_path, source):
    report = collect(tmp_path, "live", source, lambda: None, page_size=12)
    assert report["status"] == "failed"
    assert "unexpected page size" in report["error"]["message"]


def test_reordered_auctions_force_detail_refresh(tmp_path, source, monkeypatch):
    monkeypatch.setattr("utils.site.advertised_total", lambda _: 4)
    cache = tmp_path / "cache"
    collect(tmp_path / "runs", "live", source, lambda: None, cache_dir=cache)
    monkeypatch.setattr("utils.extract.cards", lambda xml: [cards(xml)[i] for i in [2, 0, 1, 3]])
    report = collect(tmp_path / "runs", "live", source, lambda: None, cache_dir=cache)
    assert report["details_fetched"] == 2
    assert report["details_reused"] == 2


def test_removed_auction_does_not_block_reuse_of_later_ones(tmp_path, source, monkeypatch):
    monkeypatch.setattr("utils.site.advertised_total", lambda _: 4)
    cache = tmp_path / "cache"
    collect(tmp_path / "runs", "live", source, lambda: None, cache_dir=cache)
    monkeypatch.setattr("utils.site.advertised_total", lambda _: 3)
    monkeypatch.setattr("utils.extract.cards", lambda xml: [cards(xml)[i] for i in [0, 2, 3]])
    report = collect(tmp_path / "runs", "live", source, lambda: None, cache_dir=cache)
    assert report["status"] == "complete"
    assert report["details_fetched"] == 0
    assert report["details_reused"] == 3


def test_expired_cache_is_refreshed(tmp_path, source, monkeypatch):
    monkeypatch.setattr("utils.site.advertised_total", lambda _: 4)
    cache = tmp_path / "cache"
    collect(tmp_path / "runs", "live", source, lambda: None, cache_dir=cache)
    baseline = read_json(cache / "auctions.json")
    for record in baseline["records"].values():
        record["checked_at"] = "2000-01-01T00:00:00Z"
    write_json(cache / "auctions.json", baseline)
    report = collect(tmp_path / "runs", "live", source, lambda: None, cache_dir=cache)
    assert report["details_fetched"] == 4
    assert report["details_reused"] == 0


def test_window_spans_listing_pages(tmp_path, source, monkeypatch):
    monkeypatch.setattr("utils.site.advertised_total", lambda _: 8)
    respond = source.respond
    def two_pages(method, url, data, action):
        if action == LIST_ID and data[f"{LIST_ID}_first"] == "4":
            xml = source.pages["page"]
            for number in ["22096", "22095", "22094", "22093"]:
                xml = xml.replace(number, str(int(number) - 4))
            return xml
        return respond(method, url, data, action)
    source.respond = two_pages
    cache = tmp_path / "cache"
    seed = collect(tmp_path / "runs", "live", source, lambda: None, cache_dir=cache)
    assert seed["status"] == "complete"
    assert seed["count"] == 8
    stopped = collect(tmp_path / "runs", "live", source, lambda: None, cache_dir=cache, stop_window=6)
    assert stopped["count"] == 6
    assert stopped["stop_reason"] == "known-consecutive-window"
    assert len(stopped["matched_window"]) == 6


def test_public_history_and_ids_restore_the_incremental_baseline(tmp_path, source, monkeypatch):
    monkeypatch.setattr("utils.site.advertised_total", lambda _: 4)
    report = collect(tmp_path / "runs", "live", source, lambda: None)
    auctions = read_json(tmp_path / "runs" / report["run_id"] / "auctions.json")
    site = tmp_path / "site"
    publish_run({**report, "auctions": auctions}, site)
    source.calls.clear()
    next_run = collect(tmp_path / "runs", "live", source, lambda: None, baseline_dir=site)
    assert next_run["details_reused"] == 4
    assert next_run["details_fetched"] == 0
    assert len(source.calls) == 2


def test_returns_reload_listing_state_and_refreshed_action_ids(tmp_path, stateful_source):
    report = collect(tmp_path, "sample", stateful_source, lambda: None)
    assert report["status"] == "partial"
    assert report["count"] == 4
    assert report["details_complete"] is True
    assert stateful_source.revision == 9
    assert stateful_source.pagination == [(0, 4)] * 9
    clicks = [action for method, url, action in stateful_source.calls if method == "POST" and url == LIST_URL and action != LIST_ID]
    assert clicks[:3] == [f"{LIST_ID}:0:j_idt1169", f"{LIST_ID}:0:j_idt2168", f"{LIST_ID}:1:j_idt3169"]


def test_return_restores_twelve_row_page_and_reselects_by_number(tmp_path, stateful_source):
    site = RemajuSite(Trace(tmp_path / "trace"), stateful_source, lambda: None, rows=12)
    site.open_listing()
    page = cards(site.list_page(12))
    target = page[7]
    assert target.listing.numero_remate == "22077"
    site.open_detail(target)
    site.leave()
    assert stateful_source.pagination == [(12, 12), (12, 12)]
    assert site.view.state == stateful_source.expected_state
    site.open_tracking(target)
    assert stateful_source.calls[-2] == ("POST", LIST_URL, f"{LIST_ID}:19:j_idt2168")
    site.leave()
    assert stateful_source.pagination == [(12, 12)] * 3
    assert len(site.cards) == 12


@pytest.mark.parametrize("change", ["missing", "changed", "no-tracking"])
def test_refreshed_listing_cannot_select_a_missing_or_changed_auction(tmp_path, stateful_source, change):
    site = RemajuSite(Trace(tmp_path / "trace"), stateful_source, lambda: None)
    site.open_listing()
    card = cards(site.list_page(0))[0]
    number = card.listing.numero_remate
    if change == "missing":
        del site.cards[number]
    elif change == "changed":
        site.cards[number] = replace(card, listing=card.listing.model_copy(update={"descripcion": "changed"}))
    else:
        site.cards[number] = replace(card, tracking_id=None)
    before = len(stateful_source.calls)
    with pytest.raises(ValueError, match="Tracking action missing" if change == "no-tracking" else "Listing changed"):
        site.open_tracking(card)
    assert all(action in {"", LIST_ID} for _, _, action in stateful_source.calls[before:])
    assert stateful_source.pagination[1:] == ([(4, 4)] if change == "missing" else [])


def test_inserted_auction_relocates_card_pushed_to_next_page(tmp_path, stateful_source):
    site = RemajuSite(Trace(tmp_path / "trace"), stateful_source, lambda: None, rows=12)
    site.open_listing()
    target = cards(site.list_page(36))[-1]
    site.open_detail(target)
    stateful_source.inserted = 1
    site.leave()
    assert site.shift == 1
    assert target.listing.numero_remate not in site.cards
    site.open_tracking(target)
    assert stateful_source.pagination[-2:] == [(36, 12), (48, 12)]
    assert stateful_source.calls[-2][2].startswith(f"{LIST_ID}:48:")
    site.leave()
    assert site.first == 48


def test_auction_missing_from_neighbouring_pages_still_fails(tmp_path, stateful_source):
    site = RemajuSite(Trace(tmp_path / "trace"), stateful_source, lambda: None, rows=12)
    site.open_listing()
    target = cards(site.list_page(12))[0]
    stateful_source.inserted = 30
    del site.cards[target.listing.numero_remate]
    with pytest.raises(ValueError, match="Listing changed"):
        site.open_detail(target)
    assert stateful_source.pagination[-2:] == [(24, 12), (0, 12)]


@pytest.mark.parametrize("inserted, total", [(1, 25), (-1, 23)])
def test_listing_shift_during_collection_neither_skips_nor_fails(tmp_path, stateful_source, monkeypatch, inserted, total):
    stateful_source.total = 24
    monkeypatch.setattr("utils.site.advertised_total", lambda _: stateful_source.total)
    respond = stateful_source.respond

    def shifting(method, url, data, source):
        if method == "GET" and url == LIST_URL and stateful_source.revision == 30:
            stateful_source.inserted, stateful_source.total = inserted, total
        return respond(method, url, data, source)

    stateful_source.respond = shifting
    report = collect(tmp_path, "live", stateful_source, lambda: None, page_size=12)
    numbers = (tmp_path / report["run_id"] / "ids.txt").read_text().splitlines()
    assert report["failures"] == []
    assert report["pages_complete"] is True
    assert len(numbers) == len(set(numbers))
    assert {str(number) for number in range(22073, 22097)} <= set(numbers)
    if inserted > 0:
        assert report["status"] == "complete"
        assert numbers[-1] == "22097"


@pytest.mark.parametrize("url, suffix, action", [
    (LIST_URL, "j_idt169", "detail-click"),
    (DETAIL_URL, "j_idt171", "detail-close"),
    (LIST_URL, "j_idt168", "tracking-click"),
    (TRACKING_URL, "j_idt40", "tracking-close"),
])
def test_recorded_source_error_stops_on_original_navigation_and_preserves_baseline(tmp_path, source, sample_data_dir, monkeypatch, url, suffix, action):
    monkeypatch.setattr("utils.site.advertised_total", lambda _: 4)
    cache = tmp_path / "cache"
    assert collect(tmp_path / "runs", "live", source, lambda: None, cache_dir=cache)["status"] == "complete"
    baseline = {path.name: path.read_bytes() for path in cache.iterdir()}
    original = source.respond
    recorded = (sample_data_dir / "navigation_error.xml").read_text()

    def fail(method, request_url, data, button):
        if method == "POST" and request_url == url and button.endswith(suffix):
            return recorded
        return original(method, request_url, data, button)

    source.respond = fail
    source.calls.clear()
    report = collect(tmp_path / "runs", "live", source, lambda: None, cache_dir=cache, cache_max_age_hours=0)
    assert report["status"] == "failed"
    assert report["count"] == 0
    assert report["failures"][0]["numero_remate"] == "22096"
    assert report["error"]["message"] == f"Unexpected {action} redirect: /remaju/error/error500.xhtml"
    response = report["error"]["response"]
    assert response["action"] == action
    assert response["status"] == 200
    assert (tmp_path / "runs" / report["run_id"] / response["body_file"]).read_text() == recorded
    assert source.calls[-1][0:2] == ("POST", url)
    assert source.calls[-1][2].endswith(suffix)
    assert {path.name: path.read_bytes() for path in cache.iterdir()} == baseline
