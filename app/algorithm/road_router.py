from __future__ import annotations

import heapq
import json
from functools import lru_cache
from pathlib import Path

from app.algorithm.siting_optimization import haversine_distance


def _node_key(lng: float, lat: float, ndigits: int = 7) -> tuple[float, float]:
    return (round(lng, ndigits), round(lat, ndigits))


@lru_cache(maxsize=1)
def load_road_graph() -> tuple[dict, list[tuple[float, float]]]:
    """
    从 whu_roads.geojson 构建无向路网图。
    返回:
    - graph: {node: [(neighbor, dist), ...]}
    - nodes: 所有节点列表
    """
    project_root = Path(__file__).resolve().parents[2]
    roads_path = project_root / "whu_spatial_data" / "whu_roads.geojson"

    with open(roads_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    graph: dict[tuple[float, float], list[tuple[tuple[float, float], float]]] = {}

    for feat in data.get("features", []):
        geom = feat.get("geometry", {})
        if geom.get("type") != "LineString":
            continue

        coords = geom.get("coordinates", [])
        if len(coords) < 2:
            continue

        props = feat.get("properties", {})
        oneway = str(props.get("oneway", "")).lower() in {"yes", "1", "true"}

        for i in range(len(coords) - 1):
            a = _node_key(coords[i][0], coords[i][1])
            b = _node_key(coords[i + 1][0], coords[i + 1][1])

            dist = haversine_distance(a[0], a[1], b[0], b[1])

            graph.setdefault(a, []).append((b, dist))
            if not oneway:
                graph.setdefault(b, []).append((a, dist))

    nodes = list(graph.keys())
    return graph, nodes


def find_nearest_graph_node(lng: float, lat: float, nodes: list[tuple[float, float]]) -> tuple[float, float]:
    best_node = None
    best_dist = float("inf")

    for node in nodes:
        d = haversine_distance(lng, lat, node[0], node[1])
        if d < best_dist:
            best_dist = d
            best_node = node

    if best_node is None:
        raise ValueError("路网节点为空，无法匹配最近道路节点")

    return best_node


def dijkstra_path(
    graph: dict,
    start: tuple[float, float],
    end: tuple[float, float],
) -> list[tuple[float, float]]:
    pq = [(0.0, start)]
    dist = {start: 0.0}
    prev = {start: None}
    visited = set()

    while pq:
        cur_dist, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)

        if u == end:
            break

        for v, w in graph.get(u, []):
            nd = cur_dist + w
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))

    if end not in prev:
        return []

    path = []
    cur = end
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return path


def build_road_following_route(
    from_lng: float,
    from_lat: float,
    to_lng: float,
    to_lat: float,
) -> tuple[list[list[float]], float]:
    """
    返回:
    - 路线坐标 [[lng, lat], ...]
    - 路线总长度（米）
    """
    graph, nodes = load_road_graph()

    start_node = find_nearest_graph_node(from_lng, from_lat, nodes)
    end_node = find_nearest_graph_node(to_lng, to_lat, nodes)

    path = dijkstra_path(graph, start_node, end_node)

    if not path:
        coords = [[from_lng, from_lat], [to_lng, to_lat]]
        dist = haversine_distance(from_lng, from_lat, to_lng, to_lat)
        return coords, round(dist, 2)

    coords = [[from_lng, from_lat]]
    coords.extend([[lng, lat] for lng, lat in path])
    coords.append([to_lng, to_lat])

    total_dist = 0.0
    for i in range(len(coords) - 1):
        total_dist += haversine_distance(
            coords[i][0], coords[i][1],
            coords[i + 1][0], coords[i + 1][1],
        )

    return coords, round(total_dist, 2)