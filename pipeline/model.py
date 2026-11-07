"""
Crash-risk forecast model: where and when injury crashes are expected,
given the day of week, time of day and the weather forecast.

    expected injury crashes in cell c on day d
        = base_c                      how crash-prone this 1 km cell is
        x dow_d                       citywide day-of-week factor
        x Lrain_k(s(c),d) x u_c,k     citywide rain lift x this cell's own rain lift
        x Lhot^hot(s,d)   x u_c,hot   same for hot days (max temp >= 30 C)

The share of a day's risk in a given time window comes from the cell's own
hour-of-day profile, shrunk toward the citywide profile.

Citywide factors come from a Poisson regression on daily injury-crash counts
in each weather-station area (each crash takes the weather of its nearest
NOAA station: Central Park, LaGuardia or JFK).

Cell-level lifts u_c,k are shrunk with a Gamma-Poisson (empirical Bayes)
prior: u ~ Gamma(a, a). The prior strength a is fitted by maximum marginal
likelihood, so the data decides how much cells really differ in weather
sensitivity. A huge a means "no detectable local difference" and every
cell gets the citywide lift.
"""
import numpy as np
from scipy.special import gammaln

# NOAA station locations (metadata for the three stations in the provided file)
STATIONS = {
    "USW00094728": ("Central Park", 40.7789, -73.9692),
    "USW00014732": ("LaGuardia", 40.7794, -73.8803),
    "USW00094789": ("JFK", 40.6386, -73.7622),
}
RAIN_LIGHT, RAIN_HEAVY, HOT_C = 1.0, 10.0, 30.0
WINDOWS = {"all": (0, 24), "am": (6, 10), "mid": (10, 15), "pm": (15, 20), "night": (20, 30)}


def rain_class(prcp):
    return np.where(prcp >= RAIN_HEAVY, 2, np.where(prcp >= RAIN_LIGHT, 1, 0))


def poisson_irls(X, y, offset, iters=50):
    beta = np.zeros(X.shape[1])
    beta[0] = np.log(max(y.mean(), 1e-6)) - offset.mean()
    for _ in range(iters):
        eta = X @ beta + offset
        mu = np.exp(eta)
        z = eta - offset + (y - mu) / mu
        W = mu
        XtW = X.T * W
        new = np.linalg.solve(XtW @ X + 1e-8 * np.eye(X.shape[1]), XtW @ z)
        if np.max(np.abs(new - beta)) < 1e-9:
            beta = new
            break
        beta = new
    return beta


def fit_city(y_ds, dow_d, rain_ds, hot_ds, days):
    """Poisson regression on [day, station-area] counts. Returns factors."""
    D, S = y_ds.shape
    rows, ys = [], []
    for d in days:
        for s in range(S):
            x = [1.0] + [float(s == j) for j in range(1, S)] \
                + [float(dow_d[d] == j) for j in range(1, 7)] \
                + [float(rain_ds[d, s] == 1), float(rain_ds[d, s] == 2), float(hot_ds[d, s])]
            rows.append(x); ys.append(y_ds[d, s])
    X, y = np.array(rows), np.array(ys, float)
    b = poisson_irls(X, y, np.zeros(len(y)))
    dow = np.exp(np.r_[0, b[S:S + 6]])
    dow = dow / dow.mean()
    return {"dow": dow, "light": float(np.exp(b[S + 6])), "heavy": float(np.exp(b[S + 7])), "hot": float(np.exp(b[S + 8]))}


def nb_strength(O, E):
    """Max marginal likelihood prior strength a for O ~ Poisson(E u), u ~ Gamma(a, a)."""
    grid = np.logspace(-1, 4, 60)
    m = E > 0
    O, E = O[m], E[m]
    ll = [np.sum(gammaln(O + a) - gammaln(a) + a * np.log(a / (a + E)) + O * np.log(E / (a + E))) for a in grid]
    return float(grid[int(np.argmax(ll))])


class RiskModel:
    def __init__(self, cell_of, sta_of_cell, day_of, hour_of, n_cells, n_days, dow_d, rain_ds, hot_ds, sta_of_crash):
        self.cell_of, self.day_of, self.hour_of = cell_of, day_of, hour_of
        self.sta_of_cell, self.sta_of_crash = sta_of_cell, sta_of_crash
        self.NC, self.ND = n_cells, n_days
        self.dow_d, self.rain_ds, self.hot_ds = dow_d, rain_ds, hot_ds

    def fit(self, train_days, mask=None):
        """mask selects which crashes count (e.g. injury crashes)."""
        td = np.zeros(self.ND, bool); td[train_days] = True
        m = td[self.day_of] & (mask if mask is not None else True)
        c, d, h, s = self.cell_of[m], self.day_of[m], self.hour_of[m], self.sta_of_crash[m]
        S = self.rain_ds.shape[1]
        y_ds = np.zeros((self.ND, S)); np.add.at(y_ds, (d, s), 1)
        city = fit_city(y_ds, self.dow_d, self.rain_ds, self.hot_ds, train_days)
        self.city = city

        # day multipliers per station area, without cell effects
        rk = self.rain_ds
        mult = city["dow"][self.dow_d][:, None] * np.where(rk == 2, city["heavy"], np.where(rk == 1, city["light"], 1.0)) \
            * np.where(self.hot_ds, city["hot"], 1.0)                                   # [ND, S]
        msum = mult[train_days][:, self.sta_of_cell].sum(0)                               # [NC]
        n_c = np.bincount(c, minlength=self.NC).astype(float)
        self.base = n_c / np.maximum(msum, 1e-9)

        # cell-level weather lifts, shrunk
        self.u, self.a = {}, {}
        dc = np.zeros((self.ND, self.NC)); np.add.at(dc, (d, c), 1)
        exp_dc = mult[:, self.sta_of_cell] * self.base[None, :]                           # [ND, NC]
        for k, sel in (("light", rk == 1), ("heavy", rk == 2), ("hot", self.hot_ds)):
            on = sel[:, self.sta_of_cell] & td[:, None]                                   # [ND, NC]
            O = (dc * on).sum(0); E = (exp_dc * on).sum(0)
            a = nb_strength(O, E) if E.sum() > 0 else 1e4
            self.a[k] = a
            self.u[k] = (O + a) / (E + a)

        # hour profile, shrunk toward city
        hc = np.zeros((self.NC, 24)); np.add.at(hc, (c, h), 1)
        city_h = hc.sum(0) / hc.sum()
        alpha = 20.0
        self.prof = (hc + alpha * city_h[None, :]) / (hc.sum(1, keepdims=True) + alpha)
        self.city_prof = city_h
        return self

    def day_lambda(self, d=None, rain=None, hot=None, dow=None, use_weather=True):
        """Expected crashes per cell for a real day d, or a scenario (rain[S], hot[S], dow)."""
        if d is not None:
            rain, hot, dow = self.rain_ds[d], self.hot_ds[d], self.dow_d[d]
        rain = np.asarray(rain)[self.sta_of_cell]; hot = np.asarray(hot, bool)[self.sta_of_cell]
        lam = self.base * self.city["dow"][dow]
        if use_weather:
            cl = np.where(rain == 2, self.city["heavy"] * self.u["heavy"], np.where(rain == 1, self.city["light"] * self.u["light"], 1.0))
            lam = lam * cl * np.where(hot, self.city["hot"] * self.u["hot"], 1.0)
        return lam

    def window_share(self, w):
        h0, h1 = WINDOWS[w]
        hrs = [h % 24 for h in range(h0, h1)]
        return self.prof[:, hrs].sum(1)