"""Shrink a cell's recent injury rate toward adjacent cells."""
import numpy as np
import pandas as pd


def scores(rows):
    history = rows.set_index(["week", "y", "x"]).injury_13
    total = np.zeros(len(rows))
    neighbors = np.zeros(len(rows))
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        keys = pd.MultiIndex.from_arrays([rows.week, rows.y + dy, rows.x + dx])
        values = history.reindex(keys).to_numpy()
        total += np.nan_to_num(values)
        neighbors += np.isfinite(values)
    local_prior = np.divide(total, 13 * neighbors, out=np.zeros(len(rows)), where=neighbors > 0)
    local_prior = np.where(neighbors > 0, local_prior, rows.injury_52 / 52)
    # A Gamma prior with 13 weeks of equivalent exposure gives equal weight
    # to the observed 13-week count and the neighborhood's typical rate.
    return (rows.injury_13 + 13 * local_prior) / 26
