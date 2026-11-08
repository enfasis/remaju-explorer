import pytest

from utils.archive import read_json, reconcile, write_json
from utils.migration import migrate_bucket
from utils.publication import checksum


def auction(number, price):
    return {"numero_remate": number, "list_data": {"estado": "En proceso"}, "detail": {"remate_tab": {"precio_base": price}, "inmuebles_tab": {"inmuebles": []}, "cronograma_tab": {"fases": [{"nro": 3, "fecha_fin": "2099-01-01T00:00:00"}]}}}


def legacy(source):
    older, _ = reconcile({}, [auction("1", "$ 10"), auction("2", "$ 10")], "old", "2026-11-07T00:00:00Z", "all-phases")
    newer, _ = reconcile({}, [auction("2", "$ 20")], "new", "2026-11-08T00:00:00Z", "all-phases")
    write_json(source / "data/releases/old/state.json", older)
    path = source / "data/releases/new/state.json"
    write_json(path, newer)
    write_json(source / "data/releases/old/auctions/1.json", {"numero_remate": "1"})
    write_json(source / "data/manifest.json", {"scope": "all-phases", "schema_version": 1, "observed_at": "2026-11-08T00:00:00Z", "state": {"path": "/data/releases/new/state.json", "sha256": checksum(path)}})


def test_merges_all_states_preserves_history_and_latest_details(tmp_path):
    source = tmp_path / "source"
    legacy(source)
    ids = tmp_path / "ids.txt"
    ids.write_text("2\n")
    output = tmp_path / "flat"
    report = migrate_bucket(source, output, ids)
    records = read_json(output / "history.json")["records"]
    assert report["historical_auctions"] == 2
    assert report["current_auctions"] == 1
    assert records["remaju:1"]["present"] is False
    assert records["remaju:2"]["document"]["detail"]["remate_tab"]["precio_base"] == "$ 20"
    assert records["remaju:2"]["first_seen_at"] == "2026-11-07T00:00:00Z"
    assert (output / "ids.txt").read_text() == "2\n"
    assert (source / "data/releases/old/state.json").exists()
    assert {path.name for path in output.iterdir() if not path.name.startswith(".")} == {"manifest.json", "available.json", "history.json", "ids.txt"}


def test_refuses_to_lose_unaccounted_individual_auction(tmp_path):
    source = tmp_path / "source"
    legacy(source)
    write_json(source / "data/releases/old/auctions/999.json", {"numero_remate": "999"})
    ids = tmp_path / "ids.txt"
    ids.write_text("2\n")
    with pytest.raises(ValueError, match="missing from the state"):
        migrate_bucket(source, tmp_path / "flat", ids)
