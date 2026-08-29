from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas.common import PeriodEnum
from app.schemas.demand import HeatmapResponse
from app.algorithm.demand_prediction import build_heatmap_output


router = APIRouter()


@router.get(
    "/demand/heatmap",
    response_model=HeatmapResponse,
    summary="Get Demand Heatmap / 获取需求热力图",
    description="Return heatmap points for the selected period. Current response is mock data for frontend integration. / 返回指定时段的热力点数据，当前为前端联调用占位数据。",
)
def get_demand_heatmap(
    period: PeriodEnum = Query(..., description="Demand period: morning, noon, evening. / 需求时段：morning、noon、evening。"),
) -> HeatmapResponse:
    period_value = period.value if hasattr(period, "value") else str(period)
    return HeatmapResponse(**build_heatmap_output(period_value))