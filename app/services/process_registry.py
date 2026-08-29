from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status

from app.schemas.common import AlgorithmDomainEnum


_ALGORITHM_RUNS: dict[str, dict[str, Any]] = {}


def get_algorithm_capabilities() -> list[dict[str, Any]]:
    return [
        {
            "domain": AlgorithmDomainEnum.siting,
            "supported_algorithms": ["GA", "PSO", "NSGAII", "ACO"],
            "process_supported": True,
            "visualization_notes": "Supports iteration-level candidate sites, fitness metrics, and coverage changes. / 支持按迭代展示候选站点、适应度与覆盖率变化。",
        },
        {
            "domain": AlgorithmDomainEnum.dispatch,
            "supported_algorithms": ["ACO", "GA"],
            "process_supported": True,
            "visualization_notes": "Supports route evolution, transfer plans, and convergence metrics. / 支持路径演化、转运方案和收敛指标展示。",
        },
        {
            "domain": AlgorithmDomainEnum.demand,
            "supported_algorithms": ["LSTM", "STGCN", "MockPredictor"],
            "process_supported": True,
            "visualization_notes": "Supports prediction windows, loss curves, and intermediate demand snapshots. / 支持预测窗口、损失曲线和中间需求快照。",
        },
        {
            "domain": AlgorithmDomainEnum.evaluation,
            "supported_algorithms": ["RuleBased", "CoverageEvaluator"],
            "process_supported": True,
            "visualization_notes": "Supports recalculation steps and metric snapshots for manual edits. / 支持人工编辑后的重算步骤和指标快照展示。",
        },
    ]


def _build_siting_states(total_iterations: int) -> list[dict[str, Any]]:
    states: list[dict[str, Any]] = []
    for iteration in range(1, total_iterations + 1):
        states.append(
            {
                "iteration": iteration,
                "stage_name": f"generation_{iteration}",
                "metrics": {
                    "best_fitness": round(0.62 + iteration * 0.025, 4),
                    "coverage_ratio": round(0.58 + iteration * 0.02, 4),
                    "average_walking_distance": round(180 - iteration * 5.5, 2),
                },
                "artifacts": {
                    "candidate_sites": {
                        "type": "FeatureCollection",
                        "features": [
                            {
                                "type": "Feature",
                                "properties": {"candidate_id": f"C{iteration}-{idx+1}", "score": round(0.7 + idx * 0.03, 3)},
                                "geometry": {"type": "Point", "coordinates": [114.36 + idx * 0.002, 30.538 + iteration * 0.0003]},
                            }
                            for idx in range(3)
                        ],
                    }
                },
            }
        )
    return states


def _build_dispatch_states(total_iterations: int) -> list[dict[str, Any]]:
    states: list[dict[str, Any]] = []
    for iteration in range(1, total_iterations + 1):
        states.append(
            {
                "iteration": iteration,
                "stage_name": f"route_iteration_{iteration}",
                "metrics": {
                    "total_distance_km": round(7.5 - iteration * 0.25, 3),
                    "estimated_cost": round(180 - iteration * 4.2, 2),
                    "balance_rate": round(0.55 + iteration * 0.035, 4),
                },
                "artifacts": {
                    "dispatch_routes": {
                        "type": "FeatureCollection",
                        "features": [
                            {
                                "type": "Feature",
                                "properties": {"vehicle_id": f"V{idx+1}", "iteration": iteration},
                                "geometry": {
                                    "type": "LineString",
                                    "coordinates": [
                                        [114.36 + idx * 0.003, 30.538 + idx * 0.001],
                                        [114.362 + idx * 0.003, 30.5395 + iteration * 0.0002],
                                    ],
                                },
                            }
                            for idx in range(2)
                        ],
                    }
                },
            }
        )
    return states


def _build_generic_states(total_iterations: int, domain: AlgorithmDomainEnum) -> list[dict[str, Any]]:
    states: list[dict[str, Any]] = []
    for iteration in range(1, total_iterations + 1):
        states.append(
            {
                "iteration": iteration,
                "stage_name": f"{domain.value}_iteration_{iteration}",
                "metrics": {
                    "progress": round(iteration / total_iterations, 4),
                    "score": round(0.5 + iteration * 0.04, 4),
                },
                "artifacts": {
                    "snapshot": {
                        "iteration": iteration,
                        "domain": domain.value,
                    }
                },
            }
        )
    return states


def register_algorithm_run(domain: AlgorithmDomainEnum, algorithm_type: str, total_iterations: int = 10) -> dict[str, Any]:
    run_id = uuid.uuid4().hex
    created_at = datetime.now(UTC)

    if domain == AlgorithmDomainEnum.siting:
        states = _build_siting_states(total_iterations)
        artifacts = ["candidate_sites", "coverage_metrics"]
        notes = "Iteration process prepared for siting visualization. / 已为选址过程可视化预留迭代数据。"
    elif domain == AlgorithmDomainEnum.dispatch:
        states = _build_dispatch_states(total_iterations)
        artifacts = ["dispatch_routes", "efficiency_metrics"]
        notes = "Iteration process prepared for dispatch visualization. / 已为调度过程可视化预留迭代数据。"
    else:
        states = _build_generic_states(total_iterations, domain)
        artifacts = ["snapshot"]
        notes = "Generic iterative visualization placeholder. / 通用迭代可视化占位数据。"

    run = {
        "run_id": run_id,
        "domain": domain,
        "algorithm_type": algorithm_type,
        "status": "completed_stub",
        "total_iterations": total_iterations,
        "current_iteration": total_iterations,
        "created_at": created_at,
        "supports_process_visualization": True,
        "available_artifacts": artifacts,
        "latest_metrics": states[-1]["metrics"] if states else {},
        "notes": notes,
        "states": states,
    }
    _ALGORITHM_RUNS[run_id] = run
    return run


def get_run_detail(run_id: str) -> dict[str, Any]:
    run = _ALGORITHM_RUNS.get(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Algorithm run '{run_id}' not found. / 算法运行记录 '{run_id}' 不存在。",
        )
    return {k: v for k, v in run.items() if k != 'states'}


def list_run_states(run_id: str, limit: int | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    run = _ALGORITHM_RUNS.get(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Algorithm run '{run_id}' not found. / 算法运行记录 '{run_id}' 不存在。",
        )
    states = run['states']
    if limit is not None:
        states = states[:limit]
    return get_run_detail(run_id), states


def get_run_state(run_id: str, iteration: int) -> tuple[dict[str, Any], dict[str, Any]]:
    detail, states = list_run_states(run_id)
    for state in states:
        if state['iteration'] == iteration:
            return detail, state
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Iteration {iteration} not found for run '{run_id}'. / 运行 '{run_id}' 中未找到第 {iteration} 次迭代。",
    )
