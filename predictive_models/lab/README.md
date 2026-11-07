# CityWatch forecast lab

The lab forecasts **weekly police-reported cyclist injury collisions** in approximately 500 m grid cells. It compares nine fitted variants and two historical ranking baselines. Open [the generated replay](results/citywatch_lab.html) in a browser to play the 17 holdout weeks, switch models, and compare inspection budgets of 5, 10, or 20 cells. The interactive map loads Leaflet and OpenStreetMap over the internet.

## Model files

- [Poisson regression](models/poisson.py) estimates the number of injury collisions per cell-week.
- [Logistic regression](models/logistic.py) estimates the probability of at least one injury collision.
- [Random forest](models/random_forest.py) combines trees trained on bootstrap samples.
- [Extra trees](models/extra_trees.py) combines trees with randomized splits.
- [Gradient boosting](models/gradient_boosting.py) contains the full model and four feature-removal variants.
- [Historical baselines](models/baselines.py) rank cells by their 13-week and 52-week injury collision counts.

The files define the estimators. [train.py](train.py) prepares the inputs and runs the same validation and holdout comparison for each model.

## Results

The spring validation set selected **gradient boosting without 311** by capture at 10 cells. In the July 6–November 1, 2026 holdout, that model captured **50 of 2,010 collisions (2.49%)**. The 13-week count baseline captured **45 (2.24%)** and the 52-week baseline captured **58 (2.89%)**. The paired three-week block bootstrap interval for the selected model's gain over the 13-week baseline was **−0.61 to +1.16 percentage points**. At this budget the selected model did not beat the stronger historical baseline.

- **Logistic regression** led the observed holdout at 10 cells with **68 (3.38%)**. Full gradient boosting led at 5 cells with **38**, and boosting without bike activity led at 20 cells with **123**. These are exploratory comparisons across the holdout.
- At 10 cells, full boosting captured **60** versus **50** without weather, **50** without 311, **56** without bike activity, and **61** using crash history and calendar features alone. These are controlled feature removals within one model family. The extra inputs did not give a consistent advantage across budgets or over the crash-history-only variant.
- Full results, weekly capture counts and average precision for all methods are in [backtest.json](results/backtest.json). Average precision measures ranking quality across eligible cell-weeks. The capture denominator includes all reported cyclist injury collisions, including 101 outside the candidate cells or without usable coordinates in the holdout.

## Data and model design

- **NYC crash records.** The repo crash snapshot contributes 343,563 records in complete modeling weeks. The outcome counts a collision once if at least one cyclist was reported injured. Cells are established from January–June 2023 crash locations and fixed for evaluation. Features include local and neighboring crash history and seasonality. [NYC Open Data](https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95/about_data)
- **NOAA.** All four repository station files contribute pre-2023 precipitation averages by station and calendar month. Their record periods differ, so those averages are historical proxies. Overlapping daily records from Central Park, LaGuardia and JFK provide prior-week precipitation and temperature. Missing values are imputed using training medians. [NOAA daily summaries](https://www.ncei.noaa.gov/access/search/datasets/daily-summaries/)
- **311.** The committed aggregate covers 442,010 geocoded DOT requests in the Street Condition, Street Light Condition, Bike Lane and Sidewalk Condition categories. The model uses lagged cell counts. These requests reflect reporting behavior as well as street conditions. [NYC 311 source](https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9/about_data)
- **Citi Bike.** The August 2025 snapshot contributes 10,227,819 station start/end records. The feature first becomes available in September 2025 and serves as a fixed historical activity proxy. Station endpoints do not establish riding routes or represent every cyclist. The reference project informed the logistic and random forest comparisons. [Citi Bike data](https://citibikenyc.com/system-data) · [Reference repository](https://github.com/danieljinchoy/citibike)

Training uses July 2023–early April 2026. Validation begins April 6, 2026. The fixed holdout begins July 6 and ends November 1, the end of the latest complete week. Counts exclude the immediately preceding week to allow a reporting buffer. Weather comes from the preceding complete week. This retrospective evaluation uses revised source snapshots, so it cannot verify what records were actually available to planners on each prediction date. Models use the historical weather signal rather than a live forecast. Inspection findings would determine appropriate repairs.

## Reproduce

From the repository root:

```sh
python3 -m pip install -r predictive_models/requirements.txt
curl -fL https://s3.amazonaws.com/tripdata/202508-citibike-tripdata.zip -o /tmp/202508-citibike-tripdata.zip
python3 predictive_models/lab/train.py \
  --crashes Datasets/nyc_crashes_2023-01-01_to_2026-11-07.csv.gz \
  --weather predictive_models/lab/inputs/noaa_daily.csv \
  --archive Datasets/Weather \
  --complaints predictive_models/lab/inputs/311_weekly.csv.gz \
  --bike-zip /tmp/202508-citibike-tripdata.zip \
  --out predictive_models/lab/results
```

The 311 aggregate can be recreated with `python3 predictive_models/lab/prepare_311.py --out predictive_models/lab/inputs/311_weekly.csv.gz`. Its snapshot may change when the upstream dataset is revised. Raw Citi Bike trips and individual 311 requests are excluded from the repository.

To run just one fitted model and both baselines, add `--model Logistic` to the training command and use a separate output folder such as `--out /tmp/citywatch-logistic`. Repeat `--model` to compare specific models. Run `python3 predictive_models/lab/train.py --help` for the list of names.
