from __future__ import annotations

from fastapi import APIRouter

from app.schemas.campus import CampusBaseDataResponse
from app.services.data_loader import load_campus_base_data


router = APIRouter()


@router.get(
    "/campus/base-data",
    response_model=CampusBaseDataResponse,
    summary="Get Campus Base Data / 获取校园基础空间数据",
    description="Load road network, buildings, and POIs from local GeoJSON files. / 从本地 GeoJSON 文件加载路网、建筑和兴趣点数据。",
)
def get_campus_base_data() -> CampusBaseDataResponse:
    return CampusBaseDataResponse(**load_campus_base_data())
