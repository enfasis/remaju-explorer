from pathlib import Path

import pytest

from config import Settings
from utils.archive import write_json
from test_main import invoke


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for name in ("GEOCODING_API_KEY", "geocoding_api_key", "GEOCODING_CACHE", "EXCHANGE_RATE_CACHE"):
        monkeypatch.delenv(name, raising=False)


def test_settings_read_environment_case_insensitively(monkeypatch):
    monkeypatch.setenv("GEOCODING_API_KEY", "s3cr3t-value")
    monkeypatch.setenv("GEOCODING_CACHE", "cache/geo.json")
    settings = Settings()
    assert settings.geocoding_key() == "s3cr3t-value"
    assert settings.geocoding_cache == Path("cache/geo.json")
    assert "s3cr3t-value" not in repr(settings)


def test_settings_read_dotenv_file(tmp_path):
    (tmp_path / ".env").write_text("geocoding_api_key=from-file\nGEMINI_API_KEY=ignored\n")
    assert Settings().geocoding_key() == "from-file"


def test_missing_geocoding_key_is_reported():
    with pytest.raises(ValueError, match="GEOCODING_API_KEY"):
        Settings().geocoding_key()


def test_geocode_without_key_fails_before_processing(capsys, tmp_path):
    write_json(tmp_path / "auctions.json", [])
    write_json(tmp_path / "run.json", {"run_id": "r1"})
    code, _, err = invoke(capsys, "process", "--run-dir", str(tmp_path), "--geocode")
    assert code == 5
    assert "GEOCODING_API_KEY" in err
    assert not (tmp_path / "consolidated.json").exists()
