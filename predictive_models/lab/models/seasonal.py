"""Estimate risk from the same season in previous years."""
import numpy as np


def scores(rows):
    # Compare corresponding weeks, with a four-week allowance on either side.
    history = rows.pivot(index="cell_id", columns="week", values="injury")
    counts = history.to_numpy()
    analog = np.zeros_like(counts)
    exposure = np.zeros(counts.shape[1])
    for year in (1, 2, 3):
        for offset in range(-4, 5):
            lag = 52 * year + offset
            weight = (5 - abs(offset)) / year
            analog[:, lag:] += weight * counts[:, :-lag]
            exposure[lag:] += weight
    # Use four pseudo-weeks at the recent local rate to stabilize sparse analogs.
    seasonal = history.copy()
    seasonal.iloc[:, :] = analog
    index = rows.set_index(["cell_id", "week"]).index
    weighted_counts = seasonal.stack().reindex(index).to_numpy()
    observed_weight = dict(zip(history.columns, exposure))
    return (weighted_counts + 4 * rows.injury_13 / 13) / (rows.week.map(observed_weight) + 4)
