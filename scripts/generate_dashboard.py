#!/usr/bin/env python3
"""Generate an interactive dashboard (docs/index.html) from Intervals.icu CSV export.

Follows project guidelines: parse dates with pandas, compute pace (min/km), aggregate by week (Monday start),
and draw weekly km bars + rolling pace/volume lines. Also computes conservative weekly targets from recent base.
"""
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from pathlib import Path
import math

ROOT = Path(__file__).resolve().parents[0]
DATA = ROOT.joinpath('..').joinpath('i600311_activities.csv').resolve()
OUT = ROOT.joinpath('..').joinpath('docs')
OUT.mkdir(parents=True, exist_ok=True)

def load_and_clean(path):
    df = pd.read_csv(path)
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    runs = df[df['Tipo'].str.lower()=='run'].copy()
    runs['Distancia_km'] = runs['Distancia'].astype(float)/1000.0
    runs['Tiempo_min'] = runs['Tiempo en movimiento'].astype(float)/60.0
    runs['pace'] = runs['Tiempo_min'] / runs['Distancia_km']
    runs['week_start'] = runs['Fecha'].dt.to_period('W-MON').apply(lambda r: r.start_time)
    return runs

def weekly_aggregates(runs):
    weekly = (
        runs.groupby('week_start')
        .agg(total_km=('Distancia_km','sum'), avg_pace=('pace','mean'), n_runs=('id','count'))
        .reset_index()
        .sort_values('week_start')
    )
    weekly['week_start_str'] = weekly['week_start'].dt.strftime('%Y-%m-%d')
    weekly['rolling_km_4w'] = weekly['total_km'].rolling(4, min_periods=1).mean()
    weekly['rolling_pace_4w'] = weekly['avg_pace'].rolling(4, min_periods=1).mean()
    return weekly

def make_targets(starting_km, weeks=19):
    # conservative 10% weekly progression with step-back every 4th week (-15%)
    prog = []
    cur = starting_km
    for i in range(weeks):
        prog.append(round(cur,1))
        cur = cur * 1.10
    for i in range(3, weeks, 4):
        prog[i] = round(prog[i]*0.85,1)
    return prog

def build_dashboard(weekly, targets, plan_start):
    weeks = len(targets)
    # use target dates starting at plan_start (assumed Monday)
    dates = pd.date_range(start=plan_start, periods=weeks, freq='W-MON')
    target_series = pd.Series(targets, index=dates)

    # Observed series align by week_start
    obs_index = pd.to_datetime(weekly['week_start'])
    obs_series = pd.Series(weekly['total_km'].values, index=obs_index)

    # Build figure
    fig = go.Figure()
    fig.add_trace(go.Bar(x=obs_index, y=obs_series.values, name='Observed km', marker_color='#1f77b4'))
    fig.add_trace(go.Scatter(x=obs_index, y=weekly['rolling_km_4w'], mode='lines+markers', name='4w rolling km', line=dict(color='orange')))
    fig.add_trace(go.Scatter(x=target_series.index, y=target_series.values, mode='lines+markers', name='Planned weekly target', line=dict(color='green', dash='dash')))

    fig.update_layout(
        title='Weekly Running Volume: Observed vs Planned',
        xaxis_title='Week (start)',
        yaxis_title='Kilometers',
        template='plotly_white',
        hovermode='x unified'
    )

    # summary metrics
    latest = weekly.iloc[-1] if not weekly.empty else None
    four_week_avg = float(weekly['total_km'].tail(4).mean()) if len(weekly)>=1 else 0.0
    longest = float(runs['Distancia_km'].max()) if 'runs' in globals() else 0.0

    header_html = f"""
<h1>Munich Marathon — Training Dashboard</h1>
<p><b>Data snapshot:</b> last data point {weekly['week_start_str'].iloc[-1] if not weekly.empty else 'N/A'}</p>
<ul>
  <li><b>Recent 4-week avg:</b> {four_week_avg:.1f} km/week</li>
  <li><b>Latest weekly total:</b> {latest['total_km']:.1f if latest is not None else 0.0} km</li>
  <li><b>Longest run (observed):</b> {longest:.1f} km</li>
</ul>
"""

    html = pio.to_html(fig, full_html=False, include_plotlyjs='cdn')
    out_path = OUT.joinpath('index.html')
    with open(out_path, 'w') as f:
        f.write('<html><head><meta charset="utf-8"><title>Training Dashboard</title></head><body>')
        f.write(header_html)
        f.write(html)
        f.write('</body></html>')
    print('Wrote', out_path)


if __name__ == '__main__':
    runs = load_and_clean(DATA)
    weekly = weekly_aggregates(runs)
    # compute starting base as recent 4-week average
    recent_4w = runs[runs['Fecha'] >= runs['Fecha'].max() - pd.Timedelta(days=27)]['Distancia_km'].sum()
    start_avg = round(recent_4w/4.0,1) if recent_4w>0 else 10.0
    targets = make_targets(start_avg, weeks=19)
    plan_start = pd.to_datetime('2026-06-01')
    build_dashboard(weekly, targets, plan_start)
