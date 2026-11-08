from pathlib import Path

import requests

from .archive import read_json, write_json
from .geography import in_peru

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
            location = self.cache[key]
            if in_peru(location.get("latitude"), location.get("longitude")):
                return location["latitude"], location["longitude"]
            del self.cache[key]
            write_json(self.cache_file, self.cache)
        location = self.request(full_address(address, district, province, department, country))
        if location is None or not in_peru(*location):
            return None
        self.cache[key] = {"latitude": location[0], "longitude": location[1]}
        write_json(self.cache_file, self.cache)
        return location

    def request(self, address: str) -> tuple[float, float] | None:
        try:
            response = self.session.get(API_URL, params={"address": address, "key": self.api_key, "region": "pe", "components": "country:PE"}, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get("status") != "OK" or not data.get("results"):
                return None
            for result in data["results"]:
                location = result["geometry"]["location"]
                latitude, longitude = float(location["lat"]), float(location["lng"])
                if in_peru(latitude, longitude):
                    return latitude, longitude
            return None
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
            return None
