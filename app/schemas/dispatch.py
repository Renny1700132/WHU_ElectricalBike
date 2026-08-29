from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import PeriodEnum


class DispatchStatusItem(BaseModel):
    site_id: str
    site_name: str
    current_bikes: int = Field(ge=0)
    predicted_demand: int = Field(ge=0)
    inbound: int
    outbound: int


class DispatchStatusResponse(BaseModel):
    status: str = "mock"
    period: str
    stations: list[DispatchStatusItem] = Field(default_factory=list)


class DispatchSiteInput(BaseModel):
    site_id: str | None = None
    name: str | None = None
    latitude: float
    longitude: float
    capacity: int = Field(default=0, ge=0)


class DispatchOptimizeRequest(BaseModel):
    period: PeriodEnum
    algorithm_type: str = Field(default="GA")
    include_process: bool = Field(
        default=False,
        description="Whether to reserve and return algorithm process visualization metadata. / 是否返回算法过程可视化所需的运行信息。",
    )
    current_sites: list[DispatchSiteInput] = Field(default_factory=list)


class DispatchOptimizeResponse(BaseModel):
    status: str = "mock"
    period: str
    algorithm_type: str
    stations: list[dict[str, Any]] = Field(default_factory=list)
    dispatch_routes: dict[str, Any]
    transfer_plan: list[dict[str, Any]] = Field(default_factory=list)
    efficiency_metrics: dict[str, Any]
    process_available: bool = False
    run_id: str | None = None
    process_summary: dict[str, Any] | None = None
    process_states: list[dict[str, Any]] | None = None