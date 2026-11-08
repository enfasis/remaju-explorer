from datetime import date

import pytest

from models import Auction
from processing import Processing
from utils import extract
from utils.archive import read_json, write_json
from utils.exchange import ExchangeRateClient


class Geocoder:
    def __init__(self):
        self.calls = []

    def locate(self, address, district=None, province=None, department=None):
        self.calls.append((address, district, province, department))
        return -12.1, -77.0


class Rates:
    def pen_to_usd(self, day):
        return 0.25


@pytest.fixture
def run_dir(tmp_path, list_xml, detail_html, inmuebles_xml, cronograma_xml):
    card = extract.cards(list_xml)[0]
    auction = Auction(numero_remate=card.listing.numero_remate, list_data=card.listing, detail=extract.detail("22096", detail_html, inmuebles_xml, cronograma_xml))
    write_json(tmp_path / "auctions.json", [auction.model_dump(mode="json")])
    write_json(tmp_path / "run.json", {"run_id": "r1", "mode": "live", "status": "complete", "scope": "all-phases", "observed_at": "2026-01-01T00:00:00Z", "advertised_total": 1, "pages_complete": True, "details_complete": True})
    return tmp_path


def test_processing_geocodes_converts_and_consolidates(run_dir):
    geocoder = Geocoder()
    run = Processing(run_dir, geocoder, Rates(), today=date(2026, 1, 1)).process()
    auction = run["auctions"][0]
    assert run["run_id"] == "r1"
    assert read_json(run_dir / "consolidated.json") == run
    assert len(geocoder.calls) == 1
    assert auction["detail"]["inmuebles_tab"]["inmuebles"][0]["latitude"] == -12.1
    assert auction["detail"]["remate_tab"]["precio_base_pen"] == pytest.approx(1163355.99)
    assert auction["detail"]["remate_tab"]["precio_base_usd"] == pytest.approx(290838.9975)
    assert auction["detail"]["remate_tab"]["exchange_rate_date"] == "2026-01-01"


def test_processing_without_services_leaves_auctions_untouched(run_dir):
    run = Processing(run_dir).process()
    assert run["auctions"] == read_json(run_dir / "auctions.json")


def test_processing_clears_foreign_coordinates_without_a_paid_request(run_dir):
    auctions = read_json(run_dir / "auctions.json")
    item = auctions[0]["detail"]["inmuebles_tab"]["inmuebles"][0]
    item["latitude"], item["longitude"] = 40, 70
    write_json(run_dir / "auctions.json", auctions)
    run = Processing(run_dir).process()
    item = run["auctions"][0]["detail"]["inmuebles_tab"]["inmuebles"][0]
    assert item["latitude"] is None
    assert item["longitude"] is None


def test_processing_publishes_consolidated_run(run_dir, tmp_path_factory):
    target = tmp_path_factory.mktemp("site")
    manifest = Processing(run_dir, target=target).process()
    assert manifest["run_id"] == "r1"
    assert (target / "manifest.json").exists()


def test_exchange_rate_falls_back_to_recent_cache(tmp_path):
    cache = tmp_path / "rates.json"
    write_json(cache, {"2026-01-01": 0.27})
    client = ExchangeRateClient(cache)
    client.request = lambda: None
    assert client.pen_to_usd(date(2026, 1, 3)) == 0.27
    assert client.pen_to_usd(date(2026, 1, 10)) is None
