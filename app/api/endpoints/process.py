from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas.process import AlgorithmCapabilitiesResponse, AlgorithmRunDetailResponse, AlgorithmStateDetailResponse, AlgorithmStateListResponse
from app.services.process_registry import get_algorithm_capabilities, get_run_detail, get_run_state, list_run_states


router = APIRouter()


@router.get(
    "/algorithms/process-capabilities",
    response_model=AlgorithmCapabilitiesResponse,
    summary="Get Algorithm Process Capabilities / 获取算法过程可视化能力",
    description="Describe which algorithm domains support process visualization and what artifacts can be displayed. / 描述哪些算法域支持过程可视化，以及可展示的中间产物类型。",
)
def get_process_capabilities() -> AlgorithmCapabilitiesResponse:
    return AlgorithmCapabilitiesResponse(capabilities=get_algorithm_capabilities())


@router.get(
    "/algorithms/runs/{run_id}",
    response_model=AlgorithmRunDetailResponse,
    summary="Get Algorithm Run Detail / 获取算法运行详情",
    description="Get summary metadata for one algorithm run. / 获取单个算法运行记录的摘要信息。",
)
def get_algorithm_run_detail(run_id: str) -> AlgorithmRunDetailResponse:
    return AlgorithmRunDetailResponse(run=get_run_detail(run_id))


@router.get(
    "/algorithms/runs/{run_id}/states",
    response_model=AlgorithmStateListResponse,
    summary="List Algorithm States / 获取算法过程状态列表",
    description="List iteration states for one algorithm run. / 获取单个算法运行记录的迭代状态列表。",
)
def get_algorithm_run_states(run_id: str, limit: int | None = Query(default=None, ge=1, description="Maximum number of states to return. / 最多返回多少条状态记录。")) -> AlgorithmStateListResponse:
    run, states = list_run_states(run_id, limit=limit)
    return AlgorithmStateListResponse(run=run, total_states=len(states), states=states)


@router.get(
    "/algorithms/runs/{run_id}/states/{iteration}",
    response_model=AlgorithmStateDetailResponse,
    summary="Get Algorithm State Detail / 获取算法过程单步详情",
    description="Get one iteration state for one algorithm run. / 获取单个算法运行记录中的某一步迭代详情。",
)
def get_algorithm_state_detail(run_id: str, iteration: int) -> AlgorithmStateDetailResponse:
    run, state = get_run_state(run_id, iteration)
    return AlgorithmStateDetailResponse(run=run, state=state)
