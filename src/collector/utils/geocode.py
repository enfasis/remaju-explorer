from pathlib import Path

import requests

from .archive import read_json, write_json

API_URL = "https://maps.googleapis.com/maps/api/geocode/json"


def cache_key(address: str, district: str | None, province: str | None, department: str | None, country: str) -> str:
    return "|".join(part.strip().lower() for part in (address, district or "", province or "", department or "", country))


def full_address(address: str, district: str | None, province: str | None, department: str | None, country: str) -> str:
    return ", ".join(part.strip() for part in (address, district, province, department, country) if part)


class GeocodingClient:
    def __init__(self, api_key: str, cache_file: Path, session: requests.Session | None = None):
        self.api_key = api_key
        self.cache_file = cache_file
        self.cache: dict[str, dict[str, float]] = read_json(cache_file) if cache_file.exists() else {}
        self.session = session or requests.Session()

    def locate(self, address: str, district: str | None = None, province: str | None = None, department: str | None = None, country: str = "Peru") -> tuple[float, float] | None:
        key = cache_key(address, district, province, department, country)
        if key in self.cache:
            return self.cache[key]["latitude"], self.cache[key]["longitude"]
        location = self.request(full_address(address, district, province, department, country))
        if location is None:
            return None
        self.cache[key] = {"latitude": location[0], "longitude": location[1]}
        write_json(self.cache_file, self.cache)
        return location

    def request(self, address: str) -> tuple[float, float] | None:
        try:
            response = self.session.get(API_URL, params={"address": address, "key": self.api_key, "region": "pe"}, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get("status") != "OK" or not data.get("results"):
                return None
            location = data["results"][0]["geometry"]["location"]
            return float(location["lat"]), float(location["lng"])
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
            return None
