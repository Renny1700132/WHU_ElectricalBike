from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.algorithm.manual_evaluation import evaluate_manual_sites
from app.algorithm.siting_optimization import run_siting_optimization
from app.schemas.siting import (
    SitingEvaluateRequest,
    SitingEvaluateResponse,
    SitingOptimizeRequest,
    SitingOptimizeResponse,
)

router = APIRouter()


@router.post(
    "/siting/optimize",
    response_model=SitingOptimizeResponse,
    summary="Optimize Siting Layout / 智能选址优化",
    description="Run the real siting optimization algorithm and optionally return process states. / 运行真实选址优化算法，并可返回过程可视化状态。",
)
def optimize_siting(payload: SitingOptimizeRequest) -> SitingOptimizeResponse:
    try:
        result = run_siting_optimization(
            algorithm_type=payload.algorithm_type,
            period=payload.period,
            target_sites_count=payload.target_sites_count,
            service_radius=payload.service_radius,
            include_process=payload.include_process,
        )
        return SitingOptimizeResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/siting/evaluate",
    response_model=SitingEvaluateResponse,
    summary="Evaluate Manual Siting / 人工选址评估",
    description="Evaluate a manually edited siting plan. / 对人工编辑的选址方案进行评估。",
)
def evaluate_siting(payload: SitingEvaluateRequest) -> SitingEvaluateResponse:
    try:
        result = evaluate_manual_sites(
            current_sites=payload.current_sites,
            period=payload.period,
            service_radius=payload.service_radius,
        )
        return SitingEvaluateResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))