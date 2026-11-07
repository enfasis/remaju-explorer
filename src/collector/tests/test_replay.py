import pytest

from remaju.replay import replay


def test_replay_fixture_is_not_publishable(sample_data_dir):
    result = replay(sample_data_dir)
    assert result["count"] == 4
    assert result["publishable"] is False
    assert result["auctions"][0]["numero_remate"] == "22096"


def test_replay_rejects_missing_update(tmp_path):
    (tmp_path / "page1_list.xml").write_text("<partial-response><changes/></partial-response>")
    with pytest.raises(ValueError, match="listing update"):
        replay(tmp_path)
