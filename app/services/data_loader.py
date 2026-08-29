from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from app.core.config import settings


def _read_geojson(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Required data file not found: {path.name} / 缺少必要数据文件：{path.name}",
        )
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=3)
def load_campus_base_data() -> dict[str, Any]:
    road_network = _read_geojson(settings.data_dir / "whu_roads.geojson")
    buildings = _read_geojson(settings.data_dir / "whu_buildings.geojson")
    pois = _read_geojson(settings.data_dir / "whu_pois.geojson")

    metadata = {
        "source": "local_geojson",
        "storage_backend": settings.storage_backend,
        "data_dir": str(settings.data_dir),
        "road_feature_count": len(road_network.get("features", [])),
        "building_feature_count": len(buildings.get("features", [])),
        "poi_feature_count": len(pois.get("features", [])),
    }

    return {
        "status": "ready",
        "message": "Campus base data loaded from local GeoJSON files. / 已从本地 GeoJSON 文件加载校园基础空间数据。",
        "road_network": road_network,
        "buildings": buildings,
        "pois": pois,
        "metadata": metadata,
    }
