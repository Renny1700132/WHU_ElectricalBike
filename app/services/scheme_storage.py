from __future__ import annotations

import json
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.scheme import SchemeDetail, SchemePayload, SchemeSummary


class SchemeRepository(ABC):
    """Repository abstraction to keep future database migration straightforward."""

    @abstractmethod
    def list_schemes(self) -> list[SchemeSummary]:
        raise NotImplementedError

    @abstractmethod
    def get_scheme(self, scheme_id: str) -> SchemeDetail:
        raise NotImplementedError

    @abstractmethod
    def save_scheme(self, payload: SchemePayload) -> SchemeDetail:
        raise NotImplementedError

    @abstractmethod
    def delete_scheme(self, scheme_id: str) -> None:
        raise NotImplementedError


class FileSchemeRepository(SchemeRepository):
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _scheme_path(self, scheme_id: str) -> Path:
        return self.base_dir / f"{scheme_id}.json"

    def _read_detail(self, path: Path) -> SchemeDetail:
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scheme '{path.stem}' not found. / 方案 '{path.stem}' 不存在。",
            )
        payload = json.loads(path.read_text(encoding="utf-8"))
        return SchemeDetail.model_validate(payload)

    def list_schemes(self) -> list[SchemeSummary]:
        items: list[SchemeSummary] = []
        for path in sorted(self.base_dir.glob("*.json")):
            detail = self._read_detail(path)
            items.append(
                SchemeSummary(
                    scheme_id=detail.scheme_id,
                    name=detail.name,
                    scheme_type=detail.scheme_type,
                    description=detail.description,
                    file_path=detail.file_path,
                    created_at=detail.created_at,
                    updated_at=detail.updated_at,
                    storage_backend=detail.storage_backend,
                )
            )
        items.sort(key=lambda item: item.updated_at, reverse=True)
        return items

    def get_scheme(self, scheme_id: str) -> SchemeDetail:
        return self._read_detail(self._scheme_path(scheme_id))

    def save_scheme(self, payload: SchemePayload) -> SchemeDetail:
        scheme_id = uuid.uuid4().hex
        now = datetime.now(UTC)
        path = self._scheme_path(scheme_id)
        detail = SchemeDetail(
            scheme_id=scheme_id,
            name=payload.name,
            scheme_type=payload.scheme_type,
            description=payload.description,
            file_path=str(path),
            created_at=now,
            updated_at=now,
            storage_backend=settings.storage_backend,
            scheme_data=payload.scheme_data,
        )
        path.write_text(detail.model_dump_json(indent=2), encoding="utf-8")
        return detail

    def delete_scheme(self, scheme_id: str) -> None:
        path = self._scheme_path(scheme_id)
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scheme '{scheme_id}' not found. / 方案 '{scheme_id}' 不存在。",
            )
        path.unlink()


def get_scheme_repository() -> SchemeRepository:
    return FileSchemeRepository(settings.scheme_dir)
