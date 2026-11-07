"""Shared spatial grid and NOAA station coordinates."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.path import Path as PolygonPath

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


def manhattan_boundary():
    path = Path(__file__).with_name("inputs") / "manhattan.geojson"
    return json.loads(path.read_text())


def in_manhattan(frame):
    """Test reported coordinates against NYC's Manhattan borough boundary."""
    geometry = manhattan_boundary()
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


def manhattan_crashes(crashes):
    """Return all reported Manhattan crashes and the subset with usable points."""
    inside = in_manhattan(crashes)
    geocoded = crashes.latitude.between(40.48, 40.93) & crashes.longitude.between(-74.27, -73.68)
    mapped = grid(crashes.loc[inside], "latitude", "longitude")
    reported = crashes.loc[inside | (~geocoded & crashes.borough.eq("MANHATTAN"))]
    return reported, mapped


def load_overlap(crash_path, weather_dir):
    cols = ["collision_id", "crash_date", "latitude", "longitude", "borough", "number_of_cyclist_injured"]
    crashes = pd.read_csv(crash_path, usecols=cols).drop_duplicates("collision_id")
    crashes["date"] = pd.to_datetime(crashes.crash_date, format="mixed").dt.normalize()
    crashes["injury"] = crashes.number_of_cyclist_injured.gt(0).astype("int8")
    stations = []
    for station in STATIONS:
        cols = ["DATE", "PRCP", "TMAX", "TMIN", "PRCP_ATTRIBUTES", "TMAX_ATTRIBUTES", "TMIN_ATTRIBUTES"]
        rows = pd.read_csv(weather_dir / f"{station}.csv", usecols=cols)
        for col in ("PRCP", "TMAX", "TMIN"):
            flagged = rows[col + "_ATTRIBUTES"].fillna("").str.split(",").str[1].fillna("").ne("")
            rows.loc[flagged, col] = np.nan
        # GHCN daily archive files use tenths of mm and tenths of degrees C.
        stations.append(pd.DataFrame({"date": pd.to_datetime(rows.DATE), "station": station,
                                      "rain_mm": rows.PRCP / 10,
                                      "temperature_c": (rows.TMAX + rows.TMIN) / 20}))
    weather = pd.concat(stations, ignore_index=True)
    weather = weather.dropna().loc[lambda rows: rows.rain_mm.ge(0)]
    complete = weather.groupby("date").station.nunique()
    complete = complete.loc[complete.eq(len(STATIONS))].index
    start = max(crashes.date.min(), complete.min())
    stop = min(crashes.date.max(), complete.max())
    dates = pd.date_range(start, stop)
    if not dates.isin(complete).all():
        raise ValueError("Weather has missing station-days inside the overlap")
    crashes = crashes.loc[crashes.date.between(start, stop)]
    return crashes, weather.loc[weather.date.between(start, stop)], dates


def locations(mapped):
    cells = mapped.groupby(["y", "x"]).date.min().rename("first_seen").reset_index()
    cells["cell_id"] = cells.y.astype(str) + "-" + cells.x.astype(str)
    cells["latitude"] = LAT_ORIGIN + (cells.y + .5) * LAT_STEP
    cells["longitude"] = LON_ORIGIN + (cells.x + .5) * LON_STEP
    cells["station"] = [
        min(STATIONS, key=lambda name: (lat - STATIONS[name][0]) ** 2
            + (.76 * (lon - STATIONS[name][1])) ** 2)
        for lat, lon in zip(cells.latitude, cells.longitude)
    ]
    return cells
