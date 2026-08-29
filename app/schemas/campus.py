from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CampusBaseDataResponse(BaseModel):
    status: str = "ready"
    message: str = "Campus base data loaded from local GeoJSON files. / 已从本地 GeoJSON 文件加载校园基础空间数据。"
    road_network: dict[str, Any]
    buildings: dict[str, Any]
    pois: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)
