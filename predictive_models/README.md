# CityWatch predictive models

CityWatch ranks roughly 500 m NYC grid cells for weekly street inspections. The models forecast reported cyclist injury collisions or the probability that a cell will have at least one. The backtest compares how many collisions each ranking captures at the same weekly inspection budget.

## Models

- [Poisson regression](lab/models/poisson.py) predicts the **expected number of injury collisions** per cell-week.
- [Logistic regression](lab/models/logistic.py) estimates the **probability of at least one injury collision** using a linear combination of the input features.
- [Random forest](lab/models/random_forest.py) estimates that probability by averaging decision trees trained on bootstrap samples.
- [Extra trees](lab/models/extra_trees.py) estimates that probability using an ensemble with randomized split thresholds.
- [Gradient boosting](lab/models/gradient_boosting.py) estimates that probability with trees trained in sequence. The full version uses crash history, weather, 311 complaints, and Citi Bike activity. Four variants remove weather, 311, or Citi Bike one at a time, or use crash history and calendar features only. These comparisons show how much each input adds to this model.
- [Historical baselines](lab/models/baselines.py) rank cells by their 13-week or 52-week injury collision counts. They provide a benchmark at each inspection budget.

## Supporting files

- [Training runner](lab/train.py) builds the features, fits models, selects a method on validation data, and evaluates it on the holdout. Add `--model Logistic` to run that model with both baselines.
- [Feature preparation](lab/features.py) defines the spatial grid and aggregates August Citi Bike station endpoints. [311 preparation](lab/prepare_311.py) builds weekly street-complaint counts from NYC Open Data.
- [Inputs](lab/inputs/) contains the NOAA observation snapshot and the weekly 311 aggregate used by the backtest. The [run instructions](lab/README.md#reproduce) identify the crash file, weather archive snapshot, and Citi Bike download.
- [Results](lab/results/) contains the backtest metrics and the animated inspection replay. Download and open [the replay](lab/results/citywatch_lab.html) in a browser to compare budgets and models. [replay.html](lab/replay.html) is the template the runner uses to generate it.
- [Requirements](requirements.txt) lists the Python dependencies.

See the [forecast lab analysis](lab/README.md) for the validation and holdout results, data sources, limitations, and commands to reproduce the backtest.
