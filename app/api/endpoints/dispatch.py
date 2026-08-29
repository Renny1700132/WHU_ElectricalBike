from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.algorithm.dispatch_routing import build_site_status, run_dispatch_routing
from app.schemas.common import PeriodEnum
from app.schemas.dispatch import (
    DispatchOptimizeRequest,
    DispatchOptimizeResponse,
    DispatchStatusResponse,
)

router = APIRouter()


@router.get(
    "/dispatch/status",
    response_model=DispatchStatusResponse,
    summary="Get Dispatch Status / 获取调度供需状态",
    description="Return per-site supply and demand status for the selected period. / 返回指定时段各站点供需状态。",
)
def get_dispatch_status(
    period: PeriodEnum = Query(..., description="Dispatch period: morning, noon, evening. / 调度时段：morning、noon、evening。")
) -> DispatchStatusResponse:
    try:
        period_value = period.value if hasattr(period, "value") else str(period)

        stations = build_site_status(period=period_value, site_count=12)
        return DispatchStatusResponse(
            status="success",
            period=period_value,
            stations=stations,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/dispatch/optimize",
    response_model=DispatchOptimizeResponse,
    summary="Optimize Dispatch Routes / 调度路径优化",
    description="Run the dispatch optimization and optionally return process states. / 运行调度优化，并可返回过程状态。",
)
def optimize_dispatch(payload: DispatchOptimizeRequest) -> DispatchOptimizeResponse:
    try:
        period_value = payload.period.value if hasattr(payload.period, "value") else str(payload.period)

        result = run_dispatch_routing(
            period=period_value,
            algorithm_type=payload.algorithm_type,
            include_process=payload.include_process,
            current_sites=payload.current_sites,
        )
        return DispatchOptimizeResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))