"""Exchange rate utility for PEN to USD conversion."""

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class ExchangeRateCache:
    """Cache for exchange rates to minimize API calls."""

    CACHE_FILE = Path("data/exchange_rate_cache.json")

    def __init__(self):
        self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._cache = self._load_cache()

    def _load_cache(self) -> dict:
        if self.CACHE_FILE.exists():
            try:
                with open(self.CACHE_FILE, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError, IOError:
                return {}
        return {}

    def _save_cache(self):
        with open(self.CACHE_FILE, "w") as f:
            json.dump(self._cache, f, indent=2)

    def get_rate(self, rate_date: date = None) -> Optional[float]:
        """Get cached rate for date."""
        if rate_date is None:
            rate_date = date.today()

        date_str = rate_date.isoformat()
        cached = self._cache.get(date_str)

        if cached:
            logger.info(f"Using cached exchange rate for {date_str}: {cached}")
            return cached

        return None

    def set_rate(self, rate: float, rate_date: date = None):
        """Cache rate for date."""
        if rate_date is None:
            rate_date = date.today()

        date_str = rate_date.isoformat()
        self._cache[date_str] = rate
        self._save_cache()
        logger.info(f"Cached exchange rate for {date_str}: {rate}")


class ExchangeRateClient:
    """Client for fetching PEN to USD exchange rates."""

    API_URL = "https://api.exchangerate-api.com/v4/latest/PEN"

    def __init__(self):
        self.cache = ExchangeRateCache()
        self.session = requests.Session()

    def get_pen_to_usd_rate(self, use_cache: bool = True) -> Optional[float]:
        """Get current PEN to USD exchange rate.

        Args:
            use_cache: Whether to use cached rate

        Returns:
            Exchange rate (1 PEN = X USD) or None if failed
        """
        today = date.today()

        # Check cache
        if use_cache:
            cached_rate = self.cache.get_rate(today)
            if cached_rate:
                return cached_rate

        # Fetch from API
        try:
            logger.info("Fetching exchange rate from API...")
            response = self.session.get(self.API_URL, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Extract USD rate
            usd_rate = data.get("rates", {}).get("USD")

            if usd_rate:
                logger.info(f"Exchange rate fetched: 1 PEN = {usd_rate} USD")
                self.cache.set_rate(usd_rate, today)
                return usd_rate
            else:
                logger.error("USD rate not found in API response")
                return None

        except requests.RequestException as e:
            logger.error(f"Failed to fetch exchange rate: {e}")
            # Return yesterday's rate if available
            yesterday = date.today()
            for i in range(1, 8):  # Try last 7 days
                try:
                    prev_date = yesterday.replace(day=yesterday.day - i)
                    cached = self.cache.get_rate(prev_date)
                    if cached:
                        logger.info(f"Using rate from {prev_date}: {cached}")
                        return cached
                except:
                    pass
            return None

    def convert_pen_to_usd(self, amount_pen: float) -> Optional[float]:
        """Convert PEN amount to USD.

        Args:
            amount_pen: Amount in Peruvian Soles

        Returns:
            Amount in USD or None if conversion failed
        """
        rate = self.get_pen_to_usd_rate()
        if rate and amount_pen:
            return amount_pen * rate
        return None


def parse_money_value(money_str: str) -> Optional[float]:
    """Parse money string like 'S/. 1,163,355.99' to float."""
    if not money_str:
        return None

    try:
        # Remove S/. and spaces
        cleaned = money_str.replace("S/.", "").replace(" ", "")
        # Remove commas
        cleaned = cleaned.replace(",", "")
        return float(cleaned)
    except ValueError, TypeError:
        return None


def parse_money_with_currency(money_str: str) -> tuple[Optional[float], Optional[str]]:
    """Parse money string and detect currency.

    Args:
        money_str: Money string like 'S/. 1,163,355.99' or '$ 11,808.00'

    Returns:
        Tuple of (numeric_value, currency_code) where currency_code is 'PEN' or 'USD'
    """
    if not money_str:
        return None, None

    money_str = money_str.strip()

    # Detect currency
    currency = None
    if "S/." in money_str:
        currency = "PEN"
    elif "$" in money_str:
        currency = "USD"

    try:
        # Remove currency symbols and spaces
        cleaned = money_str.replace("S/.", "").replace("$", "").replace(" ", "")
        # Remove commas
        cleaned = cleaned.replace(",", "")
        value = float(cleaned)
        return value, currency
    except ValueError, TypeError:
        return None, None


# Convenience function
def get_exchange_rate() -> Optional[float]:
    """Get current PEN to USD exchange rate."""
    client = ExchangeRateClient()
    return client.get_pen_to_usd_rate()


def convert_price(money_str: str, to_usd: bool = True) -> Optional[float]:
    """Convert price string to USD or keep in PEN."""
    pen_value = parse_money_value(money_str)

    if pen_value is None:
        return None

    if to_usd:
        client = ExchangeRateClient()
        return client.convert_pen_to_usd(pen_value)

    return pen_value
