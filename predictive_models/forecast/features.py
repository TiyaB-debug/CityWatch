"""Shared spatial grid and NOAA station coordinates."""
import pandas as pd

LAT_ORIGIN, LON_ORIGIN = 40.48, -74.27


LAT_STEP, LON_STEP = 0.0045, 0.0059


STATIONS = {
    "USW00094728": (40.779, -73.969),
    "USW00014732": (40.779, -73.880),
    "USW00094789": (40.639, -73.762),
}


def grid(frame, latitude, longitude):
    lat = pd.to_numeric(frame[latitude], errors="coerce")
    lon = pd.to_numeric(frame[longitude], errors="coerce")
    valid = lat.between(40.48, 40.93) & lon.between(-74.27, -73.68)
    result = frame.loc[valid].copy()
    result["y"] = ((lat[valid] - LAT_ORIGIN) / LAT_STEP).astype(int)
    result["x"] = ((lon[valid] - LON_ORIGIN) / LON_STEP).astype(int)
    return result


def in_manhattan(frame):
    """Test reported coordinates against NYC's Manhattan borough boundary."""
    import json
    from pathlib import Path
    import numpy as np
    from matplotlib.path import Path as PolygonPath

    path = Path(__file__).with_name("inputs") / "manhattan.geojson"
    geometry = json.loads(path.read_text())
    points = frame[["longitude", "latitude"]].to_numpy()
    matches = np.zeros(len(points), dtype=bool)
    for shell, *holes in geometry["coordinates"]:
        vertices = np.asarray(shell)
        indices = np.flatnonzero(((points >= vertices.min(axis=0))
                                  & (points <= vertices.max(axis=0))).all(axis=1))
        inside = PolygonPath(vertices).contains_points(points[indices])
        for hole in holes:
            inside &= ~PolygonPath(hole).contains_points(points[indices])
        matches[indices] |= inside
    return matches
