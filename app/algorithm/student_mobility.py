from __future__ import annotations

import random
from datetime import datetime, timedelta

from app.algorithm.demand_prediction import build_demand_points
from app.algorithm.road_router import build_road_following_route


COURSE_SLOTS = [
    ("08:00", "08:45"),
    ("08:50", "09:35"),
    ("09:50", "10:35"),
    ("10:40", "11:25"),
    ("11:30", "12:15"),
    ("14:05", "14:50"),
    ("14:55", "15:40"),
    ("15:45", "16:30"),
    ("18:30", "19:15"),
    ("19:20", "20:05"),
    ("20:10", "20:55"),
]

STUDENT_TYPES = [
    "literature_science",
    "engineering",
    "information",
]


def _parse_hhmm(text: str) -> datetime:
    return datetime.strptime(text, "%H:%M")


def _format_hhmm(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def _minutes_between(start: str, end: str) -> int:
    return int((_parse_hhmm(end) - _parse_hhmm(start)).total_seconds() // 60)


def _sample_course_count() -> int:
    roll = random.random()
    if roll < 0.20:
        return 2
    if roll < 0.50:
        return 3
    if roll < 0.80:
        return 4
    if roll < 0.95:
        return 5
    return 6


def _pick_student_type() -> str:
    return random.choice(STUDENT_TYPES)


def _infer_campus_from_name(name: str) -> str:
    name = name or ""
    if "信息学部" in name:
        return "information"
    if "工学部" in name:
        return "engineering"
    return "literature_science"


def _load_poi_groups() -> dict[str, list[dict]]:
    demand_points = build_demand_points()

    groups = {
        "dorm": [],
        "teaching": [],
        "canteen": [],
        "library": [],
        "sports": [],
        "gate": [],
        "other": [],
    }

    for dp in demand_points:
        t = dp["type"]
        if t not in groups:
            groups["other"].append(dp)
        else:
            groups[t].append(dp)

    return groups


def _filter_by_campus(pois: list[dict], campus: str) -> list[dict]:
    filtered = []
    for poi in pois:
        inferred = _infer_campus_from_name(poi.get("name", ""))
        if inferred == campus:
            filtered.append(poi)
    return filtered


def _safe_choice(items: list[dict], fallback: list[dict]) -> dict:
    if items:
        return random.choice(items)
    if fallback:
        return random.choice(fallback)
    raise ValueError("没有可用 POI 可供选择")


def build_student_profiles(student_count: int) -> list[dict]:
    poi_groups = _load_poi_groups()

    profiles = []
    for idx in range(1, student_count + 1):
        student_type = _pick_student_type()

        dorm_candidates = _filter_by_campus(poi_groups["dorm"], student_type)
        dorm_poi = _safe_choice(dorm_candidates, poi_groups["dorm"])

        profiles.append({
            "student_id": f"stu_{idx:03d}",
            "student_type": student_type,
            "home_campus": student_type,
            "dorm_poi": dorm_poi,
        })

    return profiles


def _pick_teaching_poi(student_type: str, teaching_pois: list[dict]) -> dict:
    same_campus = _filter_by_campus(teaching_pois, student_type)

    # 85% 本学部，15% 跨学部
    if same_campus and random.random() < 0.85:
        return random.choice(same_campus)
    return _safe_choice(teaching_pois, same_campus)


def _pick_canteen_poi(student_type: str, canteen_pois: list[dict]) -> dict:
    same_campus = _filter_by_campus(canteen_pois, student_type)
    if same_campus and random.random() < 0.80:
        return random.choice(same_campus)
    return _safe_choice(canteen_pois, same_campus)


def _pick_evening_poi(student_type: str, poi_groups: dict[str, list[dict]], dorm_poi: dict) -> dict:
    # 晚间偏向回本学部
    roll = random.random()
    if roll < 0.45:
        return dorm_poi
    if roll < 0.70 and poi_groups["library"]:
        same = _filter_by_campus(poi_groups["library"], student_type)
        return _safe_choice(same, poi_groups["library"])
    if roll < 0.85 and poi_groups["sports"]:
        same = _filter_by_campus(poi_groups["sports"], student_type)
        return _safe_choice(same, poi_groups["sports"])
    same_canteen = _filter_by_campus(poi_groups["canteen"], student_type)
    return _safe_choice(same_canteen, poi_groups["canteen"])


def generate_daily_events(student_profile: dict) -> list[dict]:
    poi_groups = _load_poi_groups()
    student_type = student_profile["student_type"]
    dorm_poi = student_profile["dorm_poi"]

    course_count = _sample_course_count()
    chosen_slot_indices = sorted(random.sample(range(len(COURSE_SLOTS)), course_count))

    events = []

    # 起始静止事件：宿舍
    events.append({
        "event_id": "start_home",
        "activity_type": "stay",
        "start_time": "07:00",
        "end_time": "07:40",
        "poi": dorm_poi,
        "campus": student_type,
    })

    prev_teaching_poi = None

    for i, slot_idx in enumerate(chosen_slot_indices, start=1):
        start_time, end_time = COURSE_SLOTS[slot_idx]

        # 连续两节大概率同区域
        if prev_teaching_poi and i >= 2:
            prev_slot_idx = chosen_slot_indices[i - 2]
            is_consecutive = slot_idx == prev_slot_idx + 1
            if is_consecutive and random.random() < 0.70:
                teaching_poi = prev_teaching_poi
            else:
                teaching_poi = _pick_teaching_poi(student_type, poi_groups["teaching"])
        else:
            teaching_poi = _pick_teaching_poi(student_type, poi_groups["teaching"])

        events.append({
            "event_id": f"class_{i}",
            "activity_type": "class",
            "start_time": start_time,
            "end_time": end_time,
            "poi": teaching_poi,
            "campus": _infer_campus_from_name(teaching_poi.get("name", "")),
        })

        prev_teaching_poi = teaching_poi

        # 与下一节之间若存在较长空档，插入活动
        if i < len(chosen_slot_indices):
            next_start, _ = COURSE_SLOTS[chosen_slot_indices[i]]
            gap_minutes = _minutes_between(end_time, next_start)
            if gap_minutes >= 60:
                roll = random.random()
                if roll < 0.45 and poi_groups["canteen"]:
                    poi = _pick_canteen_poi(student_type, poi_groups["canteen"])
                    act = "meal"
                elif roll < 0.70 and poi_groups["library"]:
                    same = _filter_by_campus(poi_groups["library"], student_type)
                    poi = _safe_choice(same, poi_groups["library"])
                    act = "library"
                elif roll < 0.85 and poi_groups["sports"]:
                    same = _filter_by_campus(poi_groups["sports"], student_type)
                    poi = _safe_choice(same, poi_groups["sports"])
                    act = "sports"
                else:
                    poi = dorm_poi
                    act = "rest"

                event_start = _format_hhmm(_parse_hhmm(end_time) + timedelta(minutes=10))
                event_end = _format_hhmm(_parse_hhmm(next_start) - timedelta(minutes=10))

                if _parse_hhmm(event_start) < _parse_hhmm(event_end):
                    events.append({
                        "event_id": f"free_{i}",
                        "activity_type": act,
                        "start_time": event_start,
                        "end_time": event_end,
                        "poi": poi,
                        "campus": _infer_campus_from_name(poi.get("name", "")),
                    })

    # 晚间结束事件
    last_end = events[-1]["end_time"]
    evening_poi = _pick_evening_poi(student_type, poi_groups, dorm_poi)

    if _parse_hhmm(last_end) < _parse_hhmm("22:00"):
        evening_start = _format_hhmm(_parse_hhmm(last_end) + timedelta(minutes=15))
        if _parse_hhmm(evening_start) < _parse_hhmm("22:00"):
            events.append({
                "event_id": "evening_activity",
                "activity_type": "evening",
                "start_time": evening_start,
                "end_time": "22:00",
                "poi": evening_poi,
                "campus": _infer_campus_from_name(evening_poi.get("name", "")),
            })

    return sorted(events, key=lambda x: x["start_time"])


def build_student_daily_segments(student_profile: dict, events: list[dict], include_routes: bool = True) -> list[dict]:
    segments = []

    # 跳过第一个 start_home，不给它生成“移动段”
    filtered_events = [e for e in events if e["event_id"] != "start_home"]

    prev_poi = student_profile["dorm_poi"]
    prev_end_time = "07:40"

    for idx, event in enumerate(filtered_events, start=1):
        current_poi = event["poi"]

        same_place = prev_poi["demand_id"] == current_poi["demand_id"]

        start_time = prev_end_time
        end_time = event["start_time"]
        duration_minutes = _minutes_between(start_time, end_time)

        # 时间倒挂，直接跳过这一段
        if duration_minutes < 0:
            prev_poi = current_poi
            prev_end_time = event["end_time"]
            continue

        # 同地点不生成伪移动段
        if same_place:
            prev_poi = current_poi
            prev_end_time = event["end_time"]
            continue

        route_coords, route_distance = build_road_following_route(
            from_lng=prev_poi["x"],
            from_lat=prev_poi["y"],
            to_lng=current_poi["x"],
            to_lat=current_poi["y"],
        )

        segments.append({
            "segment_id": f"{student_profile['student_id']}_seg_{idx:03d}",
            "activity_type": f"move_to_{event['activity_type']}",
            "start_time": start_time,
            "end_time": end_time,
            "from_poi": {
                "id": prev_poi["demand_id"],
                "name": prev_poi["name"],
                "x": prev_poi["x"],
                "y": prev_poi["y"],
                "type": prev_poi["type"],
            },
            "to_poi": {
                "id": current_poi["demand_id"],
                "name": current_poi["name"],
                "x": current_poi["x"],
                "y": current_poi["y"],
                "type": current_poi["type"],
            },
            "route_coords": route_coords if include_routes else [],
            "route_distance": route_distance,
            "duration_minutes": duration_minutes,
        })

        prev_poi = current_poi
        prev_end_time = event["end_time"]

    return segments


def build_student_daily_mobility(student_count: int, include_routes: bool = True) -> list[dict]:
    profiles = build_student_profiles(student_count)

    students = []
    for profile in profiles:
        events = generate_daily_events(profile)
        segments = build_student_daily_segments(profile, events, include_routes=include_routes)

        students.append({
            "student_id": profile["student_id"],
            "student_type": profile["student_type"],
            "home_campus": profile["home_campus"],
            "dorm_poi": {
                "id": profile["dorm_poi"]["demand_id"],
                "name": profile["dorm_poi"]["name"],
                "x": profile["dorm_poi"]["x"],
                "y": profile["dorm_poi"]["y"],
                "type": profile["dorm_poi"]["type"],
            },
            "daily_events": events,
            "segments": segments,
        })

    return students