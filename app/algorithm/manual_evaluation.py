from __future__ import annotations

from app.algorithm.demand_prediction import build_demand_points
from app.algorithm.siting_optimization import (
    build_coverage_areas,
    build_distance_matrix,
    compute_site_service_stats,
    evaluate_solution,
)


def normalize_manual_sites(current_sites: list) -> list[dict]:
    normalized = []

    for idx, site in enumerate(current_sites, start=1):
        # 兼容 Pydantic model / dict 两种输入
        if hasattr(site, "model_dump"):
            raw = site.model_dump()
        elif hasattr(site, "dict"):
            raw = site.dict()
        else:
            raw = dict(site)

        normalized.append({
            "site_id": raw.get("site_id") or f"manual_{idx}",
            "name": raw.get("name") or f"manual_site_{idx}",
            "type": "manual",
            "x": raw["longitude"],
            "y": raw["latitude"],
            "capacity": raw.get("capacity", 0),
        })

    return normalized


def evaluate_manual_sites(
    current_sites: list,
    period: str = "morning",
    service_radius: float = 120.0,
) -> dict:
    if period not in {"morning", "noon", "evening"}:
        raise ValueError("period 必须为 morning / noon / evening")

    selected_sites = normalize_manual_sites(current_sites)

    if not selected_sites:
        return {
            "status": "success",
            "period": period,
            "evaluated_sites_count": 0,
            "coverage_areas": {"type": "FeatureCollection", "features": []},
            "global_metrics": {
                "coverage_rate": 0.0,
                "avg_walk_distance": 0.0,
                "fitness": 0.0,
                "period": period,
            },
        }

    demand_points = build_demand_points()
    distance_matrix = build_distance_matrix(demand_points, selected_sites)

    _, metrics = evaluate_solution(
        selected_sites=selected_sites,
        demand_points=demand_points,
        distance_matrix=distance_matrix,
        service_radius=service_radius,
        period=period,
    )

    site_stats = compute_site_service_stats(
        selected_sites=selected_sites,
        demand_points=demand_points,
        distance_matrix=distance_matrix,
        service_radius=service_radius,
        period=period,
    )

    metrics["period"] = period

    return {
        "status": "success",
        "period": period,
        "evaluated_sites_count": len(selected_sites),
        "coverage_areas": build_coverage_areas(
            selected_sites,
            service_radius,
            site_stats=site_stats,
        ),
        "global_metrics": metrics,
    }