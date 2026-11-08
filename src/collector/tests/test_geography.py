from unittest.mock import Mock

import pytest

from utils.archive import read_json, write_json
from utils.geocode import GeocodingClient, cache_key
from utils.geography import in_peru


@pytest.mark.parametrize("latitude,longitude,expected", [(-12.0464, -77.0428, True), (-3.75, -73.25, True), (-18.01, -70.25, True), (-13.53, -71.97, True), (37.77, -122.42, False), (40, 70, False), (-16.5, -68.15, False), (-0.18, -78.47, False), (-12, -81, False), (None, -77, False), (float("nan"), -77, False), (True, -77, False)])
def test_peru_polygon_rejects_other_countries_and_ocean(latitude, longitude, expected):
    assert in_peru(latitude, longitude) is expected


def test_invalid_cached_geocode_is_not_reused(tmp_path):
    path = tmp_path / "geo.json"
    key = cache_key("address", None, None, None, "Peru")
    write_json(path, {key: {"latitude": 37.77, "longitude": -122.42}})
    client = GeocodingClient("test", path)
    client.request = Mock(return_value=None)
    assert client.locate("address") is None
    assert key not in read_json(path)


def test_geocoding_constrains_country_and_rejects_foreign_result(tmp_path):
    session = Mock()
    session.get.return_value.json.return_value = {"status": "OK", "results": [{"geometry": {"location": {"lat": 37.77, "lng": -122.42}}}]}
    client = GeocodingClient("test", tmp_path / "geo.json", session)
    assert client.request("address") is None
    assert session.get.call_args.kwargs["params"]["components"] == "country:PE"
