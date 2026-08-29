from __future__ import annotations

from app.algorithm.data_loader import load_pois_geojson


POI_BASE_WEIGHT = {
    "dorm": 100,
    "teaching": 90,
    "canteen": 75,
    "gate": 85,
    "library": 65,
    "sports": 55,
    "office": 35,
    "other": 20,
}

TIME_FACTORS = {
    "morning": {
        "dorm": 1.4,
        "teaching": 1.2,
        "canteen": 0.7,
        "gate": 1.1,
        "library": 0.8,
        "sports": 0.5,
        "office": 0.8,
        "other": 0.7,
    },
    "noon": {
        "dorm": 0.7,
        "teaching": 1.0,
        "canteen": 1.4,
        "gate": 0.6,
        "library": 0.9,
        "sports": 0.7,
        "office": 0.8,
        "other": 0.8,
    },
    "evening": {
        "dorm": 1.3,
        "teaching": 0.8,
        "canteen": 1.1,
        "gate": 0.8,
        "library": 1.0,
        "sports": 0.9,
        "office": 0.5,
        "other": 0.7,
    },
}


def is_missing(value) -> bool:
    return value is None or str(value).strip().lower() in {"", "nan", "none", "null"}


def normalize_poi_type(properties: dict) -> str:
    """
    基于当前 WHU POI 数据的实际字段做分类：
    1. 优先看 building
    2. 再看 name 关键词
    3. 都不满足则归为 other
    """
    name = "" if is_missing(properties.get("name")) else str(properties.get("name")).strip()
    building = "" if is_missing(properties.get("building")) else str(properties.get("building")).strip().lower()
    amenity = "" if is_missing(properties.get("amenity")) else str(properties.get("amenity")).strip().lower()

    # 1) 先按 building 判断
    if building == "dormitory":
        return "dorm"
    if building == "university":
        return "teaching"
    if building == "office":
        return "office"

    # 2) 再按 amenity 判断（预留）
    if amenity in {"library"}:
        return "library"
    if amenity in {"restaurant", "canteen", "food_court", "fast_food"}:
        return "canteen"

    # 3) 再按中文名称关键词判断
    dorm_keywords = ["宿舍", "一舍", "二舍", "三舍", "四舍", "五舍", "六舍", "七舍", "八舍", "九舍", "十舍", "十一舍", "十二舍", "十三舍", "十四舍", "十五舍", "十六舍", "十七舍", "十八舍", "十九舍", "20舍", "21舍", "22舍", "23舍", "24舍"]
    teaching_keywords = ["教学楼", "教一", "教二", "教三", "教四", "教五", "教六", "学院", "实验楼", "教学中心"]
    canteen_keywords = ["食堂", "餐厅", "餐饮", "美食"]
    gate_keywords = ["门", "校门", "出入口"]
    library_keywords = ["图书馆"]
    sports_keywords = ["体育馆", "操场", "运动场", "球场", "风雨馆", "体育"]
    office_keywords = ["办公", "行政", "教研室", "办公室"]

    if any(k in name for k in dorm_keywords):
        return "dorm"
    if any(k in name for k in teaching_keywords):
        return "teaching"
    if any(k in name for k in canteen_keywords):
        return "canteen"
    if any(k in name for k in gate_keywords):
        return "gate"
    if any(k in name for k in library_keywords):
        return "library"
    if any(k in name for k in sports_keywords):
        return "sports"
    if any(k in name for k in office_keywords):
        return "office"

    # 4) building=yes 这种模糊情况，尽量靠 name 识别，识别不了就 other
    return "other"


def build_demand_points() -> list[dict]:
    pois_geojson = load_pois_geojson()
    features = pois_geojson.get("features", [])

    demand_points = []

    for feature in features:
        geometry = feature.get("geometry", {})
        properties = feature.get("properties", {})

        if geometry.get("type") != "Point":
            continue

        coords = geometry.get("coordinates", [])
        if len(coords) < 2:
            continue

        poi_type = normalize_poi_type(properties)
        base_weight = POI_BASE_WEIGHT[poi_type]

        demand_points.append({
            "demand_id": f'd_{properties.get("id")}',
            "source_poi_id": properties.get("id"),
            "name": properties.get("name", ""),
            "type": poi_type,
            "x": coords[0],   # lon
            "y": coords[1],   # lat
            "base_weight": base_weight,
            "demand": {
                "morning": round(base_weight * TIME_FACTORS["morning"][poi_type], 2),
                "noon": round(base_weight * TIME_FACTORS["noon"][poi_type], 2),
                "evening": round(base_weight * TIME_FACTORS["evening"][poi_type], 2),
            },
            "raw_building": properties.get("building"),
            "raw_amenity": properties.get("amenity"),
        })

    return demand_points


def predict_demand(period: str) -> dict:
    if period not in {"morning", "noon", "evening"}:
        raise ValueError("period 必须为 morning / noon / evening")

    demand_points = build_demand_points()

    return {
        "status": "success",
        "period": period,
        "demand_points": [
            {
                "demand_id": dp["demand_id"],
                "name": dp["name"],
                "type": dp["type"],
                "x": dp["x"],
                "y": dp["y"],
                "predicted_demand": dp["demand"][period],
            }
            for dp in demand_points
        ],
    }


def build_prediction_process_states(model_output: dict) -> list[dict]:
    return [
        {
            "iteration": 1,
            "stage_name": "rule_based_demand_estimation",
            "metrics": {
                "period": model_output.get("period"),
                "demand_points_count": len(model_output.get("demand_points", [])),
            },
            "artifacts": {},
        }
    ]

def build_heatmap_output(period: str) -> dict:
    """
    基于真实需求点构造热力图输出。
    输出结构与 HeatmapResponse 兼容：
    points = [[lat, lng, weight], ...]
    """
    model_output = predict_demand(period)

    heatmap_points = []
    for dp in model_output["demand_points"]:
        heatmap_points.append([
            dp["y"],                  # latitude
            dp["x"],                  # longitude
            dp["predicted_demand"],   # weight
        ])

    return {
        "status": "success",
        "period": period,
        "points": heatmap_points,
    }