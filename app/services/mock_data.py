from __future__ import annotations

import csv
import io
import json
import math
from typing import Any

from app.schemas.common import AlgorithmDomainEnum, PeriodEnum
from app.schemas.siting import SiteInput
from app.services.process_registry import register_algorithm_run

ENABLE_REAL_ALGO = {
    "siting_optimize": False,
    "siting_evaluate": False,
    "dispatch_status": False,
    "dispatch_optimize": False,
}

MOCK_SITE_POINTS = [
    {"site_id": "S1", "name": "Teaching Zone", "lat": 30.5392, "lng": 114.3651, "capacity": 40},
    {"site_id": "S2", "name": "Dormitory East", "lat": 30.5378, "lng": 114.3705, "capacity": 56},
    {"site_id": "S3", "name": "Library Hub", "lat": 30.5411, "lng": 114.3618, "capacity": 35},
    {"site_id": "S4", "name": "North Gate", "lat": 30.5436, "lng": 114.3669, "capacity": 28},
]

HEATMAP_POINTS = {
    PeriodEnum.morning: [[30.5396, 114.3644, 0.92], [30.5412, 114.3622, 0.78], [30.5374, 114.3701, 0.85]],
    PeriodEnum.noon: [[30.5401, 114.3662, 0.66], [30.5387, 114.3683, 0.71], [30.5419, 114.3608, 0.58]],
    PeriodEnum.evening: [[30.5379, 114.3711, 0.95], [30.5432, 114.3661, 0.74], [30.5390, 114.3630, 0.62]],
}


def build_heatmap(period: PeriodEnum) -> dict[str, Any]:
    return {"status": "mock", "period": period.value, "points": HEATMAP_POINTS[period]}


def _point_feature(site_id: str, name: str, lat: float, lng: float, capacity: int, served_people: int) -> dict[str, Any]:
    return {
        "type": "Feature",
        "properties": {"site_id": site_id, "name": name, "capacity": capacity, "served_people": served_people},
        "geometry": {"type": "Point", "coordinates": [lng, lat]},
    }


def _circle_polygon(lat: float, lng: float, radius_m: float, steps: int = 20) -> list[list[list[float]]]:
    lat_step = radius_m / 111_320
    lng_step = radius_m / (111_320 * max(math.cos(math.radians(lat)), 0.2))
    ring: list[list[float]] = []
    for index in range(steps):
        angle = (2 * math.pi * index) / steps
        ring.append([lng + lng_step * math.cos(angle), lat + lat_step * math.sin(angle)])
    ring.append(ring[0])
    return [ring]


def _coverage_feature(site_id: str, name: str, lat: float, lng: float, radius_m: float) -> dict[str, Any]:
    return {
        "type": "Feature",
        "properties": {"site_id": site_id, "name": name, "service_radius": radius_m},
        "geometry": {"type": "Polygon", "coordinates": _circle_polygon(lat, lng, radius_m)},
    }


def _attach_process_metadata(payload: dict[str, Any], domain: AlgorithmDomainEnum, algorithm_type: str, include_process: bool) -> dict[str, Any]:
    payload["process_available"] = True
    if not include_process:
        payload.setdefault("run_id", None)
        payload.setdefault("process_summary", None)
        return payload
    run = register_algorithm_run(domain=domain, algorithm_type=algorithm_type, total_iterations=8)
    payload["run_id"] = run["run_id"]
    payload["process_summary"] = {
        "run_id": run["run_id"],
        "domain": run["domain"],
        "algorithm_type": run["algorithm_type"],
        "status": run["status"],
        "total_iterations": run["total_iterations"],
        "current_iteration": run["current_iteration"],
        "available_artifacts": run["available_artifacts"],
    }
    return payload


def build_siting_optimize_response(algorithm_type: str, target_sites_count: int, service_radius: float, include_process: bool = False) -> dict[str, Any]:
    if ENABLE_REAL_ALGO.get("siting_optimize"):
        try:
            from app.algorithm.siting_optimization import run_siting_optimization
            return run_siting_optimization(algorithm_type=algorithm_type, target_sites_count=target_sites_count, service_radius=service_radius, include_process=include_process)
        except (ImportError, NotImplementedError) as error:
            print(f"[Warning] 真实选址算法加载失败，退回 Mock 模式。错误: {error}")
    selected = MOCK_SITE_POINTS[: min(target_sites_count, len(MOCK_SITE_POINTS))]
    optimal_sites = {"type": "FeatureCollection", "features": [_point_feature(site["site_id"], site["name"], site["lat"], site["lng"], site["capacity"], served_people=site["capacity"] * 3) for site in selected]}
    coverage_areas = {"type": "FeatureCollection", "features": [_coverage_feature(site["site_id"], site["name"], site["lat"], site["lng"], service_radius) for site in selected]}
    global_metrics = {"coverage_ratio": 0.84, "average_walking_distance": 108.5, "service_radius": service_radius, "candidate_sites_count": target_sites_count, "algorithm_state": "stub_result"}
    payload = {"status": "mock", "algorithm_type": algorithm_type, "optimal_sites": optimal_sites, "coverage_areas": coverage_areas, "global_metrics": global_metrics}
    return _attach_process_metadata(payload, AlgorithmDomainEnum.siting, algorithm_type, include_process)


def build_siting_evaluate_response(current_sites: list[SiteInput]) -> dict[str, Any]:
    if ENABLE_REAL_ALGO.get("siting_evaluate"):
        try:
            from app.algorithm.manual_evaluation import evaluate_manual_sites
            return evaluate_manual_sites(current_sites)
        except (ImportError, NotImplementedError) as error:
            print(f"[Warning] 人工选址评估计算失败，退回 Mock 模式。错误: {error}")
    sites = current_sites or [SiteInput(site_id=site["site_id"], name=site["name"], latitude=site["lat"], longitude=site["lng"], capacity=site["capacity"]) for site in MOCK_SITE_POINTS[:3]]
    coverage_areas = {"type": "FeatureCollection", "features": [_coverage_feature(site.site_id or f"manual-{index + 1}", site.name or f"Manual Site {index + 1}", site.latitude, site.longitude, 100.0) for index, site in enumerate(sites)]}
    global_metrics = {"coverage_ratio": round(min(0.55 + len(sites) * 0.08, 0.96), 2), "average_walking_distance": max(180 - len(sites) * 12, 90), "site_balance_index": round(0.75 + len(sites) * 0.03, 2), "algorithm_state": "manual_evaluation_stub"}
    return {"status": "mock", "evaluated_sites_count": len(sites), "coverage_areas": coverage_areas, "global_metrics": global_metrics}


def build_dispatch_status(period: PeriodEnum) -> dict[str, Any]:
    if ENABLE_REAL_ALGO.get("dispatch_status"):
        try:
            from app.algorithm.demand_prediction import predict_demand
            return predict_demand(period)
        except (ImportError, NotImplementedError) as error:
            print(f"[Warning] 需求预测模型加载失败，退回 Mock 模式。错误: {error}")
    period_bias = {PeriodEnum.morning: (12, 28, 10), PeriodEnum.noon: (18, 18, 4), PeriodEnum.evening: (26, 14, -8)}[period]
    stations = []
    for index, site in enumerate(MOCK_SITE_POINTS, start=1):
        current_bikes = period_bias[0] + index * 3
        predicted_demand = period_bias[1] + index * 2
        delta = predicted_demand - current_bikes + period_bias[2]
        stations.append({"site_id": site["site_id"], "site_name": site["name"], "current_bikes": current_bikes, "predicted_demand": predicted_demand, "inbound": max(delta, 0), "outbound": max(-delta, 0)})
    return {"status": "mock", "period": period.value, "stations": stations}


def build_dispatch_optimize_response(period: PeriodEnum, algorithm_type: str, include_process: bool = False) -> dict[str, Any]:
    if ENABLE_REAL_ALGO.get("dispatch_optimize"):
        try:
            from app.algorithm.dispatch_routing import run_dispatch_routing
            return run_dispatch_routing(period=period, algorithm_type=algorithm_type, include_process=include_process)
        except (ImportError, NotImplementedError) as error:
            print(f"[Warning] 调度路径优化算法加载失败，退回 Mock 模式。错误: {error}")
    route_features = []
    transfer_plan = []
    for index in range(len(MOCK_SITE_POINTS) - 1):
        start = MOCK_SITE_POINTS[index]
        end = MOCK_SITE_POINTS[index + 1]
        route_features.append({"type": "Feature", "properties": {"vehicle_id": f"V{index + 1}", "from_site": start["site_id"], "to_site": end["site_id"], "transfer_count": 6 + index * 2}, "geometry": {"type": "LineString", "coordinates": [[start["lng"], start["lat"]], [end["lng"], end["lat"]]]}})
        transfer_plan.append({"vehicle_id": f"V{index + 1}", "from_site": start["site_id"], "to_site": end["site_id"], "transfer_count": 6 + index * 2, "estimated_duration_min": 9 + index * 3})
    efficiency_metrics = {"total_distance_km": 4.8, "total_duration_min": 36, "estimated_cost": 128.0, "supply_demand_balance_rate": 0.88, "algorithm_state": "dispatch_stub"}
    payload = {"status": "mock", "period": period.value, "algorithm_type": algorithm_type, "dispatch_routes": {"type": "FeatureCollection", "features": route_features}, "transfer_plan": transfer_plan, "efficiency_metrics": efficiency_metrics}
    return _attach_process_metadata(payload, AlgorithmDomainEnum.dispatch, algorithm_type, include_process)


def build_analysis_metrics(scheme_id: str | None) -> dict[str, Any]:
    return {"status": "mock", "scheme_id": scheme_id, "summary": {"coverage_ratio": 0.84, "service_radius": 120, "balance_score": 0.81}, "charts": {"coverage_bar": [{"label": "manual", "value": 0.73}, {"label": "optimized", "value": 0.84}], "period_line": [{"period": "morning", "coverage": 0.79}, {"period": "noon", "coverage": 0.82}, {"period": "evening", "coverage": 0.84}]}}


def build_export_content(file_format: str, scheme_data: dict[str, Any]) -> tuple[str, str, bytes]:
    if file_format == "geojson":
        content = json.dumps(scheme_data, ensure_ascii=False, indent=2).encode("utf-8")
        return "application/geo+json", "geojson", content
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["key", "value"])
    for key, value in scheme_data.items():
        serialized = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
        writer.writerow([key, serialized])
    return "text/csv; charset=utf-8", "csv", buffer.getvalue().encode("utf-8")
