import pytest
from datetime import datetime

from utils.archive import read_json, write_json, reconcile
from utils.publication import checksum, eligible, money, publish_run, validate_run


def run(run_id="r1", mode="live"):
    return {"run_id": run_id, "mode": mode, "status": "complete", "scope": "all-phases", "observed_at": "2026-01-01T00:00:00Z", "advertised_total": 1, "pages_complete": True, "details_complete": True, "auctions": [{"numero_remate": "1", "list_data": {"fase": "Presentación de Ofertas", "estado": "En proceso", "fecha_presentacion": "2026-02-26"}, "detail": {"remate_tab": {"precio_base": "S/. 1,234.50"}, "inmuebles_tab": {"inmuebles": []}, "cronograma_tab": {"fases": [{"nro": 3, "fase": "Presentación de Ofertas", "fecha_inicio": "2026-01-01T00:00:00", "fecha_fin": "2099-01-01T23:59:59"}]}}}]}


def test_money_preserves_decimal_and_currency():
    assert money("S/. 1,234.50") == {"raw": "S/. 1,234.50", "amount": "1234.50", "currency": "PEN"}
    assert money("$ NaN")["amount"] is None


def test_incomplete_run_does_not_replace_manifest(tmp_path):
    first = publish_run(run(), tmp_path)
    with pytest.raises(ValueError):
        publish_run(run("r2", "sample"), tmp_path)
    assert read_json(tmp_path / "manifest.json") == first
    assert not (tmp_path / "releases").exists()


def test_accepted_snapshot_and_repeated_run(tmp_path):
    manifest = publish_run(run(), tmp_path)
    snapshot = read_json(tmp_path / manifest["available"]["path"])
    assert snapshot["auctions"][0]["detail"]["remate_tab"]["precio_base"] == "S/. 1,234.50"
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
    assert manifest["history"]["path"] == "history.json"


def test_details_and_coordinates_live_in_history_without_individual_files(tmp_path):
    source = run()
    source["auctions"][0]["detail"]["inmuebles_tab"] = {"departamento": "LIMA", "inmuebles": [{"direccion": "Av. 1", "latitude": -12.1, "longitude": -77.0}]}
    manifest = publish_run(source, tmp_path)
    summary = read_json(tmp_path / manifest["available"]["path"])["auctions"][0]
    detail = read_json(tmp_path / "history.json")["records"]["remaju:1"]["document"]["detail"]
    assert summary["detail"]["inmuebles_tab"]["inmuebles"][0]["latitude"] == -12.1
    assert detail["inmuebles_tab"]["departamento"] == "LIMA"
    assert detail["inmuebles_tab"]["inmuebles"][0]["direccion"] == "Av. 1"
    assert "detail_path" not in summary
    assert sorted(path.name for path in tmp_path.iterdir() if not path.name.startswith(".")) == ["available.json", "history.json", "ids.txt", "manifest.json"]


def test_advertised_count_is_required():
    broken = run()
    broken["advertised_total"] = 2
    with pytest.raises(ValueError, match="total"):
        validate_run(broken)


def test_early_stop_cannot_be_published_even_with_partial_override(tmp_path):
    source = {**partial(), "stop_reason": "known-consecutive-window"}
    with pytest.raises(ValueError, match="Early-stop"):
        publish_run(source, tmp_path, allow_partial=True)


def test_partial_run_cannot_replace_complete_baseline(tmp_path):
    manifest = publish_run(run(), tmp_path)
    with pytest.raises(ValueError, match="partial run cannot replace"):
        publish_run(partial(), tmp_path, allow_partial=True)
    assert read_json(tmp_path / "manifest.json") == manifest


@pytest.mark.parametrize("end,expected", [("2026-11-08T03:00:00", True), ("2026-11-08T02:59:59", False), ("2026-11-08T08:00:00+00:00", True), (None, False), ("bad", False)])
def test_availability_uses_phase_three_deadline_in_lima(end, expected):
    auction = run()["auctions"][0]
    auction["detail"]["cronograma_tab"]["fases"][0]["fecha_fin"] = end
    assert eligible(auction, datetime.fromisoformat("2026-11-08T03:00:00-05:00")) is expected


def test_missing_phase_three_and_cancelled_auctions_are_not_available():
    auction = run()["auctions"][0]
    auction["list_data"]["estado"] = "Cancelado"
    assert not eligible(auction)
    auction["list_data"]["estado"] = "En proceso"
    auction["detail"]["cronograma_tab"]["fases"] = []
    assert not eligible(auction)


def test_history_keeps_missing_and_updates_existing_records(tmp_path):
    publish_run(run(), tmp_path)
    next_run = run("r2")
    next_run["auctions"][0]["numero_remate"] = "2"
    manifest = publish_run(next_run, tmp_path)
    records = read_json(tmp_path / "history.json")["records"]
    assert records["remaju:1"]["present"] is False
    assert records["remaju:2"]["present"] is True
    assert manifest["history_count"] == 2
    assert (tmp_path / "ids.txt").read_text() == "2\n"
    updated = run("r3")
    updated["auctions"][0]["numero_remate"] = "2"
    updated["auctions"][0]["detail"]["remate_tab"]["precio_base"] = "$ 999"
    publish_run(updated, tmp_path)
    records = read_json(tmp_path / "history.json")["records"]
    assert len(records) == 2
    assert records["remaju:2"]["document"]["detail"]["remate_tab"]["precio_base"] == "$ 999"


def test_legacy_state_is_migrated_without_losing_history(tmp_path):
    first = run()
    state, _ = reconcile({}, first["auctions"], "r1", first["observed_at"], "all-phases")
    legacy = tmp_path / "data/releases/r1/state.json"
    write_json(legacy, state)
    write_json(tmp_path / "data/manifest.json", {"schema_version": 1, "scope": "all-phases", "state": {"path": "/data/releases/r1/state.json", "sha256": checksum(legacy)}})
    manifest = publish_run(run("r2"), tmp_path)
    assert manifest["schema_version"] == 2
    assert "remaju:1" in read_json(tmp_path / "history.json")["records"]
    assert legacy.exists()


def test_invalid_coordinates_removed_from_history_and_available(tmp_path):
    source = run()
    source["auctions"][0]["detail"]["inmuebles_tab"]["inmuebles"] = [{"latitude": 40, "longitude": -70}]
    publish_run(source, tmp_path)
    assert read_json(tmp_path / "available.json")["auctions"][0]["detail"]["inmuebles_tab"]["inmuebles"][0]["latitude"] is None
    item = read_json(tmp_path / "history.json")["records"]["remaju:1"]["document"]["detail"]["inmuebles_tab"]["inmuebles"][0]
    assert item["latitude"] is None
    assert source["auctions"][0]["detail"]["inmuebles_tab"]["inmuebles"][0]["latitude"] == 40
