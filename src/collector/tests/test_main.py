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


def test_publication_requires_fixture_acknowledgement(capsys, tmp_path):
    run = tmp_path / "run.json"
    write_json(run, {"auctions": []})
    code, _, err = invoke(capsys, "publish", "--run-file", str(run), "--target", str(tmp_path / "site"))
    assert code == 5
    assert "Production publication is disabled" in json.loads(err)["error"]["message"]
    assert not (tmp_path / "site").exists()


def test_process_consolidates_without_external_services(capsys, tmp_path):
    write_json(tmp_path / "auctions.json", [])
    write_json(tmp_path / "run.json", {"run_id": "r1"})
    code, out, _ = invoke(capsys, "process", "--run-dir", str(tmp_path))
    assert code == 0
    assert json.loads(out)["count"] == 0
    assert read_json(tmp_path / "consolidated.json") == {"run_id": "r1", "auctions": []}


@pytest.mark.parametrize("args", [("--help",), ("query", "--help")])
def test_help_exits_cleanly(capsys, args):
    code, out, _ = invoke(capsys, *args)
    assert code == 0
    assert "remaju" in out
