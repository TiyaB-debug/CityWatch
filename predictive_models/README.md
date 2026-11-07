# CityWatch predictive models

CityWatch ranks roughly 500 m grid cells for NYC street inspection. Its interactive map shows the August cyclist injury collision counts and Citi Bike station endpoint activity behind each recommendation. Planners can change the date range, weather filter, map area, model and inspection budget.

## How CityWatch uses AI

CityWatch fits two regularized Poisson regression models to predict the number of reported cyclist injury collisions in each cell per day. Both models learn from August 2025 using cell identity, nearest weather-station region, August Citi Bike endpoint volume and weekends. The weather model also learns from rainfall, estimated mean daily temperature and interactions between weather, station regions and bike activity. The August collision-count baseline ranks cells by the number of reported injury collisions in August.

Candidates are cells with at least one mapped August injury collision or Citi Bike endpoint. September crash labels are held out until evaluation. For the monthly inspection shortlist, daily predicted counts are summed across September and the same fixed budget is applied to each model. For weather, the map replays historical September observations as if available when making the decision. Live forecast error would need a separate evaluation.

## September 2025 backtest

Of 467 reported cyclist injury collisions, 446 had coordinates in the study bounds. All 467 count in the denominator, including collisions the system could not locate. One collision is one event with at least one reported cyclist injury.

- **5 locations** · August baseline 2 of 467 (0.43%), without weather 1 of 467 (0.21%), with weather 2 of 467 (0.43%).
- **10 locations** · August baseline 4 of 467 (0.86%), without weather 5 of 467 (1.07%), with weather 5 of 467 (1.07%).

At ten locations, both fitted models captured one more collision than the baseline. Adding weather produced no additional capture at that budget and one additional capture at five locations compared with the fitted model without weather. The small counts and single holdout month limit what can be concluded. [Machine-readable results](backtest_metrics.json)

## Run locally

From this folder, with Python 3.11 or newer:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
bash download_data.sh
python citywatch.py --crashes data/crashes.csv --weather data/weather.csv --bike-zip data/august-bike.zip
```

Open `output/citywatch_map.html` in Chrome. Leaflet and the OpenStreetMap basemap require internet access. The script also writes `output/metrics.json` and `output/daily_scores.csv`. Raw files and generated outputs stay local. The August Citi Bike archive is large, and the pipeline streams it in chunks.

## Sources and limitations

- The date window and three-station daily NOAA weather snapshot come from the [Rutgers Datathon repository](https://github.com/rutgersdsc/nyc-in-motion).
- Collision reports come from [NYC Open Data](https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95/about_data). Reports can be revised and exclude unreported events.
- Bike-share endpoints come from [Citi Bike system data](https://citibikenyc.com/system-data). The modeling workflow was inspired by the [Citi Bike rebalancing project](https://github.com/danieljinchoy/citibike). Endpoint volume measures station activity and does not identify actual routes or total cycling exposure.
- Weather is assigned from the nearest of three stations. The model estimates collision counts under observed conditions. Road conditions, causal effects and commuter route-level risk require additional data. 311 complaints were optional and are outside this model. Field inspections would determine any appropriate repairs.
