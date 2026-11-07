"""Build the Manhattan figures used to present CityWatch."""
import argparse
import json
import sys
from pathlib import Path
import pandas as pd,numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.patches import Polygon
from matplotlib.colors import LogNorm
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "predictive_models"))
from forecast.run import load, grid, locations, in_manhattan
from models.weather import daily_history, adjusted_weather
from models.clustering import cluster
from models.time_series import backtest

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--crashes", type=Path, required=True)
parser.add_argument("--weather-dir", type=Path, required=True)
parser.add_argument("--out", type=Path, default=Path(__file__).with_name("results"))
args = parser.parse_args()
out = args.out
out.mkdir(parents=True, exist_ok=True)
crashes, weather, dates = load(args.crashes, args.weather_dir)
inside=in_manhattan(crashes)
valid=crashes.latitude.between(40.48,40.93)&crashes.longitude.between(-74.27,-73.68)
mapped=grid(crashes.loc[inside],'latitude','longitude')
daily=daily_history(crashes.loc[inside|(~valid&crashes.borough.eq('MANHATTAN'))],weather.loc[weather.station.eq('USW00094728')],dates)
effects=adjusted_weather(daily)
corr=daily[['injuries','rain_mm','temperature_c']].corr().loc['injuries'].to_dict()
requests = pd.read_csv(Path(__file__).with_name("inputs") / "manhattan_dot_311_monthly.csv.gz")
requests["month"] = pd.PeriodIndex(requests.month, freq="M")
mapped['month']=mapped.date.dt.to_period('M')
by_crash=mapped.groupby(['month','y','x']).injury.sum()
by_request=requests.groupby(['month','y','x']).requests.sum()
cells=locations(mapped)
parts=[]
for month in dates.to_period('M').unique()[1:]:
    if month.end_time.normalize()>dates[-1]: continue
    frame=cells.loc[cells.first_seen.lt(month.start_time)].copy()
    def keys(when): return pd.MultiIndex.from_arrays([[when]*len(frame),frame.y,frame.x])
    frame['injuries']=by_crash.reindex(keys(month),fill_value=0).to_numpy()
    frame['prior']=by_crash.reindex(keys(month-1),fill_value=0).to_numpy()
    frame['complaints']=by_request.reindex(keys(month-1),fill_value=0).to_numpy()
    frame['month']=str(month)
    frame['days']=month.days_in_month
    parts.append(frame)
rows=pd.concat(parts)
rows['group']=pd.cut(rows.complaints,[-1,0,2,np.inf],labels=['0','1–2','3+'])
rows['prior_group']=rows.prior.clip(upper=3).astype(str)
fit=smf.glm('injuries ~ C(group) + C(prior_group) + C(month)',data=rows,
    offset=np.log(rows.days),family=sm.families.Poisson()).fit(cov_type='cluster',cov_kwds={'groups':rows.cell_id})
rr={name:[float(np.exp(fit.params[name])),*np.exp(fit.conf_int().loc[name]).tolist()] for name in fit.params.index if name.startswith('C(group)')}
summary={'correlation':corr,'weather':effects,'injuries':int(daily.injuries.sum()),'complaints':int(requests.requests.sum()),'complaint_rate_ratios':rr}
fig=Figure(figsize=(13,4.9),facecolor='#f3f7f8')
FigureCanvasAgg(fig)
a,b,c=fig.subplots(1,3,gridspec_kw={'width_ratios':[1.15,1.05,1]})
fig.subplots_adjust(left=.07,right=.97,top=.70,bottom=.22,wspace=.6)
fig.text(.07,.94,'CityWatch | What helps identify Manhattan hotspots?',fontsize=21,fontweight='bold',color='#173743')
fig.text(.07,.865,'January 2023–November 3, 2026 · Police-reported cyclist injury collisions',fontsize=11,color='#45606b')
rain=effects['rain'][2]; temp=effects['temp'][0]
for y,row in enumerate([rain,temp]):
    v=row['adjusted_ratio']; lo,hi=row['interval']
    a.errorbar(v,y,xerr=[[v-lo],[hi-v]],fmt='o',color='#087e84',capsize=4)
a.axvline(1,ls='--',color='#687f88')
a.set_yticks([0,1],['Heavy rain','Below 5 °C'])
a.set(xlim=(.52,1.16),ylim=(1.55,-.55),xlabel='Adjusted count ratio',title='1  Weather and collision counts')
a.text(.5,-.23,'Compared with dry days and 15–24.9 °C',transform=a.transAxes,ha='center',fontsize=8)
geo=json.loads((root/'predictive_models/forecast/inputs/manhattan.geojson').read_text())
for poly in geo['coordinates']: b.add_patch(Polygon(poly[0],facecolor='#dce8eb',edgecolor='#9cb3bb',lw=.35))
heat=mapped.loc[mapped.injury.gt(0)].groupby(['y','x']).injury.sum().reset_index()
from forecast.features import LAT_ORIGIN,LAT_STEP,LON_ORIGIN,LON_STEP
points=b.scatter(LON_ORIGIN+(heat.x+.5)*LON_STEP,LAT_ORIGIN+(heat.y+.5)*LAT_STEP,c=heat.injury,
    cmap='YlOrRd',norm=LogNorm(vmin=1,vmax=heat.injury.max()),s=25,marker='s')
b.set(xlim=(-74.025,-73.90),ylim=(40.695,40.888),aspect=1/.76,title='2  Where collisions cluster')
b.set_axis_off()
scale = fig.colorbar(points, ax=b, shrink=.73, label="Collisions per 500 m cell")
ticks = [value for value in (1, 5, 10, 25, 50, 100) if value <= heat.injury.max()]
scale.set_ticks(ticks, labels=[str(value) for value in ticks])
for y,(name,(v,lo,hi)) in enumerate(rr.items()):
    c.errorbar(v,y,xerr=[[v-lo],[hi-v]],fmt='o',color='#087e84',capsize=4)
c.axvline(1,ls='--',color='#687f88')
c.set_yticks([0,1],['1–2','3+'])
c.set(ylim=(1.55,-.55),xlabel='Adjusted count ratio vs. zero',title='3  Prior-month DOT complaints')
c.text(.5,-.23,'Adjusted for recent crashes and calendar month',transform=c.transAxes,ha='center',fontsize=8)
for ax in [a,c]: ax.spines[['top','right']].set_visible(False)
fig.text(.07,.045,'Sources: NYC Open Data crash and 311 reports; NOAA Central Park daily weather. Bars show 95% intervals.',fontsize=9,color='#45606b')
fig.savefig(out/'manhattan_story.png',dpi=150)

# Compare each cell on a shared, complete observation window.
complete = dates[-1].to_period("M") - 1
historical = mapped.loc[mapped.month.le(complete)]
counts = historical.groupby(["y", "x"]).injury.agg(
    **{"Vehicle collisions": "size", "Cyclist injury collisions": "sum"}
)
complaints = requests.loc[requests.month.le(complete)].groupby(["y", "x"]).requests.sum()
cluster_input = counts.join(complaints.rename("DOT complaints")).fillna(0).reset_index()
cluster_input["longitude"] = LON_ORIGIN + (cluster_input.x + .5) * LON_STEP
cluster_input["latitude"] = LAT_ORIGIN + (cluster_input.y + .5) * LAT_STEP
assigned, profiles, cluster_metrics = cluster(cluster_input)
assigned.to_csv(out / "cluster_assignments.csv", index=False)
summary["clustering"] = cluster_metrics

colors = ["#588399", "#008779", "#a84b24", "#6952a3", "#ad3e65", "#886700"]
fig = Figure(figsize=(10.5, 5.4), facecolor="#f3f7f8")
FigureCanvasAgg(fig)
a, b = fig.subplots(1, 2, gridspec_kw={"width_ratios": [1, 1.3]})
fig.subplots_adjust(top=.72, bottom=.22, left=.10, right=.94, wspace=.64)
fig.text(.10, .91, "Manhattan street-area profiles", fontsize=22, fontweight="bold", color="#173743")
fig.text(.10, .84, "K-means groups cells by vehicle collisions, cyclist injuries, and DOT complaints",
         fontsize=10, color="#45606b")
for poly in geo["coordinates"]:
    a.add_patch(Polygon(poly[0], facecolor="#dce8eb", edgecolor="#9cb3bb", lw=.35))
for label, cells in assigned.groupby("cluster"):
    a.scatter(cells.longitude, cells.latitude, s=14, marker="s", color=colors[label-1],
              label=f"Group {label} · {len(cells)} cells")
a.set(xlim=(-74.025,-73.90), ylim=(40.695,40.888), aspect=1/.76, title="Where the groups appear")
a.set_axis_off()
a.legend(loc="upper center", bbox_to_anchor=(.5,-.015), frameon=False, ncols=2, fontsize=8)
for label, profile in profiles.iterrows():
    b.plot(profile.index, profile.values, color=colors[label-1], marker="o", label=f"Group {label}")
b.axhline(0, linestyle="--", color="#6e828a", linewidth=1)
b.set(title="What distinguishes each group", ylabel="Average standardized feature")
b.set_xticks(range(3), ["Vehicle\ncollisions","Cyclist injury\ncollisions","DOT\ncomplaints"])
b.spines[["top", "right"]].set_visible(False)
fig.text(.10,.04,"Jan 2023–Oct 2026 · Higher values indicate more recorded events · NYC Open Data crashes and 311.",
         fontsize=8,color="#45606b")
fig.savefig(out / "clustering.png", dpi=150)

monthly = daily.injuries.resample("MS").sum().iloc[:-1]
test, seasonal, predicted, forward, series_metrics = backtest(monthly)
summary["time_series"] = series_metrics
fig = Figure(figsize=(10.5, 4.9), facecolor="#f3f7f8")
FigureCanvasAgg(fig)
ax = fig.subplots()
fig.subplots_adjust(top=.73,bottom=.18,left=.11,right=.96)
fig.text(.11,.91,"Manhattan cyclist injury collisions over time",fontsize=21,fontweight="bold",color="#173743")
fig.text(.11,.84,
         f"Six-month holdout · average error: seasonal baseline {series_metrics['seasonal_baseline_mae']:.1f} "
         f"vs. Holt–Winters {series_metrics['holt_winters_mae']:.1f} collisions per month",
         fontsize=10,color="#45606b")
ax.plot(monthly, color="#173743",linewidth=1.6,label="Observed")
ax.axvspan(test.index[0],test.index[-1]+pd.offsets.MonthBegin(),color="#dce8eb",label="Holdout")
ax.plot(seasonal,color="#a84b24",linestyle="--",label="Same month last year")
ax.plot(predicted,color="#008779",linewidth=2,label="Holt–Winters holdout")
ax.plot(forward,color="#6952a3",linestyle=":",marker="o",label="Holt–Winters projection")
forward_baseline = monthly.reindex(forward.index - pd.DateOffset(years=1))
ax.plot(forward.index, forward_baseline, color="#a84b24", linestyle=":", marker="x",
        label="Seasonal baseline projection")
ax.set(xlabel="Month",ylabel="Reported injury collisions",ylim=(0,None))
ax.grid(axis="y",alpha=.2)
ax.spines[["top","right"]].set_visible(False)
ax.legend(ncols=3,frameon=False,fontsize=8)
fig.text(.11,.035,"Source: NYC Open Data crash reports. The forward projection starts after October, the last complete month.",
         fontsize=8,color="#45606b")
fig.savefig(out / "time_series.png", dpi=150)
(out / "numbers.json").write_text(json.dumps(summary, indent=2) + "\n")
