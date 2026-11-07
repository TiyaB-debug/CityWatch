# CityWatch predictive models

CityWatch helps planners decide which Manhattan areas to inspect when they can visit only five or ten locations. The analysis separates historical patterns, borough-wide forecasts, and predictions for individual street areas.

## Datathon evaluation and working prototype

The competition run uses the two organizer-provided **NYC crash and NOAA weather files**. It fits on **August 2025**, ranks roughly 500 m citywide cells, and checks reported cyclist injury collisions in **September 2025**. The baseline ranks by August injury collision counts. The matched Poisson models use the same crash-history and calendar inputs, with weather added in one version. September observations serve as a simulated forecast. [Organizer dataset repository](https://github.com/rutgersdsc/nyc-in-motion)

Out of 567 September cyclist injury collisions, the August baseline and both Poisson models captured **3** at five inspections. At ten, the baseline captured **6** and both Poisson models captured **5**. Weather did not improve matched Poisson capture at either budget. The denominator includes reported events without usable coordinates. [Exact results](datathon/backtest.json)

Download [the interactive prototype](datathon/citywatch_map.html) and open it in a browser. It offers date, weather, map area, model, and budget controls and shows the evidence behind each ranked cell. Leaflet and map tiles require internet access. The activity layer shows reported crashes. Citi Bike and 311 are excluded from this competition run.

To reproduce this comparison, install the dependencies below and run `bash predictive_models/datathon/reproduce.sh`. The script verifies the organizer file checksums and reuses the [pinned pilot code](https://github.com/TiyaB-debug/CityWatch/tree/f41b1db983f22446cee70df3057016b9485816c7/predictive_models/lab). In a shallow clone, fetch history with `git fetch --unshallow` first. Outputs go to `predictive_models/output/datathon` unless a different output directory is supplied.

The Manhattan figures below use a broader historical snapshot. They are exploratory and separate from the organizer-data evaluation. The prototype supports area-level inspection planning. Consumer route warnings would require route and exposure data. Field inspection determines whether and how to intervene.

## Figures for the presentation

1. [Weather, collision heat map, and 311](presentation/results/manhattan_story.png). Read this left to right. Weather describes when reported counts change, the heat map shows where crashes have clustered, and 311 adds context for where to look.
2. [Clustering map and profiles](presentation/results/clustering.png). K-means grouped 278 cells by vehicle collisions, cyclist injury collisions, and relevant DOT complaints. Two groups gave the highest silhouette score (0.64), with 67 and 211 cells. They describe differences in recorded activity and reporting volume.
3. [Monthly time-series forecast](presentation/results/time_series.png). This shows the observed monthly totals, a six-month holdout from May through October 2026, and three projected months. Repeating the same month last year had a lower mean absolute error (**18.3 collisions/month**) than Holt–Winters (**41.4**).
4. [Individual inspection forecast figures](forecast/results/figures/). Use these to explain which cells the models would prioritize and how many reported injury collisions the shortlists captured on later data.

### What to say

Temperature had a moderate positive correlation with Manhattan's daily reported cyclist injury collisions (**r = +0.43**). The linear correlation with rainfall was near zero (**r = −0.05**). The adjusted model estimated about **11% fewer reported collisions on heavy-rain days** than on dry days. These counts do not measure risk per ride.

Cells with at least three relevant DOT complaints in the previous month had about **9.1 times** the following month's reported injury collision count of cells with zero complaints, after adjusting for prior injury collisions and calendar month. Busy streets and differences in reporting may contribute to that relationship. 311 is used in the historical analysis and clustering. Its impact on the inspection forecast remains untested.

At ten inspections per month in the July–October 2026 holdout, the prior-month baseline captured **43 of 657** reported injury collisions. The validation-selected boosted model without weather captured **53**. At five locations it captured **27**, compared with **22** for the baseline. The best observed ten-location count was **60** for both regularized Poisson variants. The holdout comparison is exploratory.

## Model files and outputs

- [Weather association model](models/weather.py) fits adjusted Poisson rate ratios for rainfall and temperature. [Estimates](presentation/results/numbers.json)
- [Clustering model](models/clustering.py) compares K-means with two through six groups using silhouette scores. It fits standardized log counts on January 2023–October 2026 records. [Cell assignments](presentation/results/cluster_assignments.csv)
- [Time-series model](models/time_series.py) evaluates additive Holt–Winters with annual seasonality against the same month last year.
- [Inspection forecast models](models/inspection.py) contain regularized and boosted Poisson models with matched weather comparisons. [Backtest](forecast/results/backtest.json) · [Daily forecasts](forecast/results/daily_forecasts.csv) · [Scenario weather](forecast/results/forecast_weather.csv)

The analysis uses overlapping crash and weather dates from January 1, 2023 through November 3, 2026. The time series excludes partial November from its observed monthly totals. The inspection forecasts use earlier data for training and later months for validation and testing. The included November 8–14 forward run uses simulated weather, and the runner accepts a future station-day CSV. Citi Bike is excluded.

[NYC crash reports](https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95/about_data) · [NOAA station data](https://www.ncei.noaa.gov/pub/data/ghcn/daily/readme.txt) · [NYC 311 service requests](https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9/about_data) · [NYC borough boundaries](https://data.cityofnewyork.us/City-Government/Borough-Boundaries/gthc-hcne)

The presentation's [311 input](presentation/inputs/manhattan_dot_311_monthly.csv.gz) contains monthly grid counts of geocoded Manhattan DOT street condition, street light, bike lane, and sidewalk condition complaints. It contains no individual request rows.

## Folder guide

- [datathon/](datathon/) contains the organizer-data evaluation, map, and reproduction command.
- [models/](models/) contains the weather, clustering, time-series, and inspection model definitions.
- [data.py](data.py) and [inputs/](inputs/) handle shared crash and weather preparation, including the Manhattan boundary.
- [presentation/](presentation/) contains the figure builder, aggregated 311 input, and presentation outputs.
- [forecast/](forecast/) contains the training and scoring runner, individual forecast figures, and validation results.

## Reproduce

From the repository root:

```sh
python3 -m pip install -r predictive_models/requirements.txt
python3 predictive_models/presentation/build.py \
  --crashes Datasets/nyc_crashes_2023-01-01_to_2026-11-07.csv.gz \
  --weather-dir Datasets/Weather

python3 predictive_models/forecast/run.py \
  --crashes Datasets/nyc_crashes_2023-01-01_to_2026-11-07.csv.gz \
  --weather-dir Datasets/Weather \
  --scenario-start 2026-11-08 \
  --out predictive_models/forecast/results
```

To score real forecast weather, replace `--scenario-start` with `--forecast path/to/weather.csv`. Supply `date`, `station`, `rain_mm`, and `temperature_c` for each future day within one calendar month and all three stations (`USW00094728`, `USW00014732`, `USW00094789`).
