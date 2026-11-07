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


def test_advertised_count_is_required():
    broken = run()
    broken["advertised_total"] = 2
    with pytest.raises(ValueError, match="total"):
        validate_run(broken)
