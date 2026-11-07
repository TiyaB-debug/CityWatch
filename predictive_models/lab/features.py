"""Shared spatial grid and August Citi Bike feature preparation."""
import zipfile

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


def bike_activity(path):
    totals = []
    columns = ["started_at", "ended_at", "start_lat", "start_lng", "end_lat", "end_lng"]
    with zipfile.ZipFile(path) as archive:
        files = [name for name in archive.namelist()
                 if name.lower().endswith(".csv") and not name.startswith("__MACOSX/")]
        if not files:
            raise ValueError("Citi Bike archive contains no CSV files")
        for name in files:
            with archive.open(name) as source:
                for chunk in pd.read_csv(source, usecols=columns, chunksize=200_000):
                    for endpoint, timestamp in [("start", "started_at"), ("end", "ended_at")]:
                        dates = chunk[timestamp].str[:10]
                        subset = chunk.loc[dates.between("2025-08-01", "2025-08-31")]
                        points = grid(subset, endpoint + "_lat", endpoint + "_lng")
                        totals.append(points.groupby(["y", "x"]).size())
    return pd.concat(totals).groupby(level=["y", "x"]).sum().rename("bike_endpoints")
