#!/usr/bin/env bash
set -euo pipefail

data_dir="${1:-data}"
mkdir -p "$data_dir"
event='https://raw.githubusercontent.com/rutgersdsc/nyc-in-motion/main/data/public'
curl -fLSs --retry 2 "$event/noaa_daily_weather_aug_sep_2025.csv" -o "$data_dir/weather.csv"
curl -fLSsG --retry 2 'https://data.cityofnewyork.us/resource/h9gi-nx95.csv' \
  --data-urlencode '$where=crash_date >= "2025-08-01T00:00:00" and crash_date < "2025-10-01T00:00:00" and number_of_cyclist_injured > 0' \
  --data-urlencode '$limit=50000' -o "$data_dir/crashes.csv"
curl -fLSs --retry 2 'https://s3.amazonaws.com/tripdata/202508-citibike-tripdata.zip' -o "$data_dir/august-bike.zip"
