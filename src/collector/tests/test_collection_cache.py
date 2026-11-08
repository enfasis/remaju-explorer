import pytest

from utils.collection_cache import CollectionCache, ConsecutiveWindow
from utils.archive import write_json


def test_new_prefix_then_historical_window():
    window = ConsecutiveWindow(["10", "9", "8", "7", "5", "4", "3", "2"], 4)
    found = [window.observe(number) for number in ["20", "19", "18", "10", "9", "8", "7"]]
    assert found == [False] * 6 + [True]
    assert list(window.matched) == ["10", "9", "8", "7"]


def test_interleaved_and_reordered_ids_reset_window():
    window = ConsecutiveWindow([str(i) for i in range(10, 0, -1)], 4)
    today = ["20", "8", "19", "7", "18", "17", "16", "10", "9", "6", "5", "4", "3", "2", "1"]
    hits = [number for number in today if window.observe(number)]
    assert hits[0] == "3"


def test_changed_summary_breaks_a_known_run():
    window = ConsecutiveWindow(["5", "4", "3", "2"], 4)
    assert not window.observe("5")
    assert not window.observe("4", unchanged=False)
    assert not window.observe("3")
    assert not window.observe("2")


@pytest.mark.parametrize("history,size", [(["1", "1"], 2), (["1"], 1)])
def test_invalid_window(history, size):
    with pytest.raises(ValueError):
        ConsecutiveWindow(history, size)


def test_mismatched_order_files_disable_cache(tmp_path):
    write_json(tmp_path / "auctions.json", {"schema_version": 1, "order": ["2", "1"], "records": {"2": {}}})
    (tmp_path / "ids.txt").write_text("1\n2\n")
    cache = CollectionCache(tmp_path)
    assert cache.order == []
    assert cache.records == {}
