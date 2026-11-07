# CityWatch inspection pilot

CityWatch recommends roughly 500 m NYC grid cells for street inspections. The pilot trains on **August 2025** and evaluates against reported cyclist injury collisions in **September 2025**.

## Interactive map

Download [citywatch_map.html](lab/results/citywatch_map.html) and open it in a browser. The map uses Leaflet and OpenStreetMap online. Adjust the September date range, select wet, dry, or warm conditions, restrict rankings to the visible map area, and choose five or ten inspections. Each recommendation shows its predicted count or baseline score, August injury history, and weather evidence.

The blue layer shows August vehicle collision activity. The red layer shows August cyclist injury collisions. A separate September outcome layer follows the date range and is available for retrospective review. The pilot uses no Citi Bike data, so the blue layer measures reported collisions. September weather is an observed-weather forecast replay.

## Models and individual figures

- **August collision baseline** ranks cells by August cyclist injury collision count alone. [Code](lab/models/baselines.py) · [Figure](lab/results/figures/baseline.png)
- **Poisson without weather** estimates daily counts from cell, station region, weekend status, and August non-cyclist-injury collision activity. [Code](lab/models/poisson.py) · [Figure](lab/results/figures/no_weather.png)
- **Poisson with weather** adds rainfall, temperature, and station-level wet-day effects to the same inputs. Comparing the two Poisson variants tests the contribution of weather. [Figure](lab/results/figures/with_weather.png)
- **Wet/dry collision rates** estimate cell-level August rates for wet and dry days, with smoothing from the broader August history. [Code](lab/models/weather_rates.py) · [Figure](lab/results/figures/weather_rates.png)

## September evaluation

The August dataset establishes 2,063 candidate cells. Models sum daily predictions over September and make one shortlist for each budget. The denominator is all **467** reported September cyclist injury collisions, including those without usable coordinates or outside the candidate cells.

- **Five locations.** August baseline **2 of 467 (0.43%)**, Poisson without weather **2 (0.43%)**, Poisson with weather **2 (0.43%)**, and wet/dry rates **1 (0.21%)**.
- **Ten locations.** August baseline **4 of 467 (0.86%)**, Poisson without weather **3 (0.64%)**, Poisson with weather **5 (1.07%)**, and wet/dry rates **5 (1.07%)**.

Weather-aware Poisson captured one more collision than the baseline and two more than matched Poisson without weather at ten locations. It tied both at five. These small counts describe one two-month pilot. [Machine-readable results](lab/results/backtest.json)

[Daily weather-aware predictions CSV](lab/results/daily_with_weather_sep_2025.csv) contains all **61,890** candidate cell-days with `cell_id`, `latitude`, `longitude`, `date`, and `with_weather`.

## Data and scope

- [NYC Open Data collision reports](https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95/about_data) supply the labels. A collision counts once when at least one cyclist was reported injured. The pipeline uses only August and September 2025 from the repository's larger snapshot.
- [NOAA daily summaries](https://www.ncei.noaa.gov/access/search/datasets/daily-summaries/) supply daily rainfall and temperature. Each cell uses the nearest of Central Park, LaGuardia, or JFK.
- [NYC borough outlines](https://data.cityofnewyork.us/City-Government/Borough-Boundaries/gthc-hcne) provide map context. The optional [311 source downloader](../Datasets/311/) remains available for future analysis.

The prototype supports planner review of areas for inspection. Its police reports are subject to reporting and geocoding gaps. Consumer route warnings require route and cycling exposure data. Field inspections would determine appropriate repairs.

## Reproduce

From the repository root:

```sh
python3 -m pip install -r predictive_models/requirements.txt
python3 predictive_models/lab/train.py \
  --crashes Datasets/nyc_crashes_2023-01-01_to_2026-11-07.csv.gz \
  --weather predictive_models/lab/inputs/noaa_aug_sep_2025.csv \
  --out predictive_models/lab/results
```
