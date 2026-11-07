"""Predict Manhattan's monthly cyclist injury totals with Holt–Winters."""
import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing


def estimate(series):
    return ExponentialSmoothing(series, trend="add", damped_trend=True,
                                seasonal="add", seasonal_periods=12,
                                initialization_method="estimated").fit()


def backtest(monthly):
    # Hold out the final six complete months as a block.
    train, test = monthly.iloc[:-6], monthly.iloc[-6:]
    baseline = monthly.shift(12).reindex(test.index)
    predicted = estimate(train).forecast(len(test)).clip(lower=0)
    forward = estimate(monthly).forecast(3).clip(lower=0)
    metrics = {
        "train_end": str(train.index[-1].date()), "holdout_start": str(test.index[0].date()),
        "holdout_end": str(test.index[-1].date()),
        "seasonal_baseline_mae": float(np.abs(test - baseline).mean()),
        "holt_winters_mae": float(np.abs(test - predicted).mean()),
    }
    return test, baseline, predicted, forward, metrics
