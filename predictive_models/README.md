# CityWatch predictive models

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

## Original August–September 2025 pilot

CityWatch recommends roughly 500 m NYC grid cells for street inspections. The pilot trains on **August 2025** and evaluates against reported cyclist injury collisions in **September 2025**.

### Interactive map

Download [citywatch_map.html](lab/results/citywatch_map.html) and open it in a browser. The map uses Leaflet and OpenStreetMap online. Adjust the September date range, select wet, dry, or warm conditions, restrict rankings to the visible map area, and choose five or ten inspections. Each recommendation shows its predicted count or baseline score, August injury history, and weather evidence.

The blue layer shows August vehicle collision activity. The red layer shows August cyclist injury collisions. A separate September outcome layer follows the date range and is available for retrospective review. The pilot uses no Citi Bike data, so the blue layer measures reported collisions. September weather is an observed-weather forecast replay.

### Models and individual figures

- **August collision baseline** ranks cells by August cyclist injury collision count alone. [Code](lab/models/baselines.py) · [Figure](lab/results/figures/baseline.png)
- **Poisson without weather** estimates daily counts from cell, station region, weekend status, and August non-cyclist-injury collision activity. [Code](lab/models/poisson.py) · [Figure](lab/results/figures/no_weather.png)
- **Poisson with weather** adds rainfall, temperature, and station-level wet-day effects to the same inputs. Comparing the two Poisson variants tests the contribution of weather. [Figure](lab/results/figures/with_weather.png)
- **Wet/dry collision rates** estimate cell-level August rates for wet and dry days, with smoothing from the broader August history. [Code](lab/models/weather_rates.py) · [Figure](lab/results/figures/weather_rates.png)

### September evaluation

The August dataset establishes 2,063 candidate cells. Models sum daily predictions over September and make one shortlist for each budget. The denominator is all **467** reported September cyclist injury collisions, including those without usable coordinates or outside the candidate cells.

- **Five locations.** August baseline **2 of 467 (0.43%)**, Poisson without weather **2 (0.43%)**, Poisson with weather **2 (0.43%)**, and wet/dry rates **1 (0.21%)**.
- **Ten locations.** August baseline **4 of 467 (0.86%)**, Poisson without weather **3 (0.64%)**, Poisson with weather **5 (1.07%)**, and wet/dry rates **5 (1.07%)**.

Weather-aware Poisson captured one more collision than the baseline and two more than matched Poisson without weather at ten locations. It tied both at five. These small counts describe one two-month pilot. [Machine-readable results](lab/results/backtest.json)

[Daily weather-aware predictions CSV](lab/results/daily_with_weather_sep_2025.csv) contains all **61,890** candidate cell-days with `cell_id`, `latitude`, `longitude`, `date`, and `with_weather`.

### Data and scope

- [NYC Open Data collision reports](https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95/about_data) supply the labels. A collision counts once when at least one cyclist was reported injured. The pipeline uses only August and September 2025 from the repository's larger snapshot.
- [NOAA daily summaries](https://www.ncei.noaa.gov/access/search/datasets/daily-summaries/) supply daily rainfall and temperature. Each cell uses the nearest of Central Park, LaGuardia, or JFK.
- [NYC borough outlines](https://data.cityofnewyork.us/City-Government/Borough-Boundaries/gthc-hcne) provide map context. The optional [311 source downloader](../Datasets/311/) remains available for future analysis.

The prototype supports planner review of areas for inspection. Its police reports are subject to reporting and geocoding gaps. Consumer route warnings require route and cycling exposure data. Field inspections would determine appropriate repairs.

### Reproduce

From the repository root:

```sh
python3 -m pip install -r predictive_models/requirements.txt
python3 predictive_models/lab/train.py \
  --crashes Datasets/nyc_crashes_2023-01-01_to_2026-11-07.csv.gz \
  --weather predictive_models/lab/inputs/noaa_aug_sep_2025.csv \
  --out predictive_models/lab/results
```
