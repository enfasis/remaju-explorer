from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    geocoding_api_key: SecretStr | None = None
    geocoding_cache: Path = Path("data/geocoding_cache.json")
    exchange_rate_cache: Path = Path("data/exchange_rate_cache.json")

    def geocoding_key(self) -> str:
        if self.geocoding_api_key is None or not self.geocoding_api_key.get_secret_value():
            raise ValueError("Google Geocoding API key not found. Set GEOCODING_API_KEY")
        return self.geocoding_api_key.get_secret_value()
