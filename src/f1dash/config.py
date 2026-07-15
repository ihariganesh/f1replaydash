from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "F1 Dash API"
    app_env: str = "dev"
    fastf1_cache_dir: str = ".cache/fastf1"
    snapshot_dir: str = ".cache/snapshots"
    export_dir: str = "exports"
    redis_url: str | None = None
    cache_ttl_seconds: int = 900

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def fastf1_cache_path(self) -> Path:
        return Path(self.fastf1_cache_dir).resolve()

    @property
    def snapshot_path(self) -> Path:
        return Path(self.snapshot_dir).resolve()

    @property
    def export_path(self) -> Path:
        return Path(self.export_dir).resolve()


settings = Settings()
