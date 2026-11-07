# CityWatch predictive models

CityWatch ranks roughly 500 m NYC grid cells for weekly street inspections. The models forecast reported cyclist injury collisions or the probability that a cell will have at least one. The backtest compares how many collisions each ranking captures at the same weekly inspection budget.

## Models

- [Poisson regression](lab/models/poisson.py) predicts the **expected number of injury collisions** per cell-week.
- [Logistic regression](lab/models/logistic.py) estimates the **probability of at least one injury collision** using a linear combination of the input features.
- [Random forest](lab/models/random_forest.py) estimates that probability by averaging decision trees trained on bootstrap samples.
- [Extra trees](lab/models/extra_trees.py) estimates that probability using an ensemble with randomized split thresholds.
- [Gradient boosting](lab/models/gradient_boosting.py) estimates that probability with trees trained in sequence. The full version uses crash history, weather, 311 complaints, and Citi Bike activity. Four variants remove weather, 311, or Citi Bike one at a time, or use crash history and calendar features only. These comparisons show how much each input adds to this model.
- [Historical baselines](lab/models/baselines.py) rank cells by their 13-week or 52-week injury collision counts. They provide a benchmark at each inspection budget.

## Individual model visuals

Each standalone figure shows the top 10 inspection cells for three holdout weeks and a cumulative capture chart for budgets of 5, 10, and 20 cells per week. Filled cells had at least one reported cyclist injury collision that week. [NYC borough outlines](https://data.cityofnewyork.us/City-Government/Borough-Boundaries/gthc-hcne)

- [Poisson regression](lab/results/figures/poisson.png)
- [Logistic regression](lab/results/figures/logistic.png)
- [Random forest](lab/results/figures/random_forest.png)
- [Extra trees](lab/results/figures/extra_trees.png)
- [Gradient boosting](lab/results/figures/gradient_boost.png)
- [Boosting without weather](lab/results/figures/boost_without_weather.png)
- [Boosting without 311](lab/results/figures/boost_without_311.png)
- [Boosting without Citi Bike](lab/results/figures/boost_without_citi_bike.png)
- [Boosting with crash history and calendar features](lab/results/figures/boost_crash_history_only.png)
- [13-week baseline](lab/results/figures/13_week_baseline.png)
- [52-week baseline](lab/results/figures/52_week_baseline.png)

## Supporting files

- [Training runner](lab/train.py) builds the features, fits models, selects a method on validation data, and evaluates it on the holdout. Add `--model Logistic` to run that model with both baselines.
- [Feature preparation](lab/features.py) defines the spatial grid and aggregates August Citi Bike station endpoints. [311 preparation](lab/prepare_311.py) builds weekly street-complaint counts from NYC Open Data.
- [Inputs](lab/inputs/) contains the NOAA and 311 snapshots used by the backtest and the borough outlines used by the figures. The [run instructions](#reproduce) identify the crash file, weather archive snapshot, and Citi Bike download.
- [Results](lab/results/) contains the backtest metrics, standalone figures, and the September 2025 daily CSV. [figures.py](lab/figures.py) renders the figures when the training runner finishes.
- [Requirements](requirements.txt) lists the Python dependencies.

## Daily CSV export

[September 2025 daily predictions](lab/results/daily_with_weather_sep_2025.csv) contains one row per candidate cell and day, with `cell_id`, `latitude`, `longitude`, `date`, and `with_weather`. The 29,460 rows cover all 982 candidate cells for September 1–30, 2025. These are expected daily collision counts from the original weather-aware Poisson model in [citywatch.py](https://github.com/TiyaB-debug/CityWatch/blob/856d3311671d67c7a64ece9c9c6449e8e835687f/predictive_models/citywatch.py), trained on August 2025 and scored using a replay of observed September weather. The newer lab predicts weekly outcomes.

## Weekly backtest results

The spring validation set selected **gradient boosting without 311** by capture at 10 cells. In the July 6–November 1, 2026 holdout, that model captured **50 of 2,010 collisions (2.49%)**. The 13-week count baseline captured **45 (2.24%)** and the 52-week baseline captured **58 (2.89%)**. The paired three-week block bootstrap interval for the selected model's gain over the 13-week baseline was **−0.61 to +1.16 percentage points**. At this budget the selected model did not beat the stronger historical baseline.

- **Logistic regression** led the observed holdout at 10 cells with **68 (3.38%)**. Full gradient boosting led at 5 cells with **38**, and boosting without bike activity led at 20 cells with **123**. These are exploratory comparisons across the holdout.
- At 10 cells, full boosting captured **60** versus **50** without weather, **50** without 311, **56** without bike activity, and **61** using crash history and calendar features alone. These are controlled feature removals within one model family. The extra inputs did not give a consistent advantage across budgets or over the crash-history-only variant.
- Full results, weekly capture counts and average precision for all methods are in [backtest.json](lab/results/backtest.json). Average precision measures ranking quality across eligible cell-weeks. The capture denominator includes all reported cyclist injury collisions, including 101 outside the candidate cells or without usable coordinates in the holdout.

## Data and model design

- **NYC crash records.** The repo crash snapshot contributes 343,563 records in complete modeling weeks. The outcome counts a collision once if at least one cyclist was reported injured. Cells are established from January–June 2023 crash locations and fixed for evaluation. Features include local and neighboring crash history and seasonality. [NYC Open Data](https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95/about_data)
- **NOAA.** All four repository station files contribute pre-2023 precipitation averages by station and calendar month. Their record periods differ, so those averages are historical proxies. Overlapping daily records from Central Park, LaGuardia and JFK provide prior-week precipitation and temperature. Missing values are imputed using training medians. [NOAA daily summaries](https://www.ncei.noaa.gov/access/search/datasets/daily-summaries/)
- **311.** The committed aggregate covers 442,010 geocoded DOT requests in the Street Condition, Street Light Condition, Bike Lane and Sidewalk Condition categories. The model uses lagged cell counts. These requests reflect reporting behavior as well as street conditions. [NYC 311 source](https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9/about_data)
- **Citi Bike.** The August 2025 snapshot contributes 10,227,819 station start/end records. The feature first becomes available in September 2025 and serves as a fixed historical activity proxy. Station endpoints do not establish riding routes or represent every cyclist. The reference project informed the logistic and random forest comparisons. [Citi Bike data](https://citibikenyc.com/system-data) · [Reference repository](https://github.com/danieljinchoy/citibike)

Training uses July 2023–early April 2026. Validation begins April 6, 2026. The fixed holdout begins July 6 and ends November 1, the end of the latest complete week. Counts exclude the immediately preceding week to allow a reporting buffer. Weather comes from the preceding complete week. This retrospective evaluation uses revised source snapshots, so it cannot verify what records were actually available to planners on each prediction date. Models use the historical weather signal rather than a live forecast. Inspection findings would determine appropriate repairs.

## Reproduce

From the repository root, extract the weather archive from the commit used for the published backtest. The live `Datasets/Weather` folder has since been updated. If the commit is missing from a shallow clone, run `git fetch --unshallow` first.

```sh
python3 -m pip install -r predictive_models/requirements.txt
curl -fL https://s3.amazonaws.com/tripdata/202508-citibike-tripdata.zip -o /tmp/202508-citibike-tripdata.zip
weather_snapshot=$(mktemp -d)
git archive 03eb7e32afa501f43d4d010e71579ee0d9de9898 Datasets/Weather | tar -x -C "$weather_snapshot"
python3 predictive_models/lab/train.py \
  --crashes Datasets/nyc_crashes_2023-01-01_to_2026-11-07.csv.gz \
  --weather predictive_models/lab/inputs/noaa_daily.csv \
  --archive "$weather_snapshot/Datasets/Weather" \
  --complaints predictive_models/lab/inputs/311_weekly.csv.gz \
  --bike-zip /tmp/202508-citibike-tripdata.zip \
  --out predictive_models/lab/results
```

The 311 aggregate can be recreated with `python3 predictive_models/lab/prepare_311.py --out predictive_models/lab/inputs/311_weekly.csv.gz`. Its snapshot may change when the upstream dataset is revised. Raw Citi Bike trips and individual 311 requests are excluded from the repository.

To run just one fitted model and both baselines, add `--model Logistic` to the training command and use a separate output folder such as `--out /tmp/citywatch-logistic`. Repeat `--model` to compare specific models. Run `python3 predictive_models/lab/train.py --help` for the list of names.
