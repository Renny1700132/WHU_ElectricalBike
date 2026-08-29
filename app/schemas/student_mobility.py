from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StudentMobilityRequest(BaseModel):
    student_count: int = Field(default=10, ge=1, le=200)
    include_routes: bool = Field(default=True)


class StudentMobilityResponse(BaseModel):
    status: str
    student_count: int
    students: list[dict[str, Any]] = Field(default_factory=list)