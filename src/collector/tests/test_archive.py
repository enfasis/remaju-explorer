import csv
import json
import subprocess
import sys

import pytest

from remaju.archive import export_csv, reconcile


def auction(number: str, price: str = "100") -> dict:
    return {"numero_remate": number, "list_data": {"precio_base": price}}


def test_observation_history_preserves_changes_and_reappearance():
    first, events = reconcile({}, [auction("1")], "r1", "2026-01-01T00:00:00Z", "all")
    assert [event["type"] for event in events] == ["auction.observed"]
    second, events = reconcile(first, [auction("1")], "r2", "2026-01-02T00:00:00Z", "all")
    assert events == []
    assert second["records"]["remaju:1"]["last_seen_at"] == "2026-01-02T00:00:00Z"
    third, events = reconcile(second, [auction("1", "200")], "r3", "2026-01-03T00:00:00Z", "all")
    assert [event["type"] for event in events] == ["auction.observed"]
    fourth, events = reconcile(third, [], "r4", "2026-01-04T00:00:00Z", "all")
    assert [event["type"] for event in events] == ["auction.absent"]
    fifth, events = reconcile(fourth, [auction("1")], "r5", "2026-01-05T00:00:00Z", "all")
    assert [event["type"] for event in events] == ["auction.observed", "auction.reappeared"]
    assert fifth["records"]["remaju:1"]["first_seen_at"] == "2026-01-01T00:00:00Z"


def test_reconcile_rejects_duplicates_and_changed_scope():
    with pytest.raises(ValueError, match="Duplicate"):
        reconcile({}, [auction("1"), auction("1")], "r", "2026-01-01", "all")
    with pytest.raises(ValueError, match="different scopes"):
        reconcile({"scope": "all"}, [], "r", "2026-01-01", "other")


def test_csv_escapes_formulas_and_preserves_unicode(tmp_path):
    path = tmp_path / "export.csv"
    export_csv([{"numero_remate": "001", "list_data": {"descripcion": "=HYPERLINK(\"x\")", "fase": "Publicación"}}], path)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        row = next(csv.DictReader(stream))
    assert row["numero_remate"] == "001"
    assert row["descripcion"].startswith("'=")
    assert row["fase"] == "Publicación"


def test_cli_import_never_overwrites_input(tmp_path):
    source = tmp_path / "auctions.json"
    source.write_text(json.dumps({"auctions": [auction("1")]}))
    result = subprocess.run([sys.executable, "-m", "remaju", "import-legacy", "--input", str(source), "--output", str(source)], capture_output=True, text=True)
    assert result.returncode == 5
    assert json.loads(source.read_text())["auctions"][0]["numero_remate"] == "1"
