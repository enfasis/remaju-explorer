from datetime import date, timedelta
from pathlib import Path

import requests

from models import RemateTab

from .archive import read_json, write_json

API_URL = "https://api.exchangerate-api.com/v4/latest/PEN"
MONEY_FIELDS = ("precio_base", "arancel", "oblaje")


def parse_money(value: str | None) -> tuple[float | None, str | None]:
    if not value:
        return None, None
    text = value.strip()
    currency = "PEN" if "S/." in text else "USD" if "$" in text else None
    try:
        return float(text.replace("S/.", "").replace("$", "").replace(" ", "").replace(",", "")), currency
    except ValueError:
        return None, None


def convert(tab: RemateTab, rate: float, day: date) -> None:
    tab.exchange_rate = rate
    tab.exchange_rate_date = day
    for field in MONEY_FIELDS:
        amount, currency = parse_money(getattr(tab, field))
        if amount is None or currency is None:
            continue
        pen, usd = (amount / rate, amount) if currency == "USD" else (amount, amount * rate)
        setattr(tab, f"{field}_pen", pen)
        setattr(tab, f"{field}_usd", usd)


class ExchangeRateClient:
    def __init__(self, cache_file: Path, session: requests.Session | None = None):
        self.cache_file = cache_file
        self.cache: dict[str, float] = read_json(cache_file) if cache_file.exists() else {}
        self.session = session or requests.Session()

    def pen_to_usd(self, day: date) -> float | None:
        if day.isoformat() in self.cache:
            return self.cache[day.isoformat()]
        rate = self.request()
        if rate is None:
            return self.recent(day)
        self.cache[day.isoformat()] = rate
        write_json(self.cache_file, self.cache)
        return rate

    def recent(self, day: date) -> float | None:
        return next((self.cache[key] for offset in range(1, 8) if (key := (day - timedelta(days=offset)).isoformat()) in self.cache), None)

    def request(self) -> float | None:
        try:
            response = self.session.get(API_URL, timeout=10)
            response.raise_for_status()
            rate = response.json().get("rates", {}).get("USD")
            return float(rate) if rate else None
        except (requests.RequestException, ValueError, TypeError, AttributeError):
            return None
