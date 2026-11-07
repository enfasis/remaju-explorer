import pytest

from utils.archive import read_json
from utils.publication import money, publish_run, validate_run


def run(run_id="r1", mode="live"):
    return {"run_id": run_id, "mode": mode, "status": "complete", "scope": "all-phases", "observed_at": "2026-01-01T00:00:00Z", "advertised_total": 1, "pages_complete": True, "details_complete": True, "auctions": [{"numero_remate": "1", "list_data": {"fase": "Presentación de Ofertas", "estado": "En proceso", "fecha_presentacion": "2026-02-26"}, "detail": {"remate_tab": {"precio_base": "S/. 1,234.50"}, "inmuebles_tab": {"inmuebles": []}, "cronograma_tab": {"fases": []}}}]}


def test_money_preserves_decimal_and_currency():
    assert money("S/. 1,234.50") == {"raw": "S/. 1,234.50", "amount": "1234.50", "currency": "PEN"}
    assert money("$ NaN")["amount"] is None


def test_incomplete_run_does_not_replace_manifest(tmp_path):
    first = publish_run(run(), tmp_path)
    with pytest.raises(ValueError):
        publish_run(run("r2", "sample"), tmp_path)
    assert read_json(tmp_path / "data/manifest.json") == first
    assert not (tmp_path / "data/releases/r2").exists()


def test_accepted_snapshot_and_repeated_run(tmp_path):
    manifest = publish_run(run(), tmp_path)
    snapshot = read_json(tmp_path / manifest["availability"]["path"].lstrip("/"))
    assert snapshot["auctions"][0]["precio_base"]["amount"] == "1234.50"
    with pytest.raises(ValueError, match="already accepted"):
        publish_run(run(), tmp_path)


def partial(run_id="p1"):
    return {**run(run_id), "status": "partial", "scope": "partial", "advertised_total": 40, "pages_complete": False}


def test_partial_run_requires_allow_partial(tmp_path):
    with pytest.raises(ValueError, match="complete"):
        publish_run(partial(), tmp_path)
    manifest = publish_run(partial(), tmp_path, allow_partial=True)
    assert manifest["scope"] == "partial"


def test_complete_run_replaces_partial_baseline(tmp_path):
    publish_run(partial(), tmp_path, allow_partial=True)
    manifest = publish_run(run("r2"), tmp_path)
    assert manifest["scope"] == "all-phases"
    assert manifest["history"] == ["/data/releases/r2/events.jsonl.gz"]


def test_release_detail_matches_site_shape(tmp_path):
    source = run()
    source["auctions"][0]["detail"]["inmuebles_tab"] = {"departamento": "LIMA", "inmuebles": [{"direccion": "Av. 1", "latitude": -12.1, "longitude": -77.0}]}
    manifest = publish_run(source, tmp_path)
    summary = read_json(tmp_path / manifest["availability"]["path"].lstrip("/"))["auctions"][0]
    detail = read_json(tmp_path / summary["detail_path"].lstrip("/"))
    assert summary["coordinates"] == [{"latitude": -12.1, "longitude": -77.0}]
    assert detail["ubicacion"]["departamento"] == "LIMA"
    assert detail["inmuebles"][0]["direccion"] == "Av. 1"


def test_advertised_count_is_required():
    broken = run()
    broken["advertised_total"] = 2
    with pytest.raises(ValueError, match="total"):
        validate_run(broken)
