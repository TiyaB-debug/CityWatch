# CityWatch predictive models

CityWatch helps planners decide which Manhattan areas to inspect when they can visit only five or ten locations. The analysis separates historical patterns, borough-wide forecasts, and predictions for individual street areas.

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
- [Inspection forecast models](forecast/models.py) contain regularized and boosted Poisson models with matched weather comparisons. [Backtest](forecast/results/backtest.json) · [Daily forecasts](forecast/results/daily_forecasts.csv) · [Scenario weather](forecast/results/forecast_weather.csv)

The analysis uses overlapping crash and weather dates from January 1, 2023 through November 3, 2026. The time series excludes partial November from its observed monthly totals. The inspection forecasts use earlier data for training and later months for validation and testing. The included November 8–14 forward run uses simulated weather, and the runner accepts a future station-day CSV. Citi Bike is excluded.

[NYC crash reports](https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95/about_data) · [NOAA station data](https://www.ncei.noaa.gov/pub/data/ghcn/daily/readme.txt) · [NYC 311 service requests](https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9/about_data) · [NYC borough boundaries](https://data.cityofnewyork.us/City-Government/Borough-Boundaries/gthc-hcne)

The presentation's [311 input](presentation/inputs/manhattan_dot_311_monthly.csv.gz) contains monthly grid counts of geocoded Manhattan DOT street condition, street light, bike lane, and sidewalk condition complaints. It contains no individual request rows.

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
