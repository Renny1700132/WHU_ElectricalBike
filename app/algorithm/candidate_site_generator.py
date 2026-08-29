from __future__ import annotations

from app.algorithm.demand_prediction import build_demand_points


CANDIDATE_ALLOWED_TYPES = {
    "dorm",
    "teaching",
    "canteen",
    "library",
    "sports",
    "gate",
}


def build_candidate_sites() -> list[dict]:
    """
    第一版候选停车点生成：
    直接从高价值 POI 需求点中筛选候选站点。
    """
    demand_points = build_demand_points()
    candidate_sites = []

    for dp in demand_points:
        if dp["type"] not in CANDIDATE_ALLOWED_TYPES:
            continue

        candidate_sites.append({
            "site_id": f's_{dp["source_poi_id"]}',
            "name": dp["name"],
            "type": dp["type"],
            "x": dp["x"],
            "y": dp["y"],
            "source_demand_id": dp["demand_id"],
            "source_poi_id": dp["source_poi_id"],
        })

    return candidate_sites