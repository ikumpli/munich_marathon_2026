#!/usr/bin/env python3
"""Generate an interactive dashboard (docs/index.html) from Intervals.icu CSV export.

Follows project guidelines: parse dates with pandas, compute pace (min/km), aggregate by week (Monday start),
and draw weekly km bars + rolling pace/volume lines. Also computes conservative weekly targets from recent base.

CSV columns (Intervals.icu English export):
  id, Type, Date, Distance (meters), Moving Time (seconds), Name, Avg HR, Norm Power,
  Intensity, Load, FTP, Weight, W'
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
DATA = ROOT.joinpath('..').joinpath('i600311_activities.csv').resolve()
OUT = ROOT.joinpath('..').joinpath('docs')
OUT.mkdir(parents=True, exist_ok=True)

MARATHON_DATE = '2026-10-11'
PLAN_START = '2026-06-01'
TARGET_PACE_MIN_KM = 5.0 + 40.0/60.0  # 5:40/km in decimal minutes


def load_and_clean(path):
    df = pd.read_csv(path)
    df['Date'] = pd.to_datetime(df['Date'])
    runs = df[df['Type'].str.lower() == 'run'].copy()
    runs['distance_km'] = runs['Distance'].astype(float) / 1000.0
    runs['moving_time_min'] = runs['Moving Time'].astype(float) / 60.0
    runs['pace'] = runs['moving_time_min'] / runs['distance_km']   # min/km decimal
    runs['pace_str'] = runs['pace'].apply(lambda p: f"{int(p)}:{int((p % 1)*60):02d}")
    runs['week_start'] = runs['Date'].dt.to_period('W-MON').apply(lambda r: r.start_time)
    if 'Avg HR' in runs.columns:
        runs['avg_hr'] = pd.to_numeric(runs['Avg HR'], errors='coerce')
    else:
        runs['avg_hr'] = float('nan')
    return runs.sort_values('Date').reset_index(drop=True)


def weekly_aggregates(runs):
    weekly = (
        runs.groupby('week_start')
        .agg(
            total_km=('distance_km', 'sum'),
            avg_pace=('pace', 'mean'),
            avg_hr=('avg_hr', 'mean'),
            n_runs=('id', 'count'),
        )
        .reset_index()
        .sort_values('week_start')
    )
    weekly['week_start_str'] = weekly['week_start'].dt.strftime('%Y-%m-%d')
    weekly['rolling_km_4w'] = weekly['total_km'].rolling(4, min_periods=1).mean()
    weekly['rolling_pace_4w'] = weekly['avg_pace'].rolling(4, min_periods=1).mean()
    weekly['avg_pace_str'] = weekly['avg_pace'].apply(lambda p: f"{int(p)}:{int((p % 1)*60):02d}" if pd.notna(p) else '')
    return weekly


def make_targets(starting_km, weeks=19):
    """Conservative 10 % weekly progression with −15 % step-back every 4th week."""
    prog = []
    cur = starting_km
    for i in range(weeks):
        prog.append(round(cur, 1))
        cur = cur * 1.10
    for i in range(3, weeks, 4):
        prog[i] = round(prog[i] * 0.85, 1)
    return prog

def build_volume_chart(weekly, targets, plan_start):
    """Bar chart: observed weekly km vs planned targets + 4-week rolling average."""
    weeks = len(targets)
    target_dates = pd.date_range(start=plan_start, periods=weeks, freq='W-MON')
    obs_index = pd.to_datetime(weekly['week_start'])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=obs_index, y=weekly['total_km'],
        name='Observed km', marker_color='#3b82f6',
        hovertemplate='%{x|%b %d}<br>%{y:.1f} km<extra>Observed</extra>',
    ))
    fig.add_trace(go.Scatter(
        x=obs_index, y=weekly['rolling_km_4w'],
        mode='lines+markers', name='4-week rolling avg',
        line=dict(color='#f97316', width=2),
        hovertemplate='%{x|%b %d}<br>%{y:.1f} km<extra>4w avg</extra>',
    ))
    fig.add_trace(go.Scatter(
        x=target_dates, y=targets,
        mode='lines+markers', name='Weekly plan target',
        line=dict(color='#22c55e', dash='dash', width=2),
        hovertemplate='%{x|%b %d}<br>%{y:.1f} km<extra>Target</extra>',
    ))
    # marathon date vertical line
    fig.add_vline(x=MARATHON_DATE, line_dash='dot', line_color='#ef4444',
                  annotation_text='Race day', annotation_position='top right')
    fig.update_layout(
        title='Weekly Running Volume — Observed vs Planned',
        xaxis_title='Week (Monday)', yaxis_title='Kilometers',
        template='plotly_white', hovermode='x unified', legend=dict(orientation='h'),
        height=380,
    )
    return fig


def build_pace_chart(weekly, runs):
    """Dual-axis: average session pace trend + individual session pace scatter."""
    fig = make_subplots(specs=[[{'secondary_y': True}]])
    fig.add_trace(go.Scatter(
        x=runs['Date'], y=runs['pace'],
        mode='markers', name='Session pace',
        marker=dict(color='#a78bfa', size=6, opacity=0.7),
        hovertemplate='%{x|%b %d}<br>%{customdata} min/km<extra>Session</extra>',
        customdata=runs['pace_str'],
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=pd.to_datetime(weekly['week_start']), y=weekly['rolling_pace_4w'],
        mode='lines+markers', name='4-week rolling pace',
        line=dict(color='#ec4899', width=2),
        hovertemplate='%{x|%b %d}<br>%{customdata} min/km<extra>4w avg</extra>',
        customdata=weekly['avg_pace_str'],
    ), secondary_y=False)
    # target pace reference line
    fig.add_hline(y=TARGET_PACE_MIN_KM, line_dash='dot', line_color='#22c55e',
                  annotation_text='MP target 5:40', secondary_y=False)
    # invert y-axis so faster pace is higher
    fig.update_yaxes(autorange='reversed', title_text='Pace (min/km)', secondary_y=False)
    fig.update_layout(
        title='Session & Rolling Average Pace',
        xaxis_title='Date', template='plotly_white',
        hovermode='x unified', legend=dict(orientation='h'), height=380,
    )
    return fig


def build_recent_runs_table(runs, n=10):
    """Simple HTML table of the last n sessions."""
    recent = runs.tail(n)[['Date', 'Name', 'distance_km', 'pace_str', 'avg_hr']].copy()
    recent['Date'] = recent['Date'].dt.strftime('%a %b %d')
    recent['distance_km'] = recent['distance_km'].apply(lambda x: f'{x:.2f} km')
    recent['avg_hr'] = recent['avg_hr'].apply(lambda x: f'{x:.0f} bpm' if pd.notna(x) else '—')
    recent.columns = ['Date', 'Name', 'Distance', 'Pace', 'Avg HR']
    rows = ''.join(
        f'<tr>{"".join(f"<td>{v}</td>" for v in row)}</tr>'
        for row in recent.iloc[::-1].itertuples(index=False)
    )
    return f'<table class="table table-sm table-striped table-hover"><thead><tr>{"".join(f"<th>{c}</th>" for c in recent.columns)}</tr></thead><tbody>{rows}</tbody></table>'


def build_dashboard(runs, weekly, targets):
    plan_start = pd.to_datetime(PLAN_START)
    four_week_avg = float(weekly['total_km'].tail(4).mean()) if not weekly.empty else 0.0
    latest_weekly = float(weekly['total_km'].iloc[-1]) if not weekly.empty else 0.0
    longest_run = float(runs['distance_km'].max()) if not runs.empty else 0.0
    last_date = runs['Date'].max().strftime('%b %d, %Y') if not runs.empty else 'N/A'
    total_runs = len(runs)
    current_pace_str = weekly['avg_pace_str'].iloc[-1] if not weekly.empty else '—'

    # race countdown
    days_to_race = (pd.to_datetime(MARATHON_DATE) - pd.Timestamp.today()).days

    vol_chart = pio.to_html(build_volume_chart(weekly, targets, plan_start), full_html=False, include_plotlyjs='cdn')
    pace_chart = pio.to_html(build_pace_chart(weekly, runs), full_html=False, include_plotlyjs=False)
    recent_table = build_recent_runs_table(runs)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Munich Marathon 2026 — Training Dashboard</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {{ background: #f8fafc; font-family: 'Segoe UI', system-ui, sans-serif; }}
    .hero {{ background: linear-gradient(135deg, #1e3a5f 0%, #3b82f6 100%); color: white; padding: 2.5rem 2rem 2rem; }}
    .hero h1 {{ font-size: 1.9rem; font-weight: 700; margin-bottom: .25rem; }}
    .hero .sub {{ opacity: .85; font-size: .95rem; }}
    .stat-card {{ border: none; border-radius: 12px; box-shadow: 0 1px 6px rgba(0,0,0,.08); }}
    .stat-value {{ font-size: 1.8rem; font-weight: 700; color: #1e3a5f; }}
    .stat-label {{ font-size: .78rem; text-transform: uppercase; letter-spacing: .05em; color: #64748b; }}
    .chart-card {{ border: none; border-radius: 12px; box-shadow: 0 1px 6px rgba(0,0,0,.08); }}
    .section-title {{ font-weight: 600; font-size: 1rem; color: #334155; margin-bottom: .75rem; }}
    .countdown {{ font-size: 2.4rem; font-weight: 800; color: #3b82f6; }}
    footer {{ color: #94a3b8; font-size: .8rem; }}
  </style>
</head>
<body>

<div class="hero">
  <div class="container">
    <h1>🏃 Munich Marathon 2026 — Training Dashboard</h1>
    <p class="sub">Last updated: {last_date} &nbsp;·&nbsp; {total_runs} runs logged</p>
  </div>
</div>

<div class="container py-4">

  <!-- KPI row -->
  <div class="row g-3 mb-4">
    <div class="col-6 col-md-2">
      <div class="card stat-card p-3 text-center h-100">
        <div class="countdown">{days_to_race}</div>
        <div class="stat-label">Days to race</div>
      </div>
    </div>
    <div class="col-6 col-md-2">
      <div class="card stat-card p-3 text-center h-100">
        <div class="stat-value">{four_week_avg:.1f}</div>
        <div class="stat-label">km / week (4w avg)</div>
      </div>
    </div>
    <div class="col-6 col-md-2">
      <div class="card stat-card p-3 text-center h-100">
        <div class="stat-value">{latest_weekly:.1f}</div>
        <div class="stat-label">km last week</div>
      </div>
    </div>
    <div class="col-6 col-md-2">
      <div class="card stat-card p-3 text-center h-100">
        <div class="stat-value">{longest_run:.1f}</div>
        <div class="stat-label">km longest run</div>
      </div>
    </div>
    <div class="col-6 col-md-2">
      <div class="card stat-card p-3 text-center h-100">
        <div class="stat-value">{current_pace_str}</div>
        <div class="stat-label">avg pace (last week)</div>
      </div>
    </div>
    <div class="col-6 col-md-2">
      <div class="card stat-card p-3 text-center h-100">
        <div class="stat-value">5:40</div>
        <div class="stat-label">target MP (sub-4h)</div>
      </div>
    </div>
  </div>

  <!-- Volume chart -->
  <div class="card chart-card p-3 mb-4">
    <p class="section-title mb-0">Weekly Volume — Observed vs Planned</p>
    {vol_chart}
  </div>

  <!-- Pace chart -->
  <div class="card chart-card p-3 mb-4">
    <p class="section-title mb-0">Session Pace History</p>
    {pace_chart}
  </div>

  <!-- Recent runs table -->
  <div class="card chart-card p-3 mb-4">
    <p class="section-title">Recent Sessions</p>
    {recent_table}
  </div>

</div>

<footer class="text-center py-3">
  Munich Marathon 2026 · Iker · Auto-generated from Intervals.icu export
</footer>

</body>
</html>
"""
    out_path = OUT.joinpath('index.html')
    out_path.write_text(html, encoding='utf-8')
    print(f'Dashboard written to {out_path}')


if __name__ == '__main__':
    runs = load_and_clean(DATA)
    weekly = weekly_aggregates(runs)
    # Use last 2 weeks as the base to reflect recent improved consistency
    recent_2w_km = runs[runs['Date'] >= runs['Date'].max() - pd.Timedelta(days=13)]['distance_km'].sum()
    start_avg = round(recent_2w_km / 2.0, 1) if recent_2w_km > 0 else 10.0
    targets = make_targets(start_avg, weeks=19)
    build_dashboard(runs, weekly, targets)
