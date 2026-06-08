#!/usr/bin/env python3
"""Generate an interactive dashboard (docs/index.html) from Intervals.icu CSV export.

CSV columns (Intervals.icu export):
  id, Type, Date, Distance (meters), Moving Time (seconds), Name, Avg HR, Norm Power,
  Intensity, Load, FTP, Weight, W'
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
from pathlib import Path
from datetime import date, timedelta

ROOT = Path(__file__).resolve().parents[0]
DATA = ROOT.joinpath('..').joinpath('i600311_activities.csv').resolve()
OUT = ROOT.joinpath('..').joinpath('docs')
OUT.mkdir(parents=True, exist_ok=True)

MARATHON_DATE = date(2026, 10, 11)
PLAN_START = date(2026, 6, 1)
TARGET_PACE_MIN_KM = 5.0 + 40.0 / 60.0  # 5:40/km

# Weekly plan: (week_num, total_km, long_km, quality_description, phase)
WEEKLY_PLAN = [
    (1,  "Jun 1",  32, 14, "Tue: 6×400m intervals · Thu: Easy 8k · Sat: 10k steady",       "Base"),
    (2,  "Jun 8",  35, 16, "Tue: 6km tempo · Thu: Easy 9k · Sat: 10k steady",               "Base"),
    (3,  "Jun 15", 38, 18, "Tue: 5×1k @VO2 · Thu: Easy 10k · Sat: 10k steady",             "Base"),
    (4,  "Jun 22", 30, 12, "Tue: Easy tempo 5k · Thu: Easy 8k · Sat: 10k easy",             "Base ↩ Recovery"),
    (5,  "Jun 29", 40, 20, "Tue: 8k tempo · Thu: Easy 10k · Sat: 10k steady",               "Build"),
    (6,  "Jul 6",  44, 22, "Tue: 6×1k @VO2 · Thu: Easy 11k · Sat: 11k steady",             "Build"),
    (7,  "Jul 13", 48, 24, "Tue: 10k tempo · Thu: Easy 12k · Sat: 12k steady",              "Build"),
    (8,  "Jul 20", 36, 16, "Tue: 5×1k @VO2 · Thu: Easy 9k · Sat: 11k steady",              "Build ↩ Recovery"),
    (9,  "Jul 27", 50, 26, "Tue: 12k progression · Thu: Easy 12k · Sat: 12k steady",        "Build"),
    (10, "Aug 3",  54, 28, "Tue: 6–8×1k @VO2 · Thu: Easy 13k · Sat: 13k steady",           "Build"),
    (11, "Aug 10", 58, 30, "Tue: 10–12k tempo · Thu: Easy 14k · Sat: 14k steady",           "Build"),
    (12, "Aug 17", 42, 18, "Tue: Easy tempo 8k · Thu: Easy 12k · Sat: 12k easy",            "Build ↩ Recovery"),
    (13, "Aug 24", 60, 32, "Tue: 6×2k @MP · Thu: Easy 14k · Sat: 14k with MP segments",    "Specific"),
    (14, "Aug 31", 62, 34, "Tue: MP intervals · Thu: Easy 14k · Sat: Long with final @MP",  "Specific"),
    (15, "Sep 7",  64, 32, "Tue: MP intervals · Thu: Easy 14k · Sat: 16–20k @MP blocks",    "Specific"),
    (16, "Sep 14", 48, 20, "Tue: 8–10k @MP · Thu: Easy 12k · Sat: 16k steady",              "Taper start"),
    (17, "Sep 21", 40, 16, "Tue: Short sharp intervals · Thu: Easy 10k · Sat: MP pickups",  "Taper"),
    (18, "Sep 28", 30, 13, "Tue: Few strides · Thu: Easy 8k · Sat: Easy 9k",                "Taper"),
    (19, "Oct 5",  22,  0, "Mon: Easy 5k · Wed: 3k strides · Thu: Rest · Sun: RACE DAY 🏁", "Race week"),
]

PHASE_COLORS = {
    "Base": "#3b82f6",
    "Base ↩ Recovery": "#93c5fd",
    "Build": "#f97316",
    "Build ↩ Recovery": "#fdba74",
    "Specific": "#8b5cf6",
    "Taper start": "#22c55e",
    "Taper": "#86efac",
    "Race week": "#ef4444",
}


def load_and_clean(path):
    df = pd.read_csv(path)
    df['Date'] = pd.to_datetime(df['Date'])
    runs = df[df['Type'].str.lower() == 'run'].copy()
    runs['distance_km'] = runs['Distance'].astype(float) / 1000.0
    runs['moving_time_min'] = runs['Moving Time'].astype(float) / 60.0
    runs['pace'] = runs['moving_time_min'] / runs['distance_km']
    runs['pace_str'] = runs['pace'].apply(lambda p: f"{int(p)}:{int((p % 1)*60):02d}")
    runs['week_start'] = runs['Date'].dt.to_period('W-MON').apply(lambda r: r.start_time)
    runs['avg_hr'] = pd.to_numeric(runs.get('Avg HR', float('nan')), errors='coerce')
    return runs.sort_values('Date').reset_index(drop=True)


def weekly_aggregates(runs):
    weekly = (
        runs.groupby('week_start')
        .agg(total_km=('distance_km', 'sum'), avg_pace=('pace', 'mean'),
             avg_hr=('avg_hr', 'mean'), n_runs=('id', 'count'))
        .reset_index().sort_values('week_start')
    )
    weekly['week_start_str'] = weekly['week_start'].dt.strftime('%Y-%m-%d')
    weekly['rolling_km_4w'] = weekly['total_km'].rolling(4, min_periods=1).mean()
    weekly['rolling_pace_4w'] = weekly['avg_pace'].rolling(4, min_periods=1).mean()
    weekly['avg_pace_str'] = weekly['avg_pace'].apply(
        lambda p: f"{int(p)}:{int((p % 1)*60):02d}" if pd.notna(p) else '')
    return weekly


def make_targets(starting_km, weeks=19):
    prog = []
    cur = starting_km
    for i in range(weeks):
        prog.append(round(cur, 1))
        cur = cur * 1.10
    for i in range(3, weeks, 4):
        prog[i] = round(prog[i] * 0.85, 1)
    return prog


# ── Charts ──────────────────────────────────────────────────────────────────

def build_volume_chart(weekly, targets, plan_start):
    target_dates = pd.date_range(start=plan_start, periods=len(targets), freq='W-MON')
    obs_index = pd.to_datetime(weekly['week_start'])
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=obs_index, y=weekly['total_km'], name='Observed km',
        marker_color='#3b82f6',
        hovertemplate='<b>%{x|%b %d}</b><br>%{y:.1f} km<extra>Observed</extra>',
    ))
    fig.add_trace(go.Scatter(
        x=obs_index, y=weekly['rolling_km_4w'], mode='lines+markers',
        name='4-week rolling avg', line=dict(color='#f97316', width=2.5),
        hovertemplate='<b>%{x|%b %d}</b><br>%{y:.1f} km<extra>4w avg</extra>',
    ))
    fig.add_trace(go.Scatter(
        x=target_dates, y=targets, mode='lines+markers',
        name='Plan target', line=dict(color='#22c55e', dash='dash', width=2),
        hovertemplate='<b>%{x|%b %d}</b><br>%{y:.1f} km<extra>Target</extra>',
    ))
    fig.add_vline(x=str(MARATHON_DATE), line_dash='dot', line_color='#ef4444',
                  annotation_text='Race day 🏁', annotation_position='top right')
    fig.update_layout(
        title=None, xaxis_title='Week (Monday)', yaxis_title='Kilometers',
        template='plotly_white', hovermode='x unified',
        legend=dict(orientation='h', y=1.1), height=400,
        margin=dict(t=20, b=40),
    )
    return fig


def build_pace_chart(weekly, runs):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=runs['Date'], y=runs['pace'], mode='markers', name='Session pace',
        marker=dict(color='#a78bfa', size=7, opacity=0.75,
                    line=dict(color='white', width=1)),
        hovertemplate='<b>%{x|%b %d}</b><br>%{customdata}<extra>Session</extra>',
        customdata=runs['pace_str'],
    ))
    fig.add_trace(go.Scatter(
        x=pd.to_datetime(weekly['week_start']), y=weekly['rolling_pace_4w'],
        mode='lines+markers', name='4-week rolling avg',
        line=dict(color='#ec4899', width=2.5),
        hovertemplate='<b>%{x|%b %d}</b><br>%{customdata}<extra>4w avg</extra>',
        customdata=weekly['avg_pace_str'],
    ))
    fig.add_hline(y=TARGET_PACE_MIN_KM, line_dash='dot', line_color='#22c55e',
                  annotation_text='Target MP 5:40', annotation_position='bottom right')
    fig.update_yaxes(autorange='reversed', title_text='Pace (min/km)',
                     tickformat='.2f')
    fig.update_layout(
        title=None, xaxis_title='Date', template='plotly_white',
        hovermode='x unified', legend=dict(orientation='h', y=1.1),
        height=400, margin=dict(t=20, b=40),
    )
    return fig


def build_plan_gantt(targets):
    """Gantt-style bar chart: one bar per week coloured by phase."""
    fig = go.Figure()
    today = pd.Timestamp.today().normalize()
    plan_start_ts = pd.Timestamp(PLAN_START)

    for row in WEEKLY_PLAN:
        wnum, wdate_str, total_km, long_km, quality, phase = row
        w_start = plan_start_ts + pd.Timedelta(weeks=wnum - 1)
        w_end = w_start + pd.Timedelta(days=6)
        color = PHASE_COLORS.get(phase, '#94a3b8')
        is_current = w_start <= today <= w_end
        target_km = targets[wnum - 1] if wnum - 1 < len(targets) else total_km
        fig.add_trace(go.Bar(
            x=[target_km],
            y=[f"W{wnum} · {wdate_str}"],
            orientation='h',
            marker_color=color,
            marker_line_color='white' if not is_current else '#1e3a5f',
            marker_line_width=2 if is_current else 0.5,
            opacity=1.0 if is_current else 0.75,
            name=phase,
            showlegend=False,
            hovertemplate=(
                f"<b>Week {wnum} ({wdate_str})</b><br>"
                f"Phase: {phase}<br>"
                f"Target: {target_km:.0f} km<br>"
                f"Long run: {long_km} km<br>"
                f"Sessions: {quality}"
                "<extra></extra>"
            ),
        ))

    # Add legend manually
    seen = set()
    for _, _, _, _, _, phase in WEEKLY_PLAN:
        if phase not in seen:
            seen.add(phase)
            fig.add_trace(go.Bar(
                x=[None], y=[None], orientation='h',
                marker_color=PHASE_COLORS.get(phase, '#94a3b8'),
                name=phase, showlegend=True,
            ))

    fig.update_layout(
        barmode='stack', title=None,
        xaxis_title='Target km / week',
        yaxis=dict(autorange='reversed', tickfont=dict(size=11)),
        template='plotly_white', height=580,
        legend=dict(orientation='h', y=1.05),
        margin=dict(t=10, b=40),
    )
    return fig


# ── HTML helpers ─────────────────────────────────────────────────────────────

def _recent_runs_table(runs, n=10):
    recent = runs.tail(n)[['Date', 'Name', 'distance_km', 'pace_str', 'avg_hr']].copy()
    recent['Date'] = recent['Date'].dt.strftime('%a %b %d')
    recent['distance_km'] = recent['distance_km'].apply(lambda x: f'{x:.2f} km')
    recent['avg_hr'] = recent['avg_hr'].apply(lambda x: f'{x:.0f} bpm' if pd.notna(x) else '—')
    recent.columns = ['Date', 'Name', 'Distance', 'Pace', 'Avg HR']
    rows = ''.join(
        f'<tr>{"".join(f"<td>{v}</td>" for v in row)}</tr>'
        for row in recent.iloc[::-1].itertuples(index=False)
    )
    headers = ''.join(f'<th>{c}</th>' for c in recent.columns)
    return (
        '<div class="table-responsive">'
        f'<table class="table table-sm table-striped table-hover align-middle mb-0">'
        f'<thead class="table-dark"><tr>{headers}</tr></thead>'
        f'<tbody>{rows}</tbody></table></div>'
    )


def _weekly_plan_table(targets):
    today = date.today()
    plan_start_d = PLAN_START
    rows = ''
    for wnum, wdate_str, orig_km, long_km, quality, phase in WEEKLY_PLAN:
        w_start = plan_start_d + timedelta(weeks=wnum - 1)
        w_end = w_start + timedelta(days=6)
        is_current = w_start <= today <= w_end
        is_past = w_end < today
        target_km = targets[wnum - 1] if wnum - 1 < len(targets) else orig_km
        color = PHASE_COLORS.get(phase, '#94a3b8')
        row_class = 'table-primary fw-bold' if is_current else ('text-muted' if is_past else '')
        badge = (
            '<span class="badge bg-primary ms-1">Current</span>' if is_current
            else ('<span class="badge bg-secondary ms-1">Done</span>' if is_past else '')
        )
        rows += (
            f'<tr class="{row_class}">'
            f'<td><span class="badge" style="background:{color}">{phase}</span></td>'
            f'<td>W{wnum} · {wdate_str}{badge}</td>'
            f'<td>{target_km:.0f} km</td>'
            f'<td>{long_km} km</td>'
            f'<td class="text-muted small">{quality}</td>'
            f'</tr>'
        )
    return (
        '<div class="table-responsive">'
        '<table class="table table-sm table-hover align-middle mb-0">'
        '<thead class="table-dark"><tr>'
        '<th>Phase</th><th>Week</th><th>Target</th><th>Long run</th><th>Daily sessions</th>'
        '</tr></thead>'
        f'<tbody>{rows}</tbody></table></div>'
    )


# ── Dashboard assembly ────────────────────────────────────────────────────────

def build_dashboard(runs, weekly, targets):
    today = date.today()
    plan_start_ts = pd.Timestamp(PLAN_START)
    race_ts = pd.Timestamp(MARATHON_DATE)

    days_to_race = (race_ts - pd.Timestamp(today)).days
    weeks_to_race = days_to_race // 7
    current_week_num = ((today - PLAN_START).days // 7) + 1
    current_week_num = max(1, min(current_week_num, 19))

    four_week_avg = float(weekly['total_km'].tail(4).mean()) if not weekly.empty else 0.0
    latest_weekly = float(weekly['total_km'].iloc[-1]) if not weekly.empty else 0.0
    longest_run = float(runs['distance_km'].max()) if not runs.empty else 0.0
    last_date = runs['Date'].max().strftime('%b %d, %Y') if not runs.empty else 'N/A'
    total_runs = len(runs)
    current_pace_str = weekly['avg_pace_str'].iloc[-1] if not weekly.empty else '—'
    current_phase = WEEKLY_PLAN[current_week_num - 1][5] if current_week_num <= 19 else '—'

    # Determine load status for current week
    current_target = targets[current_week_num - 1] if current_week_num - 1 < len(targets) else 0
    load_status = ''
    load_badge = ''
    if latest_weekly < current_target * 0.80:
        load_status = 'Underloaded'
        load_badge = 'bg-warning text-dark'
    elif latest_weekly > current_target * 1.10:
        load_status = 'Overloaded ⚠️'
        load_badge = 'bg-danger'
    else:
        load_status = 'On track ✓'
        load_badge = 'bg-success'

    vol_html = pio.to_html(build_volume_chart(weekly, targets, plan_start_ts),
                           full_html=False, include_plotlyjs='cdn')
    pace_html = pio.to_html(build_pace_chart(weekly, runs),
                            full_html=False, include_plotlyjs=False)
    gantt_html = pio.to_html(build_plan_gantt(targets),
                             full_html=False, include_plotlyjs=False)
    recent_table = _recent_runs_table(runs)
    plan_table = _weekly_plan_table(targets)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Munich Marathon 2026 — Training Dashboard LOL</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
  <style>
    body {{
      background: #0f172a;
      font-family: 'Inter', system-ui, sans-serif;
      color: #e2e8f0;
      min-height: 100vh;
    }}
    /* ── Hero ── */
    .hero {{
      background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 60%, #1d4ed8 100%);
      border-bottom: 1px solid rgba(255,255,255,.08);
      padding: 2.5rem 0 2rem;
      position: relative;
      overflow: hidden;
    }}
    .hero::before {{
      content: '26.2';
      position: absolute; right: -1rem; top: -1rem;
      font-size: 12rem; font-weight: 800; opacity: .04;
      color: white; line-height: 1; pointer-events: none;
    }}
    .hero-title {{ font-size: 2rem; font-weight: 800; letter-spacing: -.02em; }}
    .hero-sub {{ color: #94a3b8; font-size: .9rem; margin-top: .25rem; }}
    /* ── Countdown ── */
    .countdown-block {{
      display: flex; gap: 1rem; align-items: flex-end; flex-wrap: wrap;
      margin-top: 1.5rem;
    }}
    .cdown-item {{ text-align: center; }}
    .cdown-num {{
      font-size: 3rem; font-weight: 800; line-height: 1;
      background: linear-gradient(135deg, #60a5fa, #818cf8);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }}
    .cdown-label {{ font-size: .7rem; text-transform: uppercase; letter-spacing: .08em; color: #64748b; }}
    .cdown-sep {{ font-size: 2rem; color: #334155; margin-bottom: .4rem; }}
    /* ── Phase badge in hero ── */
    .phase-pill {{
      display: inline-block; padding: .3rem .8rem; border-radius: 999px;
      font-size: .8rem; font-weight: 600;
      background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.2);
      color: white;
    }}
    /* ── KPI cards ── */
    .kpi-card {{
      background: #1e293b; border: 1px solid #334155; border-radius: 14px;
      padding: 1rem 1.25rem; height: 100%;
    }}
    .kpi-value {{ font-size: 1.75rem; font-weight: 800; color: #f1f5f9; line-height: 1.1; }}
    .kpi-label {{ font-size: .72rem; text-transform: uppercase; letter-spacing: .07em; color: #64748b; margin-top: .2rem; }}
    .kpi-icon {{ font-size: 1.5rem; float: right; opacity: .4; }}
    /* ── Status badge ── */
    .status-bar {{
      background: #1e293b; border: 1px solid #334155; border-radius: 14px;
      padding: .75rem 1.25rem; display: flex; align-items: center; gap: .75rem;
    }}
    /* ── Nav tabs ── */
    .nav-tabs {{
      border-bottom: 2px solid #1e293b;
      gap: .25rem;
    }}
    .nav-tabs .nav-link {{
      color: #94a3b8; border: none; border-radius: 8px 8px 0 0;
      padding: .65rem 1.25rem; font-weight: 600; font-size: .88rem;
      background: transparent; transition: all .15s;
    }}
    .nav-tabs .nav-link:hover {{ color: #e2e8f0; background: #1e293b; }}
    .nav-tabs .nav-link.active {{
      color: #60a5fa; background: #1e293b;
      border-bottom: 2px solid #3b82f6;
    }}
    /* ── Content cards ── */
    .content-card {{
      background: #1e293b; border: 1px solid #334155; border-radius: 0 14px 14px 14px;
      padding: 1.5rem;
    }}
    .section-heading {{
      font-size: .75rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: .1em; color: #475569; margin-bottom: .75rem;
    }}
    /* ── Table overrides ── */
    .table {{ color: #cbd5e1; --bs-table-striped-bg: rgba(255,255,255,.04); }}
    .table thead.table-dark {{ background: #0f172a; --bs-table-bg: #0f172a; }}
    .table-hover tbody tr:hover {{ background: rgba(255,255,255,.06); color: #f1f5f9; }}
    /* ── Strategy cards ── */
    .strategy-card {{
      background: #0f172a; border: 1px solid #334155; border-radius: 10px;
      padding: 1rem 1.25rem;
    }}
    .strategy-card h6 {{ font-weight: 700; color: #60a5fa; margin-bottom: .5rem; }}
    .strategy-card ul {{ margin: 0; padding-left: 1.25rem; color: #94a3b8; font-size: .88rem; }}
    /* ── Pace legend ── */
    .pace-zone {{ display: flex; align-items: center; gap: .5rem; font-size: .82rem; margin-bottom: .4rem; }}
    .pace-dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}
    /* ── Footer ── */
    footer {{ color: #334155; font-size: .78rem; padding: 1.5rem 0; text-align: center; }}
    /* ── Plotly charts dark override ── */
    .js-plotly-plot .plotly .bg {{ fill: transparent !important; }}
  </style>
</head>
<body>

<!-- HERO -->
<div class="hero">
  <div class="container">
    <div class="row align-items-start">
      <div class="col-md-8">
        <div class="d-flex align-items-center gap-2 mb-1">
          <span style="font-size:1.8rem">🏃</span>
          <h1 class="hero-title mb-0">Munich Marathon 2026</h1>
        </div>
        <p class="hero-sub">Training Dashboard · Iker · Goal: Sub 4:00 · Last sync: {last_date}</p>
        <div class="countdown-block">
          <div class="cdown-item">
            <div class="cdown-num">{days_to_race}</div>
            <div class="cdown-label">Days</div>
          </div>
          <div class="cdown-sep">·</div>
          <div class="cdown-item">
            <div class="cdown-num">{weeks_to_race}</div>
            <div class="cdown-label">Weeks</div>
          </div>
          <div class="cdown-sep">to go</div>
        </div>
      </div>
      <div class="col-md-4 mt-3 mt-md-0 text-md-end">
        <div class="phase-pill mb-2">Week {current_week_num} of 19 — {current_phase}</div><br>
        <span class="badge {load_badge} fs-6 px-3 py-2">{load_status}</span>
        <div class="text-muted small mt-2">{total_runs} runs logged</div>
      </div>
    </div>
  </div>
</div>

<div class="container py-4">

  <!-- KPI ROW -->
  <div class="row g-3 mb-4">
    <div class="col-6 col-md-2">
      <div class="kpi-card">
        <div class="kpi-icon">📅</div>
        <div class="kpi-value">{four_week_avg:.1f}</div>
        <div class="kpi-label">km/week (4w avg)</div>
      </div>
    </div>
    <div class="col-6 col-md-2">
      <div class="kpi-card">
        <div class="kpi-icon">📆</div>
        <div class="kpi-value">{latest_weekly:.1f}</div>
        <div class="kpi-label">km last week</div>
      </div>
    </div>
    <div class="col-6 col-md-2">
      <div class="kpi-card">
        <div class="kpi-icon">📏</div>
        <div class="kpi-value">{longest_run:.1f}</div>
        <div class="kpi-label">km longest run</div>
      </div>
    </div>
    <div class="col-6 col-md-2">
      <div class="kpi-card">
        <div class="kpi-icon">⏱️</div>
        <div class="kpi-value">{current_pace_str}</div>
        <div class="kpi-label">avg pace (last week)</div>
      </div>
    </div>
    <div class="col-6 col-md-2">
      <div class="kpi-card">
        <div class="kpi-icon">🎯</div>
        <div class="kpi-value">5:40</div>
        <div class="kpi-label">target MP</div>
      </div>
    </div>
    <div class="col-6 col-md-2">
      <div class="kpi-card">
        <div class="kpi-icon">🏁</div>
        <div class="kpi-value">Oct 11</div>
        <div class="kpi-label">race day</div>
      </div>
    </div>
  </div>

  <!-- TABS -->
  <ul class="nav nav-tabs" id="mainTabs" role="tablist">
    <li class="nav-item">
      <button class="nav-link active" data-bs-toggle="tab" data-bs-target="#tab-overview">
        📊 Overview
      </button>
    </li>
    <li class="nav-item">
      <button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-plan">
        📋 Training Plan
      </button>
    </li>
    <li class="nav-item">
      <button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-strategy">
        🧠 Race Strategy
      </button>
    </li>
  </ul>

  <!-- TAB: OVERVIEW -->
  <div class="tab-content">
  <div class="tab-pane fade show active content-card" id="tab-overview">

    <p class="section-heading">Weekly Volume — Observed vs Planned</p>
    {vol_html}

    <p class="section-heading mt-4">Session Pace History</p>
    {pace_html}

    <p class="section-heading mt-4">Recent Sessions</p>
    {recent_table}

  </div>

  <!-- TAB: TRAINING PLAN -->
  <div class="tab-pane fade content-card" id="tab-plan">

    <p class="section-heading">19-Week Plan Overview — Weekly targets by phase</p>
    {gantt_html}

    <p class="section-heading mt-4">Full Week-by-Week Schedule</p>
    {plan_table}

  </div>

  <!-- TAB: RACE STRATEGY -->
  <div class="tab-pane fade content-card" id="tab-strategy">

    <div class="row g-3 mb-4">
      <div class="col-md-6">
        <div class="strategy-card">
          <h6>📅 Training Phases</h6>
          <ul>
            <li><strong>Weeks 1–4 · Base:</strong> Build consistency, easy mileage, 1 long run/week.</li>
            <li><strong>Weeks 5–12 · Build:</strong> Introduce tempo, threshold &amp; VO2 intervals. Long run grows.</li>
            <li><strong>Weeks 13–17 · Specific:</strong> Marathon-pace long runs, MP interval blocks.</li>
            <li><strong>Weeks 18–19 · Taper:</strong> Drop volume, keep sharpness, arrive fresh.</li>
          </ul>
        </div>
      </div>
      <div class="col-md-6">
        <div class="strategy-card">
          <h6>📆 Weekly Template (5 runs)</h6>
          <ul>
            <li><strong>Mon:</strong> Rest or easy swim (optional).</li>
            <li><strong>Tue:</strong> Quality session — intervals or hill repeats.</li>
            <li><strong>Wed:</strong> Easy recovery run (+ strength 30 min).</li>
            <li><strong>Thu:</strong> Tempo or marathon-pace run.</li>
            <li><strong>Fri:</strong> Easy run or rest.</li>
            <li><strong>Sat:</strong> Medium-long steady run.</li>
            <li><strong>Sun:</strong> Long run (progressive; MP segments from W13).</li>
          </ul>
        </div>
      </div>
    </div>

    <div class="row g-3 mb-4">
      <div class="col-md-6">
        <div class="strategy-card">
          <h6>⏱️ Training Pace Zones</h6>
          <div class="pace-zone"><span class="pace-dot" style="background:#22c55e"></span><span><strong>Easy / Recovery</strong> — 6:00–6:40 min/km</span></div>
          <div class="pace-zone"><span class="pace-dot" style="background:#3b82f6"></span><span><strong>Long run</strong> — 5:50–6:20 min/km</span></div>
          <div class="pace-zone"><span class="pace-dot" style="background:#f97316"></span><span><strong>Marathon Pace (MP)</strong> — ~5:40 min/km</span></div>
          <div class="pace-zone"><span class="pace-dot" style="background:#f43f5e"></span><span><strong>Tempo / Threshold</strong> — 4:50–5:20 min/km</span></div>
          <div class="pace-zone"><span class="pace-dot" style="background:#8b5cf6"></span><span><strong>VO2max intervals</strong> — 4:00–4:20 min/km</span></div>
          <p class="small text-muted mt-2">Keep ≥ 80 % of weekly km at easy effort.</p>
        </div>
      </div>
      <div class="col-md-6">
        <div class="strategy-card">
          <h6>🏁 Race Day Strategy</h6>
          <ul>
            <li><strong>Target:</strong> Sub 4:00 (avg 5:40 min/km).</li>
            <li><strong>Split strategy:</strong> Negative split — first half slightly conservative (~2:02), second half push (~1:58).</li>
            <li><strong>First 5k:</strong> Resist the crowd, run by feel not GPS.</li>
            <li><strong>Fuel:</strong> Gel every 30–40 min from km 10 onward.</li>
            <li><strong>Carb load:</strong> 48 h pre-race. Sleep well 2 nights before.</li>
            <li><strong>Warm-up:</strong> 10 min easy jog + drills, 30 min before gun.</li>
          </ul>
        </div>
      </div>
    </div>

    <div class="row g-3">
      <div class="col-md-6">
        <div class="strategy-card">
          <h6>⚡ Key Session Types</h6>
          <ul>
            <li><strong>VO2 intervals:</strong> 6×1k or 5×1200m at 3–5k effort, 2–3 min recovery.</li>
            <li><strong>Tempo / Threshold:</strong> 20–40 min continuous at comfortably hard pace.</li>
            <li><strong>MP runs:</strong> 8–16k blocks at target 5:40 pace.</li>
            <li><strong>Long run:</strong> From W13 include MP segments (final 8–16k at MP).</li>
          </ul>
        </div>
      </div>
      <div class="col-md-6">
        <div class="strategy-card">
          <h6>🛡️ Injury Prevention</h6>
          <ul>
            <li>Never increase weekly km &gt; 10 % in one step.</li>
            <li>Step-back week every 4th week (−15 % volume).</li>
            <li>2×/week strength: glutes, core, single-leg stability.</li>
            <li>If resting HR is elevated or legs feel heavy → swap quality for easy miles.</li>
            <li>Swim as low-impact cross-training when legs need a break.</li>
          </ul>
        </div>
      </div>
    </div>

  </div>
  </div><!-- /tab-content -->

</div><!-- /container -->

<footer>Munich Marathon 2026 · Iker · Auto-generated from Intervals.icu export · {today.strftime('%b %d, %Y')}</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
    out_path = OUT.joinpath('index.html')
    out_path.write_text(html, encoding='utf-8')
    print(f'Dashboard written to {out_path}')


if __name__ == '__main__':
    runs = load_and_clean(DATA)
    weekly = weekly_aggregates(runs)
    recent_2w_km = runs[runs['Date'] >= runs['Date'].max() - pd.Timedelta(days=13)]['distance_km'].sum()
    start_avg = round(recent_2w_km / 2.0, 1) if recent_2w_km > 0 else 10.0
    targets = make_targets(start_avg, weeks=19)
    build_dashboard(runs, weekly, targets)
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
