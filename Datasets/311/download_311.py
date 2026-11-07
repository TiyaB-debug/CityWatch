"""Download NYC 311 service requests as weekly, compressed CSV files."""
import argparse
import csv
import gzip
import io
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

API = "https://data.cityofnewyork.us/resource/erm2-nwe9.csv"
PAGE_SIZE = 25_000
ONE_DAY = timedelta(days=1)


def query(filters, **parameters):
    params = {"$where": filters}
    params.update({"$" + key: value for key, value in parameters.items()})
    response = urlopen(f"{API}?{urlencode(params)}", timeout=120)
    return io.TextIOWrapper(response, encoding="utf-8-sig", newline="")


def download_week(start, stop, directory):
    filters = f"created_date >= '{start}T00:00:00' and created_date < '{stop}T00:00:00'"
    with query(filters, select="count(*)") as response:
        expected = int(next(csv.DictReader(response))["count"])

    filename = directory / f"nyc_311_{start}_to_{stop - ONE_DAY}.csv.gz"
    partial = filename.with_suffix(".gz.part")
    seen = set()
    header = None
    try:
        with gzip.open(partial, "wt", encoding="utf-8", newline="") as output:
            writer = csv.writer(output)
            for offset in range(0, max(expected, 1), PAGE_SIZE):
                with query(filters, limit=PAGE_SIZE, offset=offset,
                           order="created_date,unique_key") as response:
                    reader = csv.reader(response)
                    fields = next(reader)
                    if header is None:
                        header = fields
                        writer.writerow(header)
                    if fields != header:
                        raise RuntimeError("The API schema changed during export")
                    key_index = header.index("unique_key")
                    date_index = header.index("created_date")
                    for row in reader:
                        if len(row) != len(header):
                            raise RuntimeError("The API returned a malformed CSV row")
                        key = row[key_index]
                        created = date.fromisoformat(row[date_index][:10])
                        if not key or key in seen or not start <= created < stop:
                            raise RuntimeError("The API returned a duplicate or out-of-range request")
                        seen.add(key)
                        writer.writerow(row)
        if len(seen) != expected:
            raise RuntimeError(f"API count changed: expected {expected}, got {len(seen)}")
        partial.replace(filename)
    finally:
        partial.unlink(missing_ok=True)
    print(f"{filename.name}: {expected:,} requests", flush=True)
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2023, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2026, 11, 7),
                        help="Inclusive end date (default: 2026-11-07)")
    parser.add_argument("--out", type=Path, default=Path("exports"))
    args = parser.parse_args()
    if args.end < args.start:
        parser.error("--end must be on or after --start")
    args.out.mkdir(parents=True, exist_ok=True)
    start = args.start
    total = 0
    while start <= args.end:
        stop = min(start + timedelta(days=7), args.end + ONE_DAY)
        total += download_week(start, stop, args.out)
        start = stop
    print(f"Downloaded {total:,} service requests.")


if __name__ == "__main__":
    main()
