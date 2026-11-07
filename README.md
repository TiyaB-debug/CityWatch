# CityWatch

CityWatch helps NYC transportation planners choose which five or ten areas to inspect when time is limited. It ranks roughly 500 m areas using reported cyclist injury collisions and shows the crash history and weather behind each recommendation.

Built for the **NYC in Motion Datathon** by Tiya Bordia, Tanvi Mane, and Andrew Ikemoto.

## Try the demo

Download [citywatch_map.html](predictive_models/datathon/citywatch_map.html) and open it in a browser with internet access for the basemap. Select a model, filter by September dates or weather, and set the inspection budget to five or ten. Click a highlighted area to see its supporting evidence. The demo replays observed weather as a simulated forecast.

## What we found

The **Datathon evaluation** used the organizer-provided NYC collision and NOAA weather files. We trained on August 2025 and tested against 567 reported cyclist injury collisions in September 2025. The baseline ranked areas by August injury collision counts. We compared two Poisson models with the same inputs, with weather added to one.

- **Five inspections** — The baseline and both models captured **3** September collisions.
- **Ten inspections** — The baseline captured **6** and both models captured **5**.

Weather did not improve capture in this one-month test. For this pilot, the August crash-count ranking gives planners a simple starting shortlist. [Exact results](predictive_models/datathon/backtest.json) · [Organizer datasets](https://github.com/rutgersdsc/nyc-in-motion)

## Explore the repository

- [Datasets](Datasets/) contains the crash snapshot, NOAA station files, and an optional [311 downloader](Datasets/311/).
- [Predictive models](predictive_models/README.md) explains the model code, inputs, outputs, and reproducible workflows.
- [Datathon evaluation](predictive_models/datathon/) contains the map, exact metrics, and reproduction script.
- [Manhattan presentation figures](predictive_models/presentation/results/) show collision hotspots, weather and complaint relationships, clustering, and a monthly time series. This separate exploratory analysis uses a broader historical snapshot.
- [Manhattan inspection forecasts](predictive_models/forecast/results/) contains individual model figures, backtest metrics, and daily forecast outputs.

## Team demo and inspection assignments

- [Crash risk map](web/index.html), [agency briefing](web/agency.html), and [commuter concept](web/commuter.html) are prebuilt HTML demos. Download and open the desired page locally. The commuter view is a prototype for exploring reported crash patterns.
- [Team pipeline](pipeline/build.py) builds the team demo from organizer CSVs in a local `data/` folder. Its docstring lists the four input filenames. Install the [team pipeline requirements](requirements.txt) and run `python3 pipeline/build.py` from the repository root. This pipeline uses a 1 km grid and reports its own [evaluation](results/eval.json), separate from the 500 m comparison above.
- [Inspection allocator](optimization/allocator.py) takes daily area scores and assigns inspection visits to teams. See the [sample assignments](assignments.csv) and [assignment map](inspection_map.html). The [example runner](run_optimizer.py) references an archived prediction path and needs an input CSV path update before rerunning.

## Reproduce the Datathon test

From the root of a full clone:

```sh
python3 -m pip install -r predictive_models/requirements.txt
bash predictive_models/datathon/reproduce.sh
```

The script downloads and verifies the two organizer files and writes results to `predictive_models/output/datathon/`. The [model README](predictive_models/README.md#reproduce) includes the separate Manhattan workflows.

## Scope and limitations

The map supports area-level inspection planning. Police reports can miss collisions, and some records lack usable coordinates. The test uses one holdout month and has no cycling-volume denominator. Citi Bike and 311 are excluded from the Datathon models. The separate Manhattan analysis uses aggregated DOT 311 complaints for historical context. Route warnings would require route and cycling exposure data, and field inspections determine what action is appropriate.

[NYC collision records](https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95/about_data) · [NOAA daily weather](https://www.ncei.noaa.gov/access/search/datasets/daily-summaries/) · [NYC 311 service requests](https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9/about_data)
