import csv

from optimization.allocator import optimize_inspections

with open(
    "predictive_models/lab/results/daily_with_weather_sep_2025.csv",
    newline="",
) as file:
    predictions = list(csv.DictReader(file))

result = optimize_inspections(
    predictions,
    team_count=3,
    inspections_per_team=4,
    date="2025-09-10",
)

assignments = result["assignments"]
summary = result["summary"]

for assignment in assignments:
    print(assignment)

print(summary)