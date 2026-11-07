"""Geocoding utility using Google Maps Geocoding API with caching."""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class GeocodingCache:
    """Cache for geocoding results to minimize API calls."""

    def __init__(self, cache_file: Path = Path("data/geocoding_cache.json")):
        """Initialize the geocoding cache.

        Args:
            cache_file: Path to the cache file
        """
        self.cache_file = cache_file
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Dict[str, float]] = {}
        self._load_cache()

    def _load_cache(self):
        """Load cache from file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                logger.info(f"Loaded {len(self._cache)} cached geocoding results")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load cache: {e}")
                self._cache = {}
        else:
            logger.info("No cache file found, starting with empty cache")
            self._cache = {}

    def _save_cache(self):
        """Save cache to file."""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(self._cache)} geocoding results to cache")
        except IOError as e:
            logger.error(f"Could not save cache: {e}")

    def _make_cache_key(
        self,
        address: str,
        country: Optional[str] = None,
        department: Optional[str] = None,
        province: Optional[str] = None,
        district: Optional[str] = None,
    ) -> str:
        """Create a unique cache key from address components.

        Args:
            address: The street address
            country: Country name (default: Peru)
            department: Department/Region
            province: Province
            district: District

        Returns:
            A unique string key for caching
        """
        # Normalize the key components
        components = [
            address.strip().lower(),
            (district or "").strip().lower(),
            (province or "").strip().lower(),
            (department or "").strip().lower(),
            (country or "peru").strip().lower(),
        ]
        return "|".join(components)

    def get_cached_location(
        self,
        address: str,
        country: Optional[str] = None,
        department: Optional[str] = None,
        province: Optional[str] = None,
        district: Optional[str] = None,
    ) -> Optional[Dict[str, float]]:
        """Check if location is already cached.

        Args:
            address: The street address
            country: Country name
            department: Department/Region
            province: Province
            district: District

        Returns:
            Dict with lat/lon if cached, None otherwise
        """
        key = self._make_cache_key(address, country, department, province, district)
        if key in self._cache:
            logger.debug(f"Cache hit for: {address[:50]}...")
            return self._cache[key]
        return None

    def add_to_cache(
        self,
        address: str,
        lat: float,
        lon: float,
        country: Optional[str] = None,
        department: Optional[str] = None,
        province: Optional[str] = None,
        district: Optional[str] = None,
    ):
        """Add a location to the cache.

        Args:
            address: The street address
            lat: Latitude
            lon: Longitude
            country: Country name
            department: Department/Region
            province: Province
            district: District
        """
        key = self._make_cache_key(address, country, department, province, district)
        self._cache[key] = {"latitude": lat, "longitude": lon}
        logger.info(f"Added to cache: {address[:50]}... -> ({lat}, {lon})")
        self._save_cache()


class GeocodingClient:
    """Client for Google Maps Geocoding API with caching."""

    BASE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

    def __init__(
        self, api_key: Optional[str] = None, cache: Optional[GeocodingCache] = None
    ):
        """Initialize the geocoding client.

        Args:
            api_key: Google Maps API key (defaults to env var geocoding_api_key)
            cache: GeocodingCache instance (creates new one if None)
        """
        self.api_key = api_key or os.getenv("geocoding_api_key")
        if not self.api_key:
            raise ValueError(
                "Google Geocoding API key not found. Set geocoding_api_key in .env"
            )

        self.cache = cache or GeocodingCache()
        self.session = requests.Session()

    def _build_address_string(
        self,
        address: str,
        country: Optional[str] = None,
        department: Optional[str] = None,
        province: Optional[str] = None,
        district: Optional[str] = None,
    ) -> str:
        """Build a formatted address string for the API.

        Args:
            address: The street address
            country: Country name (default: Peru)
            department: Department/Region
            province: Province
            district: District

        Returns:
            Formatted address string
        """
        components = [address.strip()]

        if district:
            components.append(district.strip())
        if province:
            components.append(province.strip())
        if department:
            components.append(department.strip())
        if country:
            components.append(country.strip())
        else:
            components.append("Peru")

        return ", ".join(components)

    def geocode(
        self,
        address: str,
        country: Optional[str] = None,
        department: Optional[str] = None,
        province: Optional[str] = None,
        district: Optional[str] = None,
        use_cache: bool = True,
    ) -> Optional[Tuple[float, float]]:
        """Geocode an address to get latitude and longitude.

        First checks the cache, then calls the Google API if not found.
        Results are automatically cached for future use.

        Args:
            address: The street address to geocode
            country: Country name (default: Peru)
            department: Department/Region
            province: Province
            district: District
            use_cache: Whether to use cache (default: True)

        Returns:
            Tuple of (latitude, longitude) or None if geocoding failed
        """
        # Check cache first
        if use_cache:
            cached = self.cache.get_cached_location(
                address, country, department, province, district
            )
            if cached:
                return (cached["latitude"], cached["longitude"])

        # Build full address string
        full_address = self._build_address_string(
            address, country, department, province, district
        )
        logger.info(f"Geocoding: {full_address[:80]}...")

        # Make API request
        params = {
            "address": full_address,
            "key": self.api_key,
            "region": "pe",  # Bias results to Peru
        }

        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "OK":
                logger.error(
                    f"Geocoding API error: {data.get('status')} - {data.get('error_message', 'No error message')}"
                )
                return None

            results = data.get("results", [])
            if not results:
                logger.warning(f"No geocoding results for: {full_address}")
                return None

            # Get the first result
            location = results[0]["geometry"]["location"]
            lat = location["lat"]
            lon = location["lng"]

            logger.info(f"Geocoding successful: ({lat}, {lon})")

            # Add to cache
            self.cache.add_to_cache(
                address, lat, lon, country, department, province, district
            )

            return (lat, lon)

        except requests.RequestException as e:
            logger.error(f"Geocoding request failed: {e}")
            return None
        except (KeyError, IndexError) as e:
            logger.error(f"Error parsing geocoding response: {e}")
            return None

    def geocode_inmueble(self, inmueble_data: dict) -> Optional[Tuple[float, float]]:
        """Geocode an inmueble using its address and location info.

        Args:
            inmueble_data: Dict with keys: direccion, distrito, provincia, departamento

        Returns:
            Tuple of (latitude, longitude) or None if geocoding failed
        """
        return self.geocode(
            address=inmueble_data.get("direccion", ""),
            district=inmueble_data.get("distrito"),
            province=inmueble_data.get("provincia"),
            department=inmueble_data.get("departamento"),
            country="Peru",
        )


# Convenience function for quick geocoding
def geocode_address(
    address: str,
    country: Optional[str] = None,
    department: Optional[str] = None,
    province: Optional[str] = None,
    district: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Optional[Tuple[float, float]]:
    """Convenience function to geocode a single address.

    Args:
        address: The street address
        country: Country name (default: Peru)
        department: Department/Region
        province: Province
        district: District
        api_key: Google Maps API key (uses env var if not provided)

    Returns:
        Tuple of (latitude, longitude) or None if geocoding failed
    """
    client = GeocodingClient(api_key=api_key)
    return client.geocode(address, country, department, province, district)


if __name__ == "__main__":
    # Test the geocoding client
    logging.basicConfig(level=logging.INFO)

    # Test address
    test_address = "Av. San Borja Norte 1187, San Borja, Lima, Peru"

    client = GeocodingClient()
    result = client.geocode(test_address)

    if result:
        lat, lon = result
        print(f"✓ Geocoded: {test_address}")
        print(f"  Latitude: {lat}")
        print(f"  Longitude: {lon}")
    else:
        print(f"✗ Failed to geocode: {test_address}")
