from datetime import date
from pathlib import Path
from typing import Any

from models import Auction
from utils.archive import read_json, write_json
from utils.exchange import ExchangeRateClient, convert
from utils.geocode import GeocodingClient
from utils.publication import publish_run


class Processing:
    def __init__(self, run_dir: Path, geocoder: GeocodingClient | None = None, rates: ExchangeRateClient | None = None, target: Path | None = None, today: date | None = None, allow_partial: bool = False):
        self.run_dir = run_dir
        self.geocoder = geocoder
        self.rates = rates
        self.target = target
        self.today = today or date.today()
        self.allow_partial = allow_partial

    def process(self) -> dict[str, Any]:
        auctions = self.load()
        self.geocode(auctions)
        self.exchange(auctions)
        run = self.consolidate(auctions)
        return self.publish(run) if self.target else run

    def load(self) -> list[Auction]:
        return [Auction.model_validate(item) for item in read_json(self.run_dir / "auctions.json")]

    def geocode(self, auctions: list[Auction]) -> None:
        if self.geocoder is None:
            return
        for auction in auctions:
            tab = auction.detail.inmuebles_tab
            for item in tab.inmuebles:
                if item.latitude is not None and item.longitude is not None:
                    continue
                location = self.geocoder.locate(item.direccion, tab.distrito, tab.provincia, tab.departamento)
                if location:
                    item.latitude, item.longitude = location

    def exchange(self, auctions: list[Auction]) -> None:
        rate = self.rates.pen_to_usd(self.today) if self.rates else None
        if rate is None:
            return
        for auction in auctions:
            convert(auction.detail.remate_tab, rate, self.today)

    def consolidate(self, auctions: list[Auction]) -> dict[str, Any]:
        run = {**read_json(self.run_dir / "run.json"), "auctions": [auction.model_dump(mode="json") for auction in auctions]}
        write_json(self.run_dir / "consolidated.json", run)
        return run

    def publish(self, run: dict[str, Any]) -> dict[str, Any]:
        return publish_run(run, self.target, self.allow_partial)
