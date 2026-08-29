from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import AlgorithmDomainEnum


class AlgorithmCapability(BaseModel):
    domain: AlgorithmDomainEnum
    supported_algorithms: list[str] = Field(default_factory=list)
    process_supported: bool = True
    visualization_notes: str


class AlgorithmCapabilitiesResponse(BaseModel):
    status: str = "ready"
    capabilities: list[AlgorithmCapability] = Field(default_factory=list)


class AlgorithmRunSummary(BaseModel):
    run_id: str
    domain: AlgorithmDomainEnum
    algorithm_type: str
    status: str
    total_iterations: int
    current_iteration: int
    created_at: datetime
    supports_process_visualization: bool = True
    available_artifacts: list[str] = Field(default_factory=list)


class AlgorithmRunDetail(AlgorithmRunSummary):
    latest_metrics: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None


class AlgorithmRunDetailResponse(BaseModel):
    status: str = "ready"
    run: AlgorithmRunDetail


class AlgorithmIterationState(BaseModel):
    iteration: int
    stage_name: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    artifacts: dict[str, Any] = Field(default_factory=dict)


class AlgorithmStateListResponse(BaseModel):
    status: str = "ready"
    run: AlgorithmRunDetail
    total_states: int
    states: list[AlgorithmIterationState] = Field(default_factory=list)


class AlgorithmStateDetailResponse(BaseModel):
    status: str = "ready"
    run: AlgorithmRunDetail
    state: AlgorithmIterationState
