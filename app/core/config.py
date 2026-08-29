from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "WHU Electrical Bike Backend / 武汉大学校园电单车后端"
    app_version: str = "0.3.0"
    api_prefix: str = "/api"
    data_dir_name: str = "whu_spatial_data"
    scheme_dir_name: str = "schemes"
    log_dir_name: str = "log"
    storage_backend: str = "file"
    cors_allow_origins: tuple[str, ...] = ("*",)

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def data_dir(self) -> Path:
        return self.base_dir / self.data_dir_name

    @property
    def scheme_dir(self) -> Path:
        return self.data_dir / self.scheme_dir_name

    @property
    def log_dir(self) -> Path:
        return self.base_dir / self.log_dir_name


settings = Settings()
