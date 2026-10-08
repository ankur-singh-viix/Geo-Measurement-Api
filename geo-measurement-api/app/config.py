from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "Geospatial File Measurement API"
    database_url: str = f"sqlite:///{BASE_DIR / 'geo_api.db'}"
    upload_dir: Path = BASE_DIR / "uploads"
    max_upload_size_mb: int = 50
    allowed_extensions: tuple = (".zip", ".kml")

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
