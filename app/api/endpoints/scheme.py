from __future__ import annotations

from fastapi import APIRouter

from app.schemas.scheme import (
    SchemeDeleteResponse,
    SchemeDetail,
    SchemeListResponse,
    SchemePayload,
    SchemeSaveResponse,
)
from app.services.scheme_storage import get_scheme_repository


router = APIRouter()


@router.get(
    "/schemes",
    response_model=SchemeListResponse,
    summary="List Saved Schemes / 获取已保存方案列表",
    description="List all locally saved schemes. This file-based implementation is designed to be replaceable by a database repository later. / 获取本地已保存方案列表，当前为文件存储实现，后续可替换为数据库仓储实现。",
)
def list_schemes() -> SchemeListResponse:
    repository = get_scheme_repository()
    items = repository.list_schemes()
    return SchemeListResponse(total=len(items), items=items)


@router.post(
    "/schemes",
    response_model=SchemeSaveResponse,
    summary="Save Scheme / 保存方案",
    description="Persist a scheme to local file storage under whu_spatial_data/schemes. / 将方案保存到 whu_spatial_data/schemes 本地文件目录。",
)
def save_scheme(payload: SchemePayload) -> SchemeSaveResponse:
    repository = get_scheme_repository()
    item = repository.save_scheme(payload)
    return SchemeSaveResponse(item=item)


@router.get(
    "/schemes/{scheme_id}",
    response_model=SchemeDetail,
    summary="Get Scheme Detail / 获取方案详情",
    description="Load one saved scheme from local storage. / 从本地存储加载单个方案。",
)
def get_scheme(scheme_id: str) -> SchemeDetail:
    repository = get_scheme_repository()
    return repository.get_scheme(scheme_id)


@router.delete(
    "/schemes/{scheme_id}",
    response_model=SchemeDeleteResponse,
    summary="Delete Scheme / 删除方案",
    description="Delete one saved scheme from local file storage. / 从本地文件存储中删除单个方案。",
)
def delete_scheme(scheme_id: str) -> SchemeDeleteResponse:
    repository = get_scheme_repository()
    repository.delete_scheme(scheme_id)
    return SchemeDeleteResponse(scheme_id=scheme_id)
