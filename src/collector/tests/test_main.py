import json

import pytest

from main import main
from utils.archive import read_json, write_json


def invoke(capsys, *args: str) -> tuple[int, str, str]:
    try:
        main(list(args))
        code = 0
    except SystemExit as stop:
        code = stop.code or 0
    output = capsys.readouterr()
    return code, output.out, output.err


def test_options_use_dashed_names(capsys, sample_data_dir, tmp_path):
    output = tmp_path / "replay.json"
    code, out, _ = invoke(capsys, "replay", "--capture-dir", str(sample_data_dir), "--output", str(output))
    assert code == 0
    assert json.loads(out) == {"output": str(output), "count": 4, "publishable": False}
    code, out, _ = invoke(capsys, "show", "--input", str(output), "--auction-id", "remaju:22096")
    assert code == 0
    assert json.loads(out)["numero_remate"] == "22096"


def test_invalid_mode_is_rejected_before_collecting(capsys, tmp_path):
    code, out, _ = invoke(capsys, "collect", "--mode", "bogus", "--output", str(tmp_path))
    assert code == 1
    assert "Cannot parse 'bogus'" in out
    assert not any(tmp_path.iterdir())


def test_partial_publication_requires_acknowledgement(capsys, tmp_path):
    run = tmp_path / "run.json"
    write_json(run, {"run_id": "r1", "mode": "live", "status": "partial", "scope": "partial", "auctions": []})
    code, _, err = invoke(capsys, "publish", "--run-file", str(run), "--target", str(tmp_path / "site"))
    assert code == 5
    assert "Only complete all-phase live runs" in json.loads(err)["error"]["message"]
    assert not (tmp_path / "site/manifest.json").exists()


def test_process_consolidates_without_external_services(capsys, tmp_path):
    write_json(tmp_path / "auctions.json", [])
    write_json(tmp_path / "run.json", {"run_id": "r1"})
    code, out, _ = invoke(capsys, "process", "--run-dir", str(tmp_path))
    assert code == 0
    assert json.loads(out)["count"] == 0
    assert read_json(tmp_path / "consolidated.json") == {"run_id": "r1", "auctions": []}


def test_failed_collection_returns_nonzero_with_machine_readable_report(capsys, tmp_path, monkeypatch):
    report = {"run_id": "r1", "status": "failed", "error": {"message": "Unexpected redirect"}}
    monkeypatch.setattr("main.collect", lambda *args, **kwargs: report)
    code, out, _ = invoke(capsys, "collect", "--mode", "live", "--output", str(tmp_path))
    assert code == 4
    assert json.loads(out) == report


@pytest.mark.parametrize("args", [("--help",), ("query", "--help")])
def test_help_exits_cleanly(capsys, args):
    code, out, _ = invoke(capsys, *args)
    assert code == 0
    assert "remaju" in out
