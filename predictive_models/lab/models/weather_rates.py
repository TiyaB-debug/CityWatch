"""Estimate local wet and dry collision rates with pooled smoothing."""


def predict(train, target):
    history = train.assign(wet=train.rain_mm.ge(1))
    local = history.groupby(["cell_id", "wet"]).injuries.agg(["sum", "size"])
    pooled = history.groupby("wet").injuries.mean()
    city_rate = history.injuries.mean()
    incoming = target.assign(wet=target.rain_mm.ge(1)).join(local, on=["cell_id", "wet"])
    # Five pseudo-days stabilize each cell-condition estimate. The pooled
    # wet/dry rate supplies a relative adjustment to the cell's August average.
    weather_factor = incoming.wet.map(pooled).fillna(city_rate) / city_rate
    local_average = (incoming.august_collisions + 5 * city_rate) / 36
    return (incoming["sum"].fillna(0) + 5 * local_average * weather_factor) / (
        incoming["size"].fillna(0) + 5
    )
