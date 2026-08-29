from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ExportSchemeRequest(BaseModel):
    scheme_data: dict[str, Any] = Field(default_factory=dict)
    file_format: Literal["csv", "geojson"] = "csv"
    file_name: str = "scheme_export"
