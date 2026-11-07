#!/usr/bin/env bash
set -euo pipefail

repo=$(git rev-parse --show-toplevel)
destination=${1:-"$repo/predictive_models/output/datathon"}
mkdir -p "$destination"
destination=$(cd "$destination" && pwd)
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
sources=https://raw.githubusercontent.com/rutgersdsc/nyc-in-motion/main/data/public

for file in nyc_crashes_aug_sep_2025.csv noaa_daily_weather_aug_sep_2025.csv; do
    curl -fLSs --retry 2 "$sources/$file" -o "$scratch/$file"
done
(cd "$scratch" && shasum -a 256 -c "$repo/predictive_models/datathon/SHA256SUMS")

# Reuse the pinned pilot runner so the competition results remain reproducible.
git -C "$repo" archive f41b1db983f22446cee70df3057016b9485816c7 predictive_models | tar -x -C "$scratch"
python3 "$scratch/predictive_models/lab/train.py" \
    --crashes "$scratch/nyc_crashes_aug_sep_2025.csv" \
    --weather "$scratch/noaa_daily_weather_aug_sep_2025.csv" \
    --out "$destination"
