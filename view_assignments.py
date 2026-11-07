import csv
import json
import webbrowser
from pathlib import Path

with open("assignments.csv", newline="") as file:
    assignments = list(csv.DictReader(file))

html = """
<!DOCTYPE html>
<html>
<head>
  <title>CityWatch Inspection Assignments</title>
  <link rel="stylesheet"
        href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <style>
    body { margin: 0; font-family: Arial, sans-serif; }
    header { padding: 16px; }
    h2 { margin: 0 0 8px; }
    #map { height: 80vh; }
  </style>
</head>
<body>
  <header>
    <h2>CityWatch Inspection Assignments</h2>
    <div>
      Team 1 — blue · Team 2 — orange · Team 3 — purple.
      Click a marker for details.
    </div>
    <p>Lines connect visits directly. They are straight-line estimates.</p>
  </header>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const assignments = __ASSIGNMENTS__;
    const map = L.map("map").setView([40.75, -73.98], 12);

    L.tileLayer(
      "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      { attribution: "© OpenStreetMap contributors" }
    ).addTo(map);

    const colors = ["#2563eb", "#ea580c", "#9333ea", "#15803d"];
    const teams = {};
    const bounds = [];

    for (const row of assignments) {
      const point = [Number(row.latitude), Number(row.longitude)];
      const color = colors[(Number(row.team_id) - 1) % colors.length];
      bounds.push(point);
      (teams[row.team_id] ??= []).push(row);

      const details = document.createElement("div");
      details.textContent =
        `Team ${row.team_id} · Visit ${row.visit_order} · ` +
        `Area ${row.cell_id} · Score ${Number(row.priority_score).toFixed(4)}`;

      L.circleMarker(point, {
        radius: 9, color, fillOpacity: 0.85
      }).addTo(map)
        .bindTooltip(`Team ${row.team_id} · Visit ${row.visit_order}`)
        .bindPopup(details);
    }

    for (const [team, rows] of Object.entries(teams)) {
      rows.sort((a, b) => Number(a.visit_order) - Number(b.visit_order));
      L.polyline(
        rows.map(row => [Number(row.latitude), Number(row.longitude)]),
        { color: colors[(Number(team) - 1) % colors.length] }
      ).addTo(map);
    }

    if (bounds.length) map.fitBounds(bounds, { padding: [30, 30] });
  </script>
</body>
</html>
"""

payload = json.dumps(assignments).replace("<", "\\u003c")
output = Path("inspection_map.html")
output.write_text(
    html.replace("__ASSIGNMENTS__", payload),
    encoding="utf-8",
)

webbrowser.open(output.resolve().as_uri())
print(f"Opened {output.resolve()}")