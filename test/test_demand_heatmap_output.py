from app.algorithm.demand_prediction import build_heatmap_output

result = build_heatmap_output("morning")

print("status:", result["status"])
print("period:", result["period"])
print("points:", len(result["points"]))

print("\n前5个热力点:")
for item in result["points"][:5]:
    print(item)