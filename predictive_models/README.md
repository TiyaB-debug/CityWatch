# CityWatch predictive models

CityWatch helps transportation planners decide where to inspect first when they can visit only five or ten areas. The historical analysis explains patterns in reported cyclist injuries, and the forecast map ranks areas for review.

## What changed over time

The overlapping history has **1,403 days and 18,698 reported cyclist injury collisions**. Start with these three standalone figures:

- [Historical timeline](relationships/results/timeline.png) shows monthly daily averages of injury collisions and temperature, plus the share of wet days.
- [Weather relationships](relationships/results/weather_relationships.png) shows how daily reported counts differ across rain and temperature groups after adjusting for year, month, day of week, and the other weather variable. Weather is the daily average of three NYC stations.
- [Prior crash activity](relationships/results/crash_history_relationship.png) compares next-month counts for cells with different numbers of injury collisions the month before.

**Heavy-rain days had about 18% fewer reported collisions than dry days** after adjustment (95% interval of roughly 13% to 23% fewer). Days below 5 °C had about **35% fewer** than days at 15–24.9 °C, while days at 25 °C or above had about **8% more**. These are citywide reported counts. The analysis has no cycling-volume denominator and cannot tell whether per-trip risk changed.

Areas with **2–3 injury collisions in the prior month** averaged **22.3 per 1,000 cell-days** the next month, compared with **3.3** for areas with none. Areas with at least four averaged **38.4**, based on 138 cell-months. These descriptive groups help explain why recent crash history matters for inspection rankings. [Relationship estimates and denominators](relationships/results/relationships.json)

The adjusted weather model is a Poisson regression of daily collision counts with calendar controls and seven-day HAC standard errors. Reproduce the analysis from the repository root:

```sh
python3 -m pip install -r predictive_models/requirements.txt
python3 predictive_models/relationships/analyze.py \
  --crashes Datasets/nyc_crashes_2023-01-01_to_2026-11-07.csv.gz \
  --weather-dir Datasets/Weather \
  --out predictive_models/relationships/results
```

## Full-overlap forecast

The models predict daily counts of police-reported cyclist injury collisions in roughly 500 m NYC cells. The crash and NOAA weather records overlap on **January 1, 2023 through November 3, 2026** and contain **344,203 collision reports**. Each cell uses the nearest of Central Park, LaGuardia, and JFK, the three repository stations used for consistent coverage. The models use no Citi Bike or 311 features. [NYC crash records](https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95/about_data) · [NOAA GHCN daily format and units](https://www.ncei.noaa.gov/pub/data/ghcn/daily/readme.txt)

### How the forecast is evaluated

January 2023 establishes the first candidate cells and lagged features. The backtest fits on February 2023–December 2025, selects a method using January–June 2026, and evaluates July–October 2026 with November 1–3 reported separately as a partial month. Candidate locations and crash features are frozen at each month start, using only prior months. The baseline ranks cells by injury collisions in the previous calendar month. Historical evaluation uses observed weather as a replay, so the reported capture does not include forecast error.

The forward models are then refitted through November 3. The published **November 8–14, 2026** scenario uses weather copied from the final seven observed days. To generate predictions with actual forecast inputs, pass a station-day CSV. The forecast is for area-level inspection prioritization.

### Full-month holdout results

July–October 2026 contained 2,076 reported cyclist injury collisions. At **10 inspections per month**, the previous-month baseline captured **43**, both regularized Poisson models captured **57**, boosted Poisson without weather captured **59**, and boosted Poisson with weather captured **62**. Validation selected boosted Poisson **without weather**. At five locations, that model captured **25** versus the baseline's **27**. Boosting with weather captured **31** at five and was the strongest model observed on the holdout, an exploratory comparison. Adding weather tied within the regularized Poisson pair and added six captures at five locations and three at ten within the boosted pair on the holdout. On November 1–3, all methods captured one of 33 reported injury collisions at both budgets.

### Model figures and outputs

- [Previous-month baseline](forecast/results/figures/previous_month_baseline.png) ranks by the prior month's reported cyclist injury collision count.
- [Poisson without weather](forecast/results/figures/poisson_no_weather.png) models daily counts from coordinates, crash history, and calendar variables.
- [Poisson with weather](forecast/results/figures/poisson_weather.png) adds daily rain and temperature to the same model.
- [Boosted Poisson without weather](forecast/results/figures/boosted_no_weather.png) captures nonlinear relationships in crash and calendar inputs.
- [Boosted Poisson with weather](forecast/results/figures/boosted_weather.png) adds weather to the same nonlinear model.

Download [the forecast inspection map](forecast/results/forecast_map.html) and open it in a browser. It has model, date, rain, location, and budget controls. The basemap requires internet access. The [forecast CSV](forecast/results/daily_forecasts.csv) includes all candidate cells for each scenario day. Its baseline column repeats the prior-month ranking count as supporting evidence. The other model columns are expected daily collision counts. [Backtest metrics](forecast/results/backtest.json) · [Scenario weather](forecast/results/forecast_weather.csv)

### Run the full-overlap forecast

From the repository root:

```sh
python3 -m pip install -r predictive_models/requirements.txt
python3 predictive_models/forecast/run.py \
  --crashes Datasets/nyc_crashes_2023-01-01_to_2026-11-07.csv.gz \
  --weather-dir Datasets/Weather \
  --scenario-start 2026-11-08 \
  --out predictive_models/forecast/results
```

Replace `--scenario-start 2026-11-08` with `--forecast path/to/weather.csv` to supply weather. Use columns `date`, `station`, `rain_mm`, and `temperature_c`, with one row per date and station. Use all three stations (`USW00094728`, `USW00014732`, `USW00094789`) for each future day within one calendar month. Crash features stay frozen at the latest issue date supported by a complete preceding month.
