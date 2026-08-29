from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas.analysis import AnalysisMetricsResponse
from app.services.mock_data import build_analysis_metrics


router = APIRouter()


@router.get(
    "/analysis/metrics",
    response_model=AnalysisMetricsResponse,
    summary="Get Analysis Metrics / 获取分析指标",
    description="Return analysis summary and chart-ready data. Current response is mock data for frontend integration. / 返回分析摘要和图表数据，当前为前端联调用占位数据。",
)
def get_analysis_metrics(
    scheme_id: str | None = Query(default=None, description="Optional scheme identifier. / 可选方案 ID。"),
) -> AnalysisMetricsResponse:
    return AnalysisMetricsResponse(**build_analysis_metrics(scheme_id))
