"""Configurações de ingestão (lê .env via pydantic-settings)."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql://quantopagou:quantopagou_dev@localhost:5433/quantopagou",
        alias="DATABASE_URL",
    )
    compras_api_base: str = Field(
        default="https://dadosabertos.compras.gov.br",
        alias="COMPRAS_API_BASE",
    )
    snapshots_dir: Path = Field(default=Path("./snapshots"), alias="SNAPSHOTS_DIR")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


settings = Settings()
