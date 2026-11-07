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
