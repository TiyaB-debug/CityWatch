"""
Build the crash-risk forecast: clean data, fit the model, evaluate it on
held-out days, and write the map page with all data embedded.

    python pipeline/build.py            # reads data/*.csv, writes web/index.html, web/satellite.html, results/eval.json

Inputs (provided datathon datasets):
    data/nyc_crashes_aug_sep_2025.csv          NYPD Motor Vehicle Collisions
    data/noaa_daily_weather_aug_sep_2025.csv   NOAA daily summaries (Central Park, LaGuardia, JFK)
    data/nyc311_dot_aug_sep_2025.csv           NYC 311 DOT service requests
    data/mta_station_accessibility_current.csv MTA subway stations (only used to name map cells)
"""
import json, os, sys
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(__file__))
from model import RiskModel, STATIONS, rain_class, fit_city, HOT_C, WINDOWS

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(ROOT, "data")
CELL_M = 1000
LAT0 = 40.70
MX, MY = 111320 * np.cos(np.radians(LAT0)), 110540
rng = np.random.default_rng(7)


def to_xy(lat, lng):
    return (lng + 74.30) * MX, (lat - 40.45) * MY


def to_ll(x, y):
    return y / MY + 40.45, x / MX - 74.30


def load():
    c = pd.read_csv(os.path.join(DATA, "nyc_crashes_aug_sep_2025.csv"))
    n0 = len(c)
    c = c[(c.latitude.between(40.49, 40.92)) & (c.longitude.between(-74.27, -73.68))].copy()
    c["date"] = pd.to_datetime(c.crash_date).dt.normalize()
    c["hour"] = pd.to_datetime(c.crash_time, format="%H:%M").dt.hour
    c["inj"] = (c.number_of_persons_injured.fillna(0) + c.number_of_persons_killed.fillna(0)) > 0
    c["cyc"] = c.number_of_cyclist_injured.fillna(0) > 0
    print(f"crashes: {n0:,} rows, {len(c):,} with usable NYC coordinates")

    w = pd.read_csv(os.path.join(DATA, "noaa_daily_weather_aug_sep_2025.csv"), parse_dates=["DATE"])
    s311 = pd.read_csv(os.path.join(DATA, "nyc311_dot_aug_sep_2025.csv"), parse_dates=["created_date", "closed_date"])
    s311 = s311.dropna(subset=["latitude", "longitude"])
    mta = pd.read_csv(os.path.join(DATA, "mta_station_accessibility_current.csv"))
    return c, w, s311, mta


def main():
    c, w, s311, mta = load()
    dates = pd.date_range(c.date.min(), c.date.max(), freq="D")
    ND = len(dates)
    day_i = {d: i for i, d in enumerate(dates)}
    sta_ids = list(STATIONS)
    S = len(sta_ids)

    # weather matrices [day, station]
    W = w.pivot(index="DATE", columns="STATION", values=["PRCP", "TMAX"]).reindex(dates)
    prcp = W["PRCP"][sta_ids].values
    tmax = W["TMAX"][sta_ids].values
    rain_ds = rain_class(prcp)
    hot_ds = tmax >= HOT_C
    dow_d = dates.dayofweek.values

    # grid cells
    x, y = to_xy(c.latitude.values, c.longitude.values)
    ix, iy = (x // CELL_M).astype(int), (y // CELL_M).astype(int)
    key = ix * 1000 + iy
    ukeys, cell_of = np.unique(key, return_inverse=True)
    NC = len(ukeys)
    cx = (ukeys // 1000 + 0.5) * CELL_M; cy = (ukeys % 1000 + 0.5) * CELL_M
    clat, clng = to_ll(cx, cy)
    sxy = np.array([to_xy(v[1], v[2]) for v in STATIONS.values()])
    sta_of_cell = cKDTree(sxy).query(np.c_[cx, cy])[1]
    sta_of_crash = sta_of_cell[cell_of]
    day_of = c.date.map(day_i).values
    hour_of = c.hour.values
    inj = c.inj.values; cyc = c.cyc.values
    print(f"{NC} cells of {CELL_M} m with at least one crash; {ND} days; wet days (any station >= 1 mm): {(rain_ds.max(1) >= 1).sum()}")

    def model():
        return RiskModel(cell_of, sta_of_cell, day_of, hour_of, NC, ND, dow_d, rain_ds, hot_ds, sta_of_crash)

    full = model().fit(np.arange(ND), mask=inj)
    print("city factors:", {k: (round(v, 3) if isinstance(v, float) else np.round(v, 3).tolist()) for k, v in full.city.items()})
    print("prior strength a:", {k: round(v, 1) for k, v in full.a.items()})

    # ---------------- evaluation ----------------
    inj_dc = np.zeros((ND, NC)); np.add.at(inj_dc, (day_of[inj], cell_of[inj]), 1)
    Ks = [25, 50, 100]
    cap = {m: {k: [0, 0] for k in Ks} for m in ("forecast", "no_weather", "crash_count")}
    cap_wet = {m: {k: [0, 0] for k in Ks} for m in cap}
    ll = {"forecast": 0.0, "no_weather": 0.0}; ll_wet = {"forecast": 0.0, "no_weather": 0.0}
    loo = np.zeros((ND, NC))
    # time-window test: does each cell's own hour profile rank cells better than an all-day ranking?
    inj_dwc = {}
    for wname, (h0, h1) in WINDOWS.items():
        if wname == "all":
            continue
        hrs = np.array([h % 24 for h in range(h0, h1)])
        sel = inj & np.isin(hour_of, hrs)
        a_ = np.zeros((ND, NC)); np.add.at(a_, (day_of[sel], cell_of[sel]), 1)
        inj_dwc[wname] = a_
    capw = {wname: {"cell_profile": [0, 0], "all_day_rank": [0, 0]} for wname in inj_dwc}
    wet_day = rain_ds.max(1) >= 1
    for d in range(ND):
        tr = np.r_[0:d, d + 1:ND]
        m = model().fit(tr, mask=inj)
        lf = m.day_lambda(d); ln = m.day_lambda(d, use_weather=False)
        cnt = inj_dc[tr].sum(0)
        loo[d] = lf
        act = inj_dc[d]
        for name, score in (("forecast", lf), ("no_weather", ln), ("crash_count", cnt + 1e-6 * lf)):
            order = np.argsort(-score)
            for k in Ks:
                hit = act[order[:k]].sum()
                cap[name][k][0] += hit; cap[name][k][1] += act.sum()
                if wet_day[d]:
                    cap_wet[name][k][0] += hit; cap_wet[name][k][1] += act.sum()
        for wname, a_ in inj_dwc.items():
            actw = a_[d]
            for nm, sc in (("cell_profile", lf * m.window_share(wname)), ("all_day_rank", lf)):
                o = np.argsort(-sc)[:50]
                capw[wname][nm][0] += actw[o].sum(); capw[wname][nm][1] += actw.sum()
        for name, lam in (("forecast", lf), ("no_weather", ln)):
            lam = np.maximum(lam, 1e-9)
            v = float(np.sum(act * np.log(lam) - lam))
            ll[name] += v
            if wet_day[d]:
                ll_wet[name] += v

    # calibration: do the top 10 areas get a crash as often as the model says?
    calib = {}
    for wname, (h0, h1) in WINDOWS.items():
        hrs = np.array([h % 24 for h in range(h0, h1)])
        sel = inj & np.isin(hour_of, hrs)
        a_ = np.zeros((ND, NC)); np.add.at(a_, (day_of[sel], cell_of[sel]), 1)
        share = full.window_share(wname)
        obs, pred = [], []
        for d in range(ND):
            lw = loo[d] * share
            top = np.argsort(-lw)[:10]
            obs += (a_[d, top] > 0).tolist(); pred += (1 - np.exp(-lw[top])).tolist()
        calib[wname] = {"observed": round(float(np.mean(obs)) * 100, 1), "predicted": round(float(np.mean(pred)) * 100, 1)}

    def fmt(cp):
        return {name: {f"top_{k}": round(a / b, 4) for k, (a, b) in v.items()} for name, v in cp.items()}

    # city-level weather effects with bootstrap CIs, for three outcomes
    effects = {}
    for label, msk in (("all_crashes", np.ones(len(c), bool)), ("injury_crashes", inj), ("cyclist_injury_crashes", cyc)):
        y_ds = np.zeros((ND, S)); np.add.at(y_ds, (day_of[msk], sta_of_crash[msk]), 1)
        est = fit_city(y_ds, dow_d, rain_ds, hot_ds, np.arange(ND))
        boots = [fit_city(y_ds, dow_d, rain_ds, hot_ds, rng.integers(0, ND, ND)) for _ in range(300)]
        effects[label] = {k: {"lift": round(est[k], 3), "ci95": [round(float(np.quantile([b[k] for b in boots], q)), 3) for q in (0.025, 0.975)]}
                          for k in ("light", "heavy", "hot")}

    # does rain shift WHERE injury crashes happen? permutation test on the cell x wet/dry table
    def g_for(rmat):
        f = np.zeros(len(c), bool); f[inj] = rmat[day_of[inj], sta_of_crash[inj]] >= 1
        t = np.zeros((NC, 2)); np.add.at(t, (cell_of[inj], f[inj].astype(int)), 1)
        t = t[t.sum(1) > 0]
        e = t.sum(1, keepdims=True) * t.sum(0, keepdims=True) / t.sum()
        m_ = t > 0
        return float(2 * np.sum(t[m_] * np.log(t[m_] / e[m_])))
    g_obs = g_for(rain_ds)
    g_null = [g_for(rain_ds[rng.permutation(ND)]) for _ in range(499)]
    p_shift = (1 + sum(g >= g_obs for g in g_null)) / (1 + len(g_null))

    daily = pd.DataFrame({"n": np.bincount(day_of, minlength=ND), "inj": np.bincount(day_of[inj], minlength=ND),
                          "rain": rain_ds[:, 0]})
    ev = {
        "data": {"crashes_used": int(len(c)), "injury_crashes": int(inj.sum()), "cells": int(NC), "days": ND,
                 "wet_days_any_station": int(wet_day.sum()), "cell_size_m": CELL_M},
        "daily_means_central_park_rain_class": daily.groupby("rain")[["n", "inj"]].mean().round(1).rename(index={0: "dry", 1: "light", 2: "heavy"}).to_dict(),
        "citywide_weather_effects": effects,
        "rain_shifts_location_of_injury_crashes": {"G": round(g_obs, 1), "permutation_p": round(p_shift, 3),
                                                   "null_mean_G": round(float(np.mean(g_null)), 1)},
        "cell_prior_strength_a": {k: round(v, 1) for k, v in full.a.items()},
        "loo_capture_all_days": fmt(cap),
        "loo_capture_wet_days": fmt(cap_wet),
        "loo_poisson_loglik": {"all_days": {k: round(v, 1) for k, v in ll.items()}, "wet_days": {k: round(v, 1) for k, v in ll_wet.items()}},
        "loo_capture_top50_by_time_window": {w_: {k: round(a / b, 4) for k, (a, b) in v.items()} for w_, v in capw.items()},
        "top10_crash_chance_calibration_pct": calib,
        "share_of_cells_top_k": {f"top_{k}": round(k / NC, 4) for k in Ks},
    }
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    json.dump(ev, open(os.path.join(ROOT, "results", "eval.json"), "w"), indent=1)
    print(json.dumps(ev, indent=1))

    # ---------------- cell attributes ----------------
    n_all = np.bincount(cell_of, minlength=NC)
    n_inj = np.bincount(cell_of[inj], minlength=NC)
    n_cyc = np.bincount(cell_of[cyc], minlength=NC)
    killed = np.bincount(cell_of, weights=c.number_of_persons_killed.fillna(0).values, minlength=NC)
    persons_inj = np.bincount(cell_of, weights=c.number_of_persons_injured.fillna(0).values, minlength=NC)
    night = np.bincount(cell_of[(hour_of >= 20) | (hour_of < 6)], minlength=NC)
    boro = c.assign(cell=cell_of).dropna(subset=["borough"]).groupby("cell").borough.agg(lambda v: v.mode().iat[0])
    boro = [boro.get(i, "") for i in range(NC)]
    # nearest subway station name
    mxy = np.c_[to_xy(mta.gtfs_latitude.values, mta.gtfs_longitude.values)]
    dist, j = cKDTree(mxy).query(np.c_[cx, cy])
    names = [(f"{mta.stop_name.iat[k]} ({mta.daytime_routes.iat[k].replace(' ', ', ')})" if dd < 900 else "") for dd, k in zip(dist, j)]

    # every subway stop, mapped to the cell it sits in (for search)
    mx_, my_ = to_xy(mta.gtfs_latitude.values, mta.gtfs_longitude.values)
    mkey = (mx_ // CELL_M).astype(int) * 1000 + (my_ // CELL_M).astype(int)
    mpos = np.searchsorted(ukeys, mkey)
    stops = sorted({(f"{mta.stop_name.iat[i]} ({mta.daytime_routes.iat[i].replace(' ', ', ')})", int(mpos[i]),
                     round(float(mta.gtfs_latitude.iat[i]), 5), round(float(mta.gtfs_longitude.iat[i]), 5))
                    for i in range(len(mta)) if mpos[i] < NC and ukeys[mpos[i]] == mkey[i]})

    # 311 DOT requests per cell
    cat_map = {"Street Condition": 0, "Street Light Condition": 1, "Traffic Signal Condition": 2,
               "Sidewalk Condition": 3, "Curb Condition": 3}
    s311 = s311[s311.complaint_type.isin(cat_map)].copy()
    s311["cat"] = s311.complaint_type.map(cat_map)
    s311["open_end"] = s311.status != "Closed"
    sx, sy = to_xy(s311.latitude.values, s311.longitude.values)
    skey = (sx // CELL_M).astype(int) * 1000 + (sy // CELL_M).astype(int)
    pos = np.searchsorted(ukeys, skey)
    ok = (pos < NC) & (ukeys[np.minimum(pos, NC - 1)] == skey)
    i311 = np.zeros((NC, 5), int)
    np.add.at(i311, (pos[ok], s311.cat.values[ok]), 1)
    np.add.at(i311[:, 4], pos[ok][s311.open_end.values[ok]], 1)
    res_h = (s311.closed_date - s311.created_date).dt.total_seconds() / 3600
    s311_summary = s311.assign(h=res_h).groupby("complaint_type").h.median().round(1).to_dict()

    win_share = {w_: np.round(full.window_share(w_), 4).tolist() for w_ in WINDOWS}

    out = {
        "meta": {
            "cell_m": CELL_M, "dates": [d.strftime("%Y-%m-%d") for d in dates], "dow": dow_d.tolist(),
            "stations": [{"id": k, "name": v[0], "lat": v[1], "lng": v[2]} for k, v in STATIONS.items()],
            "prcp": np.round(prcp, 1).tolist(), "tmax": np.round(tmax, 1).tolist(),
            "city": {"dow": np.round(full.city["dow"], 4).tolist(), "light": round(full.city["light"], 4),
                     "heavy": round(full.city["heavy"], 4), "hot": round(full.city["hot"], 4)},
            "eval": ev, "s311_median_hours_to_close": s311_summary,
            "city_hour_profile": np.round(full.city_prof, 4).tolist(),
        },
        "cells": {
            "lat": np.round(clat, 5).tolist(), "lng": np.round(clng, 5).tolist(), "sta": sta_of_cell.tolist(),
            "base": np.round(full.base, 5).tolist(),
            "u_light": np.round(full.u["light"], 3).tolist(), "u_heavy": np.round(full.u["heavy"], 3).tolist(), "u_hot": np.round(full.u["hot"], 3).tolist(),
            "win": win_share, "n_all": n_all.tolist(), "n_inj": n_inj.tolist(), "n_cyc": n_cyc.tolist(),
            "persons_inj": persons_inj.astype(int).tolist(), "killed": killed.astype(int).tolist(), "night": night.tolist(),
            "boro": boro, "name": names, "i311": i311.tolist(), "stops": [list(x) for x in stops],
        },
        "loo": np.round(loo, 3).tolist(),
        "crashes": {"lat": np.round(c.latitude.values, 5).tolist(), "lng": np.round(c.longitude.values, 5).tolist(),
                    "day": day_of.tolist(), "hour": hour_of.tolist(), "inj": inj.astype(int).tolist(), "cyc": cyc.astype(int).tolist(),
                    "cell": cell_of.tolist()},
    }
    import make_satellite  # noqa: F401  (regenerates web/template_satellite.html from template.html)
    payload = json.dumps(out, separators=(",", ":"))
    for tname, oname in (("template.html", "index.html"), ("template_satellite.html", "satellite.html"),
                         ("template_agency.html", "agency.html"), ("template_commuter.html", "commuter.html")):
        tpl = open(os.path.join(ROOT, "web", tname)).read()
        html = tpl.replace("/*__DATA__*/null", payload)
        open(os.path.join(ROOT, "web", oname), "w").write(html)
        print(f"wrote web/{oname} ({len(html) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()