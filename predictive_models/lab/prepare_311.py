"""Aggregate geocoded street-related DOT requests to the CityWatch grid."""
import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlencode

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab.features import grid

API = "https://data.cityofnewyork.us/resource/erm2-nwe9.csv"
FILTER = ("agency = 'DOT' and complaint_type in "
          "('Street Condition','Street Light Condition','Bike Lane','Sidewalk Condition') "
          "and latitude is not null and longitude is not null")
MONTHS = [day.date().isoformat() for day in pd.date_range("2023-01-01", "2026-11-01", freq="MS")]
PAGE_SIZE = 50_000


def fetch(start, stop, output, **params):
    filters = f"created_date >= '{start}T00:00:00' and created_date < '{stop}T00:00:00' and {FILTER}"
    query = {"$where": filters, **{"$" + key: value for key, value in params.items()}}
    subprocess.run(["curl", "-LfSs", "--compressed", "--retry", "3", "--max-time", "150",
                    API + "?" + urlencode(query), "-o", str(output)], check=True)
    return output


def read_months(directory):
    paths = [directory / f"{month}.csv" for month in MONTHS]
    frames = [pd.read_csv(path) for path in paths]
    if any(len(frame) >= PAGE_SIZE for frame in frames):
        raise ValueError("A monthly export reached the API limit and needs pagination")
    records = pd.concat(frames, ignore_index=True)
    if records.unique_key.isna().any() or records.unique_key.duplicated().any():
        raise ValueError("Missing or duplicate 311 request IDs")
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--monthly-csvs", type=Path, help="Reuse previously downloaded monthly projections")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with TemporaryDirectory() as temp:
        directory = args.monthly_csvs or Path(temp)
        if args.monthly_csvs is None:
            with ThreadPoolExecutor(max_workers=6) as pool:
                jobs = [pool.submit(fetch, start, stop, directory / f"{start}.csv",
                                    select="unique_key,created_date,latitude,longitude",
                                    limit=PAGE_SIZE, order="created_date,unique_key")
                        for start, stop in zip(MONTHS, MONTHS[1:] + ["2026-11-02"])]
                for job in jobs:
                    job.result()
        records = read_months(directory)
    dates = pd.to_datetime(records.created_date, format="mixed").dt.normalize()
    records["week"] = dates - pd.to_timedelta(dates.dt.dayofweek, unit="D")
    mapped = grid(records, "latitude", "longitude")
    counts = mapped.groupby(["y", "x", "week"]).size().rename("requests").reset_index()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    counts.to_csv(args.out, index=False, compression={"method": "gzip", "mtime": 0})
    metadata = {"projected_requests": len(records), "requests_in_study_bounds": len(mapped)}
    args.out.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(metadata)


if __name__ == "__main__":
    main()
