from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas.export import ExportSchemeRequest
from app.services.mock_data import build_export_content


router = APIRouter()


@router.post(
    "/export/scheme",
    summary="Export Scheme Data / 导出方案数据",
    description="Export submitted scheme data as CSV or GeoJSON. / 将提交的方案数据导出为 CSV 或 GeoJSON 文件。",
)
def export_scheme(payload: ExportSchemeRequest) -> StreamingResponse:
    media_type, suffix, content = build_export_content(
        file_format=payload.file_format,
        scheme_data=payload.scheme_data,
    )
    filename = f"{payload.file_name}.{suffix}"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(BytesIO(content), media_type=media_type, headers=headers)
