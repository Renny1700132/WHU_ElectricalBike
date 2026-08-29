from __future__ import annotations

from pydantic import BaseModel, Field


class HeatmapResponse(BaseModel):
    status: str = "mock"
    period: str
    points: list[list[float]] = Field(
        default_factory=list,
        description="[lat, lng, weight] records for frontend heatmap rendering. / 用于前端热力图渲染的点位数组。",
    )
