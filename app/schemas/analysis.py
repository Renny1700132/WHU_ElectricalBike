from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AnalysisMetricsResponse(BaseModel):
    status: str = "mock"
    scheme_id: str | None = None
    summary: dict[str, Any] = Field(default_factory=dict)
    charts: dict[str, Any] = Field(default_factory=dict)
