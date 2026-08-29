from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SiteInput(BaseModel):
    site_id: str | None = None
    name: str | None = None
    latitude: float
    longitude: float
    capacity: int = Field(default=0, ge=0)


class SitingOptimizeRequest(BaseModel):
    algorithm_type: str = Field(default="GA")
    period: str = Field(default="morning")
    target_sites_count: int = Field(default=5, ge=1)
    service_radius: float = Field(default=120.0, gt=0)
    include_process: bool = Field(
        default=False,
        description="Whether to reserve and return algorithm process visualization metadata. / 是否返回算法过程可视化所需的运行信息。",
    )


class SitingOptimizeResponse(BaseModel):
    status: str = "mock"
    algorithm_type: str
    period: str
    optimal_sites: dict[str, Any]
    coverage_areas: dict[str, Any]
    global_metrics: dict[str, Any]
    process_available: bool = False
    run_id: str | None = None
    process_summary: dict[str, Any] | None = None
    process_states: list[dict[str, Any]] | None = None


class SitingEvaluateRequest(BaseModel):
    current_sites: list[SiteInput] = Field(default_factory=list)
    period: str = Field(default="morning")
    service_radius: float = Field(default=120.0, gt=0)


class SitingEvaluateResponse(BaseModel):
    status: str = "mock"
    period: str
    evaluated_sites_count: int
    coverage_areas: dict[str, Any]
    global_metrics: dict[str, Any]