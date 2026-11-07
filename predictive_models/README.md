# CityWatch predictive models

CityWatch ranks roughly 500 m NYC grid cells for weekly street inspections. The models forecast reported cyclist injury collisions or the probability that a cell will have at least one. The backtest compares how many collisions each ranking captures at the same weekly inspection budget.

## Models and individual figures

Each figure shows which top-10 cells the method adds, drops, or shares with the 52-week baseline in three holdout weeks. The chart shows cumulative capture gained or lost at each inspection budget. The weekly models use crash records, NOAA weather, and 311 complaints where specified.

- **Poisson regression** predicts the expected number of injury collisions from crash history, weather, and 311. [Model](lab/models/poisson.py) · [Figure](lab/results/figures/poisson.png)
- **Logistic regression** estimates the probability of at least one collision from the same inputs. [Model](lab/models/logistic.py) · [Figure](lab/results/figures/logistic.png)
- **Hurdle model** estimates the chance of a collision first, then estimates the number of additional collisions in weeks with an injury collision. The two parts produce an expected count. [Model](lab/models/hurdle.py) · [Figure](lab/results/figures/hurdle.png)
- **Seasonal analog** weights crash counts around the same week in previous years and blends them with recent local history. [Model](lab/models/seasonal.py) · [Figure](lab/results/figures/seasonal_analog.png)
- **Spatial shrinkage** blends each cell's recent injury rate with the rates of its four adjacent cells, using longer local history when no adjacent cell is available. [Model](lab/models/spatial.py) · [Figure](lab/results/figures/spatial_shrinkage.png)
- **Historical baselines** rank cells by lagged crash counts. [Model](lab/models/baselines.py) · [13-week figure](lab/results/figures/13_week_baseline.png) · [52-week figure](lab/results/figures/52_week_baseline.png)

[Borough outlines](https://data.cityofnewyork.us/City-Government/Borough-Boundaries/gthc-hcne)

## Supporting files

- [Training runner](lab/train.py) builds the features, fits models, selects a method on validation data, and evaluates it on the holdout. Add `--model Logistic` to run that model with both baselines.
- [Feature preparation](lab/features.py) defines the spatial grid and NOAA station locations. [311 preparation](lab/prepare_311.py) builds weekly street-complaint counts from NYC Open Data.
- [Inputs](lab/inputs/) contains the NOAA and 311 snapshots used by the backtest and the borough outlines used by the figures. The [run instructions](#reproduce) identify the crash file and weather archive snapshot.
- [Results](lab/results/) contains the backtest metrics, standalone figures, and the September 2025 daily CSV. [figures.py](lab/figures.py) renders the figures when the training runner finishes.
- [Requirements](requirements.txt) lists the Python dependencies.

## Daily CSV export

[September 2025 daily predictions](lab/results/daily_with_weather_sep_2025.csv) contains one row per candidate cell and day, with `cell_id`, `latitude`, `longitude`, `date`, and `with_weather`. The 29,460 rows cover all 982 candidate cells for September 1–30, 2025. These are expected daily collision counts from the original weather-aware Poisson model in [citywatch.py](https://github.com/TiyaB-debug/CityWatch/blob/856d3311671d67c7a64ece9c9c6449e8e835687f/predictive_models/citywatch.py), trained on August 2025 and scored using a replay of observed September weather. This historical export used Citi Bike station endpoints. The current weekly models use zero Citi Bike data.

## Weekly backtest results

Spring validation selected **Poisson regression** at 10 inspections per week. It captured **59 of 2,010** holdout collisions, compared with **58** for the 52-week baseline and **45** for the 13-week baseline. Logistic regression and the hurdle model each captured **68**, an exploratory holdout result.

At 10 cells, the seasonal analog changed **6.82 picks per week** on average relative to the 52-week baseline and captured **39** collisions. Spatial shrinkage changed **4.88** and captured **52**. Poisson changed **4.47** and captured **59**. The shortlist changes and the capture results measure different things.

[Backtest metrics](lab/results/backtest.json) contains all budgets, weekly counts, average precision, and the paired three-week block bootstrap interval for the validation-selected model versus the 52-week baseline. The denominator includes all reported cyclist injury collisions, including 101 outside the candidate cells or without usable coordinates.

## Data and model design

- **NYC crash records.** The repo crash snapshot contributes 343,563 records in complete modeling weeks. The outcome counts a collision once if at least one cyclist was reported injured. Cells are established from January–June 2023 crash locations and fixed for evaluation. Features include local and neighboring crash history and seasonality. [NYC Open Data](https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95/about_data)
- **NOAA.** All four repository station files contribute pre-2023 precipitation averages by station and calendar month. Their record periods differ, so those averages are historical proxies. Overlapping daily records from Central Park, LaGuardia and JFK provide prior-week precipitation and temperature. Missing values are imputed using training medians. [NOAA daily summaries](https://www.ncei.noaa.gov/access/search/datasets/daily-summaries/)
- **311.** The committed aggregate covers 442,010 geocoded DOT requests in the Street Condition, Street Light Condition, Bike Lane and Sidewalk Condition categories. The model uses lagged cell counts. These requests reflect reporting behavior as well as street conditions. [NYC 311 source](https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9/about_data)

Training uses July 2023–early April 2026. Validation begins April 6, 2026. The fixed holdout begins July 6 and ends November 1, the end of the latest complete week. Counts exclude the immediately preceding week to allow a reporting buffer. Weather comes from the preceding complete week. This retrospective evaluation uses revised source snapshots, so it cannot verify what records were actually available to planners on each prediction date. Models use the historical weather signal rather than a live forecast. Inspection findings would determine appropriate repairs.

## Reproduce

From the repository root, extract the weather archive from the commit used for the published backtest. The live `Datasets/Weather` folder has since been updated. If the commit is missing from a shallow clone, run `git fetch --unshallow` first.

```sh
python3 -m pip install -r predictive_models/requirements.txt
weather_snapshot=$(mktemp -d)
git archive 03eb7e32afa501f43d4d010e71579ee0d9de9898 Datasets/Weather | tar -x -C "$weather_snapshot"
python3 predictive_models/lab/train.py \
  --crashes Datasets/nyc_crashes_2023-01-01_to_2026-11-07.csv.gz \
  --weather predictive_models/lab/inputs/noaa_daily.csv \
  --archive "$weather_snapshot/Datasets/Weather" \
  --complaints predictive_models/lab/inputs/311_weekly.csv.gz \
  --out predictive_models/lab/results
```

The 311 aggregate can be recreated with `python3 predictive_models/lab/prepare_311.py --out predictive_models/lab/inputs/311_weekly.csv.gz`. Its snapshot may change when the upstream dataset is revised. Individual 311 requests are excluded from the repository.

To run just one fitted model and both baselines, add `--model Logistic` to the training command and use a separate output folder such as `--out /tmp/citywatch-logistic`. Repeat `--model` to compare specific models. Run `python3 predictive_models/lab/train.py --help` for the list of names.
