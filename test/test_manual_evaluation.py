from app.algorithm.manual_evaluation import evaluate_manual_sites

manual_sites = [
    {
        "site_id": "m1",
        "name": "测试站点1",
        "latitude": 30.5415,
        "longitude": 114.3539,
        "capacity": 20,
    },
    {
        "site_id": "m2",
        "name": "测试站点2",
        "latitude": 30.5447,
        "longitude": 114.3644,
        "capacity": 30,
    },
    {
        "site_id": "m3",
        "name": "测试站点3",
        "latitude": 30.5307,
        "longitude": 114.3536,
        "capacity": 25,
    },
]

result = evaluate_manual_sites(
    current_sites=manual_sites,
    period="morning",
    service_radius=120.0,
)

print(result["status"])
print(result["evaluated_sites_count"])
print(result["global_metrics"])
print(result["coverage_areas"]["features"][:2])