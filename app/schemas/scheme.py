from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import SchemeTypeEnum


class SchemePayload(BaseModel):
    name: str = Field(..., min_length=1, description="Scheme name / 方案名称")
    scheme_type: SchemeTypeEnum = Field(..., description="Scheme type / 方案类型")
    description: str | None = Field(default=None, description="Scheme description / 方案描述")
    scheme_data: dict[str, Any] = Field(default_factory=dict, description="Full scheme payload / 完整方案数据")


class SchemeSummary(BaseModel):
    scheme_id: str
    name: str
    scheme_type: SchemeTypeEnum
    description: str | None = None
    file_path: str
    created_at: datetime
    updated_at: datetime
    storage_backend: str = "file"


class SchemeDetail(SchemeSummary):
    scheme_data: dict[str, Any] = Field(default_factory=dict)


class SchemeListResponse(BaseModel):
    status: str = "ready"
    total: int
    items: list[SchemeSummary] = Field(default_factory=list)


class SchemeSaveResponse(BaseModel):
    status: str = "saved"
    item: SchemeDetail


class SchemeDeleteResponse(BaseModel):
    status: str = "deleted"
    scheme_id: str
