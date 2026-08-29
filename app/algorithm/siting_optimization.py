from __future__ import annotations

import random
from typing import Any

from app.algorithm.candidate_site_generator import build_candidate_sites
from app.algorithm.demand_prediction import build_demand_points


SERVICE_RADIUS = 200.0
TARGET_SITES_COUNT = 10

GA_POPULATION_SIZE = 60
GA_GENERATIONS = 120
GA_MUTATION_RATE = 0.12
GA_ELITE_SIZE = 6

COVERAGE_WEIGHT = 0.7
DISTANCE_WEIGHT = 0.3
MIN_SITE_SPACING = 80.0


def haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    import math

    r = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def build_circle_polygon(lon: float, lat: float, radius_m: float, num_points: int = 36) -> list[list[float]]:
    import math

    lat_rad = math.radians(lat)
    dlat = radius_m / 111320.0
    dlng = radius_m / (111320.0 * max(math.cos(lat_rad), 1e-6))

    coords = []
    for i in range(num_points):
        angle = 2 * math.pi * i / num_points
        y = lat + dlat * math.sin(angle)
        x = lon + dlng * math.cos(angle)
        coords.append([x, y])

    coords.append(coords[0])
    return coords


def build_distance_matrix(demand_points: list[dict], candidate_sites: list[dict]) -> dict:
    matrix = {}
    for dp in demand_points:
        row = {}
        for site in candidate_sites:
            dist = haversine_distance(dp["x"], dp["y"], site["x"], site["y"])
            row[site["site_id"]] = dist
        matrix[dp["demand_id"]] = row
    return matrix


def compute_site_service_stats(
    selected_sites: list[dict],
    demand_points: list[dict],
    distance_matrix: dict,
    service_radius: float,
    period: str,
) -> dict[str, dict]:
    """
    统计每个站点服务人数（当前时段）和建议容量。
    served_people: 被该站点最近覆盖到的需求总量
    capacity: 先按 served_people 的 30% 估一个建议容量，至少 10
    """
    selected_site_ids = [s["site_id"] for s in selected_sites]
    site_stats = {
        s["site_id"]: {
            "served_people": 0,
            "capacity": 0,
        }
        for s in selected_sites
    }

    for dp in demand_points:
        nearest_site_id = min(
            selected_site_ids,
            key=lambda sid: distance_matrix[dp["demand_id"]][sid]
        )
        nearest_distance = distance_matrix[dp["demand_id"]][nearest_site_id]

        if nearest_distance <= service_radius:
            site_stats[nearest_site_id]["served_people"] += dp["demand"][period]

    for sid, stats in site_stats.items():
        served = stats["served_people"]
        stats["served_people"] = int(round(served))
        stats["capacity"] = max(10, int(round(served * 0.3)))

    return site_stats


def sites_to_feature_collection(sites: list[dict], site_stats: dict[str, dict] | None = None) -> dict:
    site_stats = site_stats or {}

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [site["x"], site["y"]]},
                "properties": {
                    "site_id": site["site_id"],
                    "name": site["name"],
                    "type": site["type"],
                    "capacity": site_stats.get(site["site_id"], {}).get("capacity", site.get("capacity", 0)),
                    "served_people": site_stats.get(site["site_id"], {}).get("served_people", 0),
                },
            }
            for site in sites
        ],
    }


def build_coverage_areas(
    best_sites: list[dict],
    service_radius: float,
    site_stats: dict[str, dict] | None = None,
) -> dict:
    site_stats = site_stats or {}

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        build_circle_polygon(site["x"], site["y"], service_radius)
                    ],
                },
                "properties": {
                    "site_id": site["site_id"],
                    "service_radius": service_radius,
                    "capacity": site_stats.get(site["site_id"], {}).get("capacity", site.get("capacity", 0)),
                    "served_people": site_stats.get(site["site_id"], {}).get("served_people", 0),
                },
            }
            for site in best_sites
        ],
    }


def evaluate_solution(
    selected_sites: list[dict],
    demand_points: list[dict],
    distance_matrix: dict,
    service_radius: float,
    period: str,
) -> tuple[float, dict]:
    total_demand = sum(dp["demand"][period] for dp in demand_points)
    total_demand = max(total_demand, 1.0)

    covered_demand = 0.0
    weighted_distance_sum = 0.0

    selected_site_ids = [s["site_id"] for s in selected_sites]

    for dp in demand_points:
        dp_weight = dp["demand"][period]
        nearest_distance = min(distance_matrix[dp["demand_id"]][site_id] for site_id in selected_site_ids)

        weighted_distance_sum += nearest_distance * dp_weight
        if nearest_distance <= service_radius:
            covered_demand += dp_weight

    coverage_rate = covered_demand / total_demand
    avg_walk_distance = weighted_distance_sum / total_demand

    distance_score = 1.0 / (1.0 + avg_walk_distance / 100.0)

    spacing_penalty = 0.0
    for i in range(len(selected_sites)):
        for j in range(i + 1, len(selected_sites)):
            d = haversine_distance(
                selected_sites[i]["x"], selected_sites[i]["y"],
                selected_sites[j]["x"], selected_sites[j]["y"],
            )
            if d < MIN_SITE_SPACING:
                spacing_penalty += (MIN_SITE_SPACING - d) / MIN_SITE_SPACING * 0.1

    fitness = COVERAGE_WEIGHT * coverage_rate + DISTANCE_WEIGHT * distance_score - spacing_penalty

    metrics = {
        "coverage_rate": round(coverage_rate, 4),
        "avg_walk_distance": round(avg_walk_distance, 2),
        "fitness": round(fitness, 4),
    }
    return fitness, metrics


def initialize_population(candidate_sites: list[dict], target_sites_count: int, population_size: int) -> list[list[dict]]:
    if len(candidate_sites) < target_sites_count:
        raise ValueError("候选点数量不足")

    population = []
    for _ in range(population_size):
        population.append(random.sample(candidate_sites, target_sites_count))
    return population


def tournament_selection(scored_population: list[tuple[list[dict], float, dict]], k: int = 3) -> list[dict]:
    group = random.sample(scored_population, min(k, len(scored_population)))
    group.sort(key=lambda x: x[1], reverse=True)
    return group[0][0]


def crossover(parent1: list[dict], parent2: list[dict], target_sites_count: int, candidate_sites: list[dict]) -> list[dict]:
    merged = {site["site_id"]: site for site in parent1}
    merged.update({site["site_id"]: site for site in parent2})

    merged_sites = list(merged.values())
    random.shuffle(merged_sites)

    child = merged_sites[:target_sites_count]

    if len(child) < target_sites_count:
        existing_ids = {s["site_id"] for s in child}
        remain = [s for s in candidate_sites if s["site_id"] not in existing_ids]
        child.extend(random.sample(remain, target_sites_count - len(child)))

    return child


def mutate(solution: list[dict], candidate_sites: list[dict], mutation_rate: float) -> list[dict]:
    solution = solution[:]
    if random.random() < mutation_rate:
        idx = random.randrange(len(solution))
        existing_ids = {s["site_id"] for s in solution}
        available = [s for s in candidate_sites if s["site_id"] not in existing_ids]
        if available:
            solution[idx] = random.choice(available)
    return solution


def run_genetic_algorithm(
    demand_points: list[dict],
    candidate_sites: list[dict],
    target_sites_count: int,
    service_radius: float,
    period: str,
) -> dict[str, Any]:
    distance_matrix = build_distance_matrix(demand_points, candidate_sites)
    population = initialize_population(candidate_sites, target_sites_count, GA_POPULATION_SIZE)

    iterations = []
    best_solution = None
    best_fitness = float("-inf")
    best_metrics = None

    for generation in range(GA_GENERATIONS):
        scored_population = []
        for solution in population:
            fitness, metrics = evaluate_solution(solution, demand_points, distance_matrix, service_radius, period)
            scored_population.append((solution, fitness, metrics))

        scored_population.sort(key=lambda x: x[1], reverse=True)

        if scored_population[0][1] > best_fitness:
            best_solution = scored_population[0][0]
            best_fitness = scored_population[0][1]
            best_metrics = scored_population[0][2]

        iterations.append({
            "generation": generation + 1,
            "best_fitness": round(scored_population[0][1], 4),
            "coverage_rate": scored_population[0][2]["coverage_rate"],
            "avg_walk_distance": scored_population[0][2]["avg_walk_distance"],
        })

        next_population = [item[0] for item in scored_population[:GA_ELITE_SIZE]]

        while len(next_population) < GA_POPULATION_SIZE:
            parent1 = tournament_selection(scored_population)
            parent2 = tournament_selection(scored_population)
            child = crossover(parent1, parent2, target_sites_count, candidate_sites)
            child = mutate(child, candidate_sites, GA_MUTATION_RATE)
            next_population.append(child)

        population = next_population

    return {
        "best_sites": best_solution,
        "metrics": best_metrics,
        "iterations": iterations,
    }


def build_siting_process_states(result: dict) -> list[dict]:
    states = []
    for item in result.get("iterations", []):
        states.append({
            "iteration": item["generation"],
            "stage_name": f'generation_{item["generation"]}',
            "metrics": {
                "best_fitness": item["best_fitness"],
                "coverage_rate": item["coverage_rate"],
                "avg_walk_distance": item["avg_walk_distance"],
            },
            "artifacts": {},
        })
    return states


def run_siting_optimization(
    algorithm_type: str = "GA",
    period: str = "morning",
    target_sites_count: int = TARGET_SITES_COUNT,
    service_radius: float = SERVICE_RADIUS,
    include_process: bool = False,
) -> dict:
    if period not in {"morning", "noon", "evening"}:
        raise ValueError("period 必须为 morning / noon / evening")

    if algorithm_type.upper() != "GA":
        raise ValueError("当前版本先只支持 GA")

    demand_points = build_demand_points()
    candidate_sites = build_candidate_sites()

    result = run_genetic_algorithm(
        demand_points=demand_points,
        candidate_sites=candidate_sites,
        target_sites_count=target_sites_count,
        service_radius=service_radius,
        period=period,
    )

    best_sites = result["best_sites"]
    distance_matrix = build_distance_matrix(demand_points, best_sites)
    site_stats = compute_site_service_stats(
        selected_sites=best_sites,
        demand_points=demand_points,
        distance_matrix=distance_matrix,
        service_radius=service_radius,
        period=period,
    )

    response = {
        "status": "success",
        "algorithm_type": "GA",
        "period": period,
        "optimal_sites": sites_to_feature_collection(best_sites, site_stats=site_stats),
        "coverage_areas": build_coverage_areas(best_sites, service_radius, site_stats=site_stats),
        "global_metrics": result["metrics"],
        "process_available": include_process,
        "process_summary": {
            "total_generations": len(result.get("iterations", []))
        } if include_process else None,
    }

    if include_process:
        response["process_states"] = build_siting_process_states(result)

    return response