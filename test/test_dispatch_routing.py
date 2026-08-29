from app.algorithm.dispatch_routing import run_dispatch_routing

result = run_dispatch_routing(
    period="morning",
    algorithm_type="ACO",
    include_process=True,
)

print("status:", result["status"])
print("period:", result["period"])
print("algorithm_type:", result["algorithm_type"])
print("stations:", len(result["stations"]))
print("transfer_plan:", len(result["transfer_plan"]))
print("efficiency_metrics:", result["efficiency_metrics"])

print("\n前3个站点状态:")
for item in result["stations"][:3]:
    print(item)

print("\n前3个调度任务:")
for item in result["transfer_plan"][:3]:
    print(item)

print("\n前2条路线:")
for feature in result["dispatch_routes"]["features"][:2]:
    print(feature)