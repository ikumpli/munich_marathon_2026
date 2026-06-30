#!/usr/bin/env python3
"""Generate an interactive dashboard from Intervals.icu CSV export. Siuuu!

CSV columns (Intervals.icu export):
  id, Type, Date, Distance (meters), Moving Time (seconds), Name, Avg HR, Norm Power,
  Intensity, Load, FTP, Weight, W'
"""
import json
import pandas as pd
from pathlib import Path
from datetime import date, timedelta

ROOT = Path(__file__).resolve().parents[0]
DATA = ROOT.joinpath('..').joinpath('i600311_activities.csv').resolve()
OUT = ROOT.joinpath('..').joinpath('docs')
OUT.mkdir(parents=True, exist_ok=True)
PLAN_JSON = ROOT.joinpath('..').joinpath('plan.json').resolve()

MARATHON_DATE = date(2026, 10, 11)
PLAN_START = date(2026, 6, 8)
TARGET_PACE_MIN_KM = 5.0 + 40.0 / 60.0  # 5:40/km

# Weekly plan: (week_num, date_label, orig_km, long_km, quality_description, phase)
# quality string encodes all 7 days: "Mon: ... · Tue: ... · Wed: ... · Thu: ... · Fri: ... · Sat: ... · Sun: ..."
WEEKLY_PLAN = [
    (1,  "Jun 8",  30, 14, "Mon: Rest or swim · Tue: 6×400m (3 steady ~4:50/km + 3 progressive↗, 2min rest) · Wed: Easy 6k @6:10–6:30/km · Thu: Easy 7k @6:10–6:30/km · Fri: Rest · Sat: 9k steady @5:50–6:10/km · Sun: Long 14k @6:10–6:30/km",   "Base"),
    (2,  "Jun 15", 33, 16, "Mon: Rest or swim · Tue: 6×400m (3 steady ~4:45/km + 3 progressive↗, 2min rest) · Wed: Easy 6k @6:10–6:30/km · Thu: Easy 8k @6:10–6:30/km · Fri: Rest · Sat: 10k steady @5:50–6:10/km · Sun: Long 16k @6:10–6:30/km",  "Base"),
    (3,  "Jun 22", 28, 12, "Mon: Rest or swim · Tue: 4×400m easy strides — light recovery · Wed: Easy 5k @6:20–6:40/km · Thu: Easy 6k @6:20–6:40/km · Fri: Rest · Sat: 8k easy @6:10–6:30/km · Sun: Long 12k @6:20–6:40/km",                       "Base ↩ Recovery"),
    (4,  "Jun 29", 26,  0, "Mon: Rest or swim · Tue: Easy 6k @6:20–6:40/km — no strides, save legs · Wed: Easy 8k @6:10–6:30/km (moderate, get it done early) · Thu: Easy 4k @6:20–6:40/km · Fri: Rest · Sat: Easy 3k shakeout + 4×100m light strides · Sun: 🏁 10k RACE @~4:25/km — go get it!",  "Base"),
    (5,  "Jul 6",  30, 16, "Mon: Rest or swim · Tue: 6×400m (3 steady ~4:50/km + 3 progressive↗, 2min rest) · Wed: Easy 6k @6:10–6:30/km · Thu: Easy 7k @6:10–6:30/km · Fri: Rest · Sat: 8k steady @5:50–6:10/km · Sun: Long 16k @6:10–6:30/km",          "Base"),
    (6,  "Jul 13", 33, 18, "Mon: Rest or swim · Tue: 6×400m (3 steady ~4:45/km + 3 progressive↗, 2min rest) · Wed: Easy 6k @6:10–6:30/km · Thu: Easy 8k @6:10–6:30/km · Fri: Rest · Sat: 10k steady @5:50–6:10/km · Sun: Long 18k @6:10–6:30/km",         "Base"),
    (7,  "Jul 20", 28, 12, "Mon: Rest or swim · Tue: 4×400m easy strides — light recovery · Wed: Easy 5k @6:20–6:40/km · Thu: Easy 6k @6:20–6:40/km · Fri: Rest · Sat: 8k easy @6:10–6:30/km · Sun: Long 12k @6:20–6:40/km",                              "Base ↩ Recovery"),
    (8,  "Jul 27", 42, 20, "Mon: Rest or swim · Tue: 8k tempo @4:50–5:20/km · Wed: Easy 7k @6:10–6:30/km · Thu: Easy 10k @6:10–6:30/km · Fri: Rest · Sat: 10k steady @5:50–6:10/km · Sun: Long 20k @6:00–6:20/km",                                        "Build"),
    (9,  "Aug 3",  46, 22, "Mon: Rest or swim · Tue: 6×1k @VO2 (4:10–4:20/km, 90s rest) · Wed: Easy 7k @6:10–6:30/km · Thu: Easy 11k @6:10–6:30/km · Fri: Rest · Sat: 11k steady @5:50–6:10/km · Sun: Long 22k @6:00–6:20/km",                           "Build"),
    (10, "Aug 10", 50, 24, "Mon: Rest or swim · Tue: 10k tempo @4:50–5:20/km · Wed: Easy 7k @6:10–6:30/km · Thu: Easy 12k @6:10–6:30/km · Fri: Rest · Sat: 12k steady @5:50–6:10/km · Sun: Long 24k @5:55–6:15/km",                                       "Build"),
    (11, "Aug 17", 40, 18, "Mon: Rest or swim · Tue: 5×1k @VO2 easy (4:15–4:25/km) · Wed: Easy 6k @6:10–6:30/km · Thu: Easy 10k @6:10–6:30/km · Fri: Rest · Sat: 10k steady @5:50–6:10/km · Sun: Long 18k @6:10–6:20/km",                                "Build ↩ Recovery"),
    (12, "Aug 24", 54, 28, "Mon: Rest or swim · Tue: 6×2k @MP (5:40/km, 2min rest) · Wed: Easy 7k @6:10–6:30/km · Thu: Easy 12k @6:10–6:30/km · Fri: Rest · Sat: 13k incl 6k @5:40/km · Sun: Long 28k (final 6k @5:40/km)",                              "Specific"),
    (13, "Aug 31", 56, 30, "Mon: Rest or swim · Tue: 8×1k @MP (5:40/km, 90s rest) · Wed: Easy 7k @6:10–6:30/km · Thu: Easy 13k @6:10–6:30/km · Fri: Rest · Sat: 13k incl 8k @5:40/km · Sun: Long 30k (final 8k @5:40/km)",                               "Specific"),
    (14, "Sep 7",  56, 30, "Mon: Rest or swim · Tue: 4×2k @MP (5:40/km, 2min rest) · Wed: Easy 7k @6:10–6:30/km · Thu: Easy 12k @6:10–6:30/km · Fri: Rest · Sat: 13k incl 10k @5:40/km · Sun: Long 30k (14–16k @5:40/km)",                               "Specific"),
    (15, "Sep 14", 46, 22, "Mon: Rest or swim · Tue: 6×1k @MP easy (5:40/km, 90s rest) · Wed: Easy 6k @6:10–6:30/km · Thu: Easy 11k @6:10–6:30/km · Fri: Rest · Sat: 12k incl short MP effort · Sun: Long 22k (6k @5:40/km)",                            "Specific ↩ Recovery"),
    (16, "Sep 21", 40, 16, "Mon: Rest or swim · Tue: 8×200m fast strides (3:50–4:00/km, 60s rest) · Wed: Easy 6k @6:10–6:30/km · Thu: Easy 10k @6:10–6:30/km · Fri: Rest · Sat: 10k incl 3×2k @5:40/km · Sun: Long 16k @6:00–6:20/km",            "Taper start"),
    (17, "Sep 28", 28, 12, "Mon: Rest or swim · Tue: 6×100m easy strides · Wed: Easy 5k @6:20–6:40/km · Thu: Easy 7k @6:20–6:40/km · Fri: Rest · Sat: Easy 7k @6:20–6:40/km · Sun: Long 12k @6:10–6:30/km",                                       "Taper"),
    (18, "Oct 5",  20,  0, "Mon: Easy 4k @6:20–6:40/km · Tue: Rest · Wed: 3k easy strides · Thu: Rest · Fri: Rest · Sat: Rest · Sun: RACE DAY 🏁 — 5:40/km avg, negative split",                                                                    "Race week"),
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


def _load_plan():
    """Load plan.json if it exists, return None otherwise."""
    if PLAN_JSON.exists():
        with open(PLAN_JSON) as f:
            return json.load(f)
    return None


def load_and_clean(path):
    df = pd.read_csv(path)
    df['Date'] = pd.to_datetime(df['Date'])
    runs = df[df['Type'].str.lower() == 'run'].copy()
    runs['distance_km'] = runs['Distance'].astype(float) / 1000.0
    runs['moving_time_min'] = runs['Moving Time'].astype(float) / 60.0
    runs = runs[runs['distance_km'] > 0].copy()
    runs['pace'] = runs['moving_time_min'] / runs['distance_km']
    runs = runs[runs['pace'].apply(lambda p: pd.notna(p) and p != float('inf'))].copy()
    runs['pace_str'] = runs['pace'].apply(lambda p: f"{int(p)}:{int((p % 1)*60):02d}")
    runs['week_start'] = runs['Date'].dt.normalize() - pd.to_timedelta(runs['Date'].dt.weekday, unit='D')
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


def make_targets():
    """Extract planned weekly km directly from WEEKLY_PLAN — no computed projection."""
    return [row[2] for row in WEEKLY_PLAN]


def _esc(s):
    """Minimal HTML-attribute escaping for tooltip text."""
    return (str(s).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def _fmt_pace_clock(p):
    return f"{int(p)}:{int((p % 1) * 60):02d}"

# ── Charts ──────────────────────────────────────────────────────────────────

def build_volume_chart(weekly, targets, plan_start):
    """Native SVG: observed weekly km bars + plan-target line + 4-week rolling avg."""
    n = len(targets)
    plan_mondays = [pd.Timestamp(plan_start).normalize() + pd.Timedelta(weeks=i) for i in range(n)]
    obs_map, roll_map = {}, {}
    for m, k, r in zip(pd.to_datetime(weekly['week_start']), weekly['total_km'], weekly['rolling_km_4w']):
        key = pd.Timestamp(m).normalize()
        obs_map[key] = float(k)
        roll_map[key] = float(r) if pd.notna(r) else None
    observed = [obs_map.get(m) for m in plan_mondays]
    rolling = [roll_map.get(m) for m in plan_mondays]
    today = pd.Timestamp(date.today())

    W, H = 920, 360
    pad_l, pad_r, pad_t, pad_b = 38, 14, 18, 48
    plot_w, plot_h = W - pad_l - pad_r, H - pad_t - pad_b
    band = plot_w / n
    bar_w = band * 0.5

    vmax = max(list(targets) + [v for v in observed if v]) * 1.12
    tick_step = 20 if vmax > 40 else 10
    y_top = (int(vmax // tick_step) + 1) * tick_step

    def yv(v):
        return pad_t + plot_h * (1 - v / y_top)

    def xc(i):
        return pad_l + band * i + band / 2

    def is_cur(m):
        return m <= today <= (m + pd.Timedelta(days=6))

    p = [f'<svg viewBox="0 0 {W} {H}" class="chart-svg" preserveAspectRatio="xMidYMid meet" role="img">']

    t = 0
    while t <= y_top + 0.1:
        y = yv(t)
        p.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{W - pad_r}" y2="{y:.1f}" stroke="#1e293b"/>')
        p.append(f'<text x="{pad_l - 6}" y="{y + 3:.1f}" fill="#64748b" font-size="10" text-anchor="end">{int(t)}</text>')
        t += tick_step

    for i, m in enumerate(plan_mondays):
        if is_cur(m):
            x0 = pad_l + band * i
            p.append(f'<rect x="{x0:.1f}" y="{pad_t}" width="{band:.1f}" height="{plot_h}" fill="#3b82f6" opacity="0.08"/>')

    for i, v in enumerate(observed):
        if not v:
            continue
        x = xc(i) - bar_w / 2
        y = yv(v)
        h = (pad_t + plot_h) - y
        tip = _esc(f"Week {i + 1} ({WEEKLY_PLAN[i][1]}) — {v:.1f} km run")
        p.append(f'<rect class="vbar" x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="2" fill="#3b82f6"><title>{tip}</title></rect>')

    tpts = " ".join(f"{xc(i):.1f},{yv(targets[i]):.1f}" for i in range(n))
    p.append(f'<polyline points="{tpts}" fill="none" stroke="#22c55e" stroke-width="2" stroke-dasharray="5 4"/>')
    for i in range(n):
        cx, cy = xc(i), yv(targets[i])
        tip = _esc(f"Week {i + 1} ({WEEKLY_PLAN[i][1]}) — target {targets[i]:.0f} km")
        p.append(f'<rect class="vbar" x="{cx - 3:.1f}" y="{cy - 3:.1f}" width="6" height="6" transform="rotate(45 {cx:.1f} {cy:.1f})" fill="#22c55e"><title>{tip}</title></rect>')

    rpts = [(xc(i), yv(rolling[i])) for i in range(n) if rolling[i]]
    if len(rpts) >= 2:
        rp = " ".join(f"{x:.1f},{y:.1f}" for x, y in rpts)
        p.append(f'<polyline points="{rp}" fill="none" stroke="#f97316" stroke-width="2"/>')
    for x, y in rpts:
        p.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#f97316"/>')

    rx = xc(n - 1)
    p.append(f'<line x1="{rx:.1f}" y1="{pad_t}" x2="{rx:.1f}" y2="{pad_t + plot_h}" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="2 3"/>')
    p.append(f'<text x="{rx:.1f}" y="{pad_t - 5}" fill="#ef4444" font-size="11" text-anchor="end">\U0001F3C1</text>')

    for i, m in enumerate(plan_mondays):
        col = "#94a3b8" if is_cur(m) else "#475569"
        p.append(f'<text x="{xc(i):.1f}" y="{H - pad_b + 16}" fill="{col}" font-size="9" text-anchor="middle">W{i + 1}</text>')
    for i in range(0, n, 3):
        p.append(f'<text x="{xc(i):.1f}" y="{H - pad_b + 30}" fill="#64748b" font-size="9" text-anchor="middle">{WEEKLY_PLAN[i][1]}</text>')

    p.append('</svg>')
    legend = (
        '<div class="chart-legend">'
        '<span class="ci"><span class="sw" style="background:#3b82f6"></span>Observed km</span>'
        '<span class="ci"><span class="sw" style="background:#f97316"></span>4-week avg</span>'
        '<span class="ci"><span class="sw" style="background:#22c55e"></span>Plan target</span>'
        '</div>'
    )
    return '<div class="chart-wrap">' + "".join(p) + legend + '</div>'


def build_pace_chart(weekly, runs):
    """Native SVG: per-session pace scatter + 4-week rolling avg + target MP line."""
    runs_sorted = runs.sort_values('Date')
    dates = list(pd.to_datetime(runs_sorted['Date']))
    paces = [float(p) for p in runs_sorted['pace']]
    pstrs = list(runs_sorted['pace_str'])
    names = list(runs_sorted['Name']) if 'Name' in runs_sorted else [''] * len(dates)
    if not dates:
        return '<div class="text-muted small">No sessions yet.</div>'

    dmin, dmax = min(dates), max(dates)
    span_days = max((dmax - dmin).days, 1)
    target = TARGET_PACE_MIN_KM
    pall = paces + [target]
    pmin, pmax = min(pall), max(pall)
    pspan = max(pmax - pmin, 0.2)
    pmin_d = pmin - pspan * 0.12
    pmax_d = pmax + pspan * 0.12

    W, H = 920, 340
    pad_l, pad_r, pad_t, pad_b = 46, 14, 18, 40
    plot_w, plot_h = W - pad_l - pad_r, H - pad_t - pad_b

    def xd(d):
        return pad_l + plot_w * ((pd.Timestamp(d) - dmin).days / span_days)

    def yp(v):
        return pad_t + plot_h * ((v - pmin_d) / (pmax_d - pmin_d))

    p = [f'<svg viewBox="0 0 {W} {H}" class="chart-svg" preserveAspectRatio="xMidYMid meet" role="img">']

    nticks = 4
    for k in range(nticks + 1):
        v = pmin_d + (pmax_d - pmin_d) * k / nticks
        y = yp(v)
        p.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{W - pad_r}" y2="{y:.1f}" stroke="#1e293b"/>')
        p.append(f'<text x="{pad_l - 6}" y="{y + 3:.1f}" fill="#64748b" font-size="10" text-anchor="end">{_fmt_pace_clock(v)}</text>')

    for mdt in pd.date_range(dmin.normalize(), dmax.normalize(), freq='MS'):
        if mdt < dmin:
            continue
        x = xd(mdt)
        p.append(f'<line x1="{x:.1f}" y1="{pad_t}" x2="{x:.1f}" y2="{pad_t + plot_h}" stroke="#1e293b"/>')
        p.append(f'<text x="{x:.1f}" y="{H - pad_b + 16}" fill="#64748b" font-size="10" text-anchor="middle">{mdt.strftime("%b")}</text>')

    ty = yp(target)
    p.append(f'<line x1="{pad_l}" y1="{ty:.1f}" x2="{W - pad_r}" y2="{ty:.1f}" stroke="#22c55e" stroke-width="1.5" stroke-dasharray="5 4"/>')
    p.append(f'<text x="{W - pad_r}" y="{ty - 5:.1f}" fill="#22c55e" font-size="10" text-anchor="end">Target MP 5:40</text>')

    wk_dates = list(pd.to_datetime(weekly['week_start']))
    wk_pace = [float(v) if pd.notna(v) else None for v in weekly['rolling_pace_4w']]
    rpts = [(xd(d), yp(v)) for d, v in zip(wk_dates, wk_pace) if v and dmin <= d <= dmax]
    if len(rpts) >= 2:
        rp = " ".join(f"{x:.1f},{y:.1f}" for x, y in rpts)
        p.append(f'<polyline points="{rp}" fill="none" stroke="#ec4899" stroke-width="2"/>')

    for d, pc, ps, nm in zip(dates, paces, pstrs, names):
        x, y = xd(d), yp(pc)
        tip = _esc(f"{pd.Timestamp(d).strftime('%a %b %d')} \u00b7 {ps}/km \u2014 {nm}")
        p.append(f'<circle class="pdot" cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#818cf8" stroke="#0f172a" stroke-width="1.2"><title>{tip}</title></circle>')

    p.append('</svg>')
    legend = (
        '<div class="chart-legend">'
        '<span class="ci"><span class="sw" style="background:#818cf8;width:10px;height:10px;border-radius:50%"></span>Session pace</span>'
        '<span class="ci"><span class="sw" style="background:#ec4899"></span>4-week avg</span>'
        '<span class="ci"><span class="sw" style="background:#22c55e"></span>Target MP</span>'
        '</div>'
    )
    return '<div class="chart-wrap">' + "".join(p) + legend + '</div>'


def build_plan_gantt(targets):
    """Native HTML/CSS: one horizontal bar per week, coloured by phase."""
    today = date.today()
    max_t = max(targets) if targets else 1

    seen = []
    for row in WEEKLY_PLAN:
        if row[5] not in seen:
            seen.append(row[5])
    legend_chips = "".join(
        f'<span class="ci"><span class="sw" style="background:{PHASE_COLORS.get(ph, "#94a3b8")};width:12px;height:12px;border-radius:3px"></span>{_esc(ph)}</span>'
        for ph in seen
    )

    rows = []
    for wnum, wdate_str, total_km, long_km, quality, phase in WEEKLY_PLAN:
        w_start = PLAN_START + timedelta(weeks=wnum - 1)
        w_end = w_start + timedelta(days=6)
        is_current = w_start <= today <= w_end
        is_past = w_end < today
        tk = targets[wnum - 1] if wnum - 1 < len(targets) else total_km
        color = PHASE_COLORS.get(phase, '#94a3b8')
        pct = max(tk / max_t * 100, 2)
        opacity = '1' if is_current else ('0.5' if is_past else '0.92')
        ring = 'box-shadow:0 0 0 2px #3b82f6;' if is_current else ''
        tip = _esc(f"Week {wnum} ({wdate_str}) \u00b7 {phase} \u00b7 target {tk:.0f} km \u00b7 long {long_km} km \u2014 {quality}")
        rows.append(
            f'<div class="gbar" title="{tip}" style="display:flex;align-items:center;gap:.6rem;margin-bottom:.34rem;opacity:{opacity}">'
            f'<div style="flex:0 0 86px;font-size:.7rem;color:#94a3b8">W{wnum}<span style="color:#475569"> \u00b7 {wdate_str}</span></div>'
            f'<div style="flex:1;background:#0f172a;border-radius:6px;height:22px;position:relative;{ring}">'
            f'<div class="gbar-fill" style="width:{pct:.1f}%;height:100%;background:{color};border-radius:6px"></div>'
            f'<span style="position:absolute;right:8px;top:0;line-height:22px;font-size:.68rem;color:#e2e8f0">{tk:.0f} km</span>'
            f'</div>'
            f'</div>'
        )

    return (
        '<div class="chart-wrap">'
        f'<div class="chart-legend" style="margin:0 0 .8rem">{legend_chips}</div>'
        + "".join(rows) +
        '</div>'
    )


# ── HTML helpers ─────────────────────────────────────────────────────────────

def _week_calendar_html(week_entry, targets, today, plan_days=None):
    """7-day calendar card for the current training week."""
    wnum, wdate_str, orig_km, long_km, quality, phase = week_entry

    # Parse explicit day sessions from quality string: "Tue: ... · Thu: ... · Sat: ..."
    parsed = {}
    for part in quality.split(' · '):
        if ': ' in part:
            day_key, desc = part.split(': ', 1)
            parsed[day_key.strip()] = desc.strip()

    target_km_val = targets[wnum - 1] if wnum - 1 < len(targets) else orig_km

    days_info = [
        ('Mon', parsed.get('Mon', 'Rest or easy swim'),              '💤'),
        ('Tue', parsed.get('Tue', 'Quality session'),                '⚡'),
        ('Wed', parsed.get('Wed', 'Easy recovery run @6:10–6:30/km'),'🏃'),
        ('Thu', parsed.get('Thu', 'Easy run @6:10–6:30/km'),         '🏃'),
        ('Fri', parsed.get('Fri', 'Rest'),                           '💤'),
        ('Sat', parsed.get('Sat', 'Steady run @5:50–6:10/km'),       '🏃'),
        ('Sun', parsed.get('Sun', f'Long run {long_km}k @6:10–6:20/km'), '📏'),
    ]

    week_monday = today - timedelta(days=today.weekday())
    phase_color = PHASE_COLORS.get(phase, '#94a3b8')
    plan_day_map = {d['day']: d for d in plan_days} if plan_days else {}
    _icon_map = {'rest': '💤', 'easy': '🏃', 'quality': '⚡', 'long': '📏', 'race': '🏁'}

    cards = ''
    for i, (short, session, icon) in enumerate(days_info):
        day_date = week_monday + timedelta(days=i)

        # Override with live plan.json data when available
        actual_km = None
        session_type_str = None
        if short in plan_day_map:
            day_entry = plan_day_map[short]
            session = day_entry.get('planned', session)
            icon = _icon_map.get(day_entry.get('session_type', 'easy'), icon)
            actual_km = day_entry.get('actual_km')
            session_type_str = day_entry.get('session_type')

        is_today = (day_date == today)
        is_past = day_date < today

        if is_today:
            card_bg, card_border = '#1e3a5f', '2px solid #3b82f6'
            day_color, date_color, text_color, opacity = '#60a5fa', '#93c5fd', '#f1f5f9', '1'
        elif is_past:
            card_bg, card_border = '#0a0f1a', '1px solid #1e293b'
            day_color, date_color, text_color, opacity = '#334155', '#334155', '#475569', '0.55'
        else:
            card_bg, card_border = '#0f172a', '1px solid #334155'
            day_color, date_color, text_color, opacity = '#64748b', '#475569', '#94a3b8', '1'

        today_dot = (
            '<span style="display:inline-block;width:7px;height:7px;border-radius:50%;'
            'background:#3b82f6;margin-left:5px;vertical-align:middle"></span>'
        ) if is_today else ''

        # Actual metrics block
        actual_html = ''
        if actual_km is not None and actual_km > 0:
            pace_val = plan_day_map[short].get('actual_pace_min_km') if short in plan_day_map else None
            hr_val = plan_day_map[short].get('actual_hr') if short in plan_day_map else None
            act_name = plan_day_map[short].get('actual_name') if short in plan_day_map else None
            pace_str = f"{int(pace_val)}:{int((pace_val % 1)*60):02d}/km" if pace_val else ''
            hr_str = f'{int(hr_val)} bpm' if hr_val else ''
            metrics = ' · '.join(filter(None, [f'{actual_km:.1f} km', pace_str, hr_str]))
            name_html = (
                f'<div style="font-size:.6rem;color:#64748b;margin-top:.1rem">{act_name}</div>'
            ) if act_name else ''
            actual_html = (
                f'<div style="margin-top:.45rem;padding:.35rem .4rem;border-radius:6px;'
                f'background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.25)">'
                f'<div style="font-size:.6rem;font-weight:700;color:#22c55e;'
                f'letter-spacing:.04em;margin-bottom:.15rem">✓ DONE</div>'
                f'<div style="font-size:.68rem;color:#86efac;line-height:1.5">{metrics}</div>'
                f'{name_html}'
                f'</div>'
            )
            # If a quality session was planned but activity name has no quality keywords, warn
            planned_orig = plan_day_map[short].get('planned', '') if short in plan_day_map else ''
            if planned_orig and session_type_str == 'quality':
                _quality_kws = ('interval', 'intervals', 'tempo', 'mp run', 'mp pace')
                name_lower = (act_name or '').lower()
                if not any(kw in name_lower for kw in _quality_kws):
                    actual_html += (
                        f'<div style="font-size:.6rem;color:#f97316;margin-top:.2rem">'
                        f'⚠ Planned: {planned_orig[:45]}{"…" if len(planned_orig)>45 else ""}</div>'
                    )
        elif is_past and session_type_str not in ('rest', None):
            actual_html = (
                '<div style="margin-top:.45rem;padding:.3rem .4rem;border-radius:6px;'
                'background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.2)">'
                '<div style="font-size:.6rem;font-weight:700;color:#ef4444">✗ NOT DONE</div>'
                '</div>'
            )

        cards += (
            f'<div style="flex:1;min-width:110px;border-radius:10px;padding:.75rem .65rem;'
            f'background:{card_bg};border:{card_border};opacity:{opacity}">'
            f'<div style="font-size:.68rem;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:.07em;color:{day_color};margin-bottom:.15rem">{short}{today_dot}</div>'
            f'<div style="font-size:.65rem;color:{date_color};margin-bottom:.5rem">{day_date.strftime("%b %d")}</div>'
            f'<div style="font-size:1rem;margin-bottom:.3rem">{icon}</div>'
            f'<div style="font-size:.75rem;color:{text_color};line-height:1.4">{session}</div>'
            f'{actual_html}'
            f'</div>'
        )

    return (
        f'<div style="background:#1e293b;border:1px solid #334155;border-radius:14px;'
        f'padding:1.25rem;margin-bottom:1.5rem">'
        f'<div style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;'
        f'color:#475569;margin-bottom:.85rem">'
        f'Week {wnum} &nbsp;·&nbsp; {wdate_str} &nbsp;·&nbsp; '
        f'<span style="color:{phase_color}">{phase}</span> &nbsp;·&nbsp; '
        f'Target: <span style="color:#f1f5f9">{target_km_val:.0f} km</span>'
        f'</div>'
        f'<div style="display:flex;gap:.5rem;flex-wrap:wrap">{cards}</div>'
        f'</div>'
    )


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
    current_week_num = max(1, min(current_week_num, 18))

    four_week_avg = float(weekly['total_km'].tail(4).mean()) if not weekly.empty else 0.0
    # Look up weeks by their Monday date (robust to an empty current week)
    this_week_monday = pd.Timestamp(today - timedelta(days=today.weekday()))
    last_week_monday = this_week_monday - pd.Timedelta(weeks=1)
    weekly_by_monday = weekly.set_index('week_start')

    def _week_metric(monday, col, default):
        return weekly_by_monday.loc[monday, col] if monday in weekly_by_monday.index else default

    this_week_km = float(_week_metric(this_week_monday, 'total_km', 0.0))
    last_week_km = float(_week_metric(last_week_monday, 'total_km', 0.0))
    last_week_pace_str = _week_metric(last_week_monday, 'avg_pace_str', '—') or '—'
    longest_run = float(runs['distance_km'].max()) if not runs.empty else 0.0
    last_date = runs['Date'].max().strftime('%b %d, %Y') if not runs.empty else 'N/A'
    total_runs = len(runs)
    current_pace_str = last_week_pace_str
    current_phase = WEEKLY_PLAN[current_week_num - 1][5] if current_week_num <= 18 else '—'
    current_week_entry = WEEKLY_PLAN[current_week_num - 1]
    _plan_data = _load_plan()
    _plan_days = None
    if _plan_data:
        for _wk in _plan_data.get('weeks', []):
            if _wk['week'] == current_week_num:
                _plan_days = _wk['days']
                break
    calendar_html = _week_calendar_html(current_week_entry, targets, today, plan_days=_plan_days)

    # Load status reflects the last COMPLETED week vs its plan target
    # (an in-progress current week would always read "underloaded" early on)
    last_week_num = ((last_week_monday.date() - PLAN_START).days // 7) + 1
    last_week_target = targets[last_week_num - 1] if 0 <= last_week_num - 1 < len(targets) else 0
    load_status = ''
    load_badge = ''
    if last_week_target and last_week_km < last_week_target * 0.80:
        load_status = 'Underloaded'
        load_badge = 'bg-warning text-dark'
    elif last_week_target and last_week_km > last_week_target * 1.10:
        load_status = 'Overloaded ⚠️'
        load_badge = 'bg-danger'
    else:
        load_status = 'On track ✓'
        load_badge = 'bg-success'

    vol_html = build_volume_chart(weekly, targets, plan_start_ts)
    pace_html = build_pace_chart(weekly, runs)
    gantt_html = build_plan_gantt(targets)
    recent_table = _recent_runs_table(runs)
    plan_table = _weekly_plan_table(targets)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Munich Marathon 2026 — Training Dashboard</title>
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="Munich 2026">
  <link rel="apple-touch-icon" href="apple-touch-icon.png">
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
    /* ── Charts (native SVG / HTML) ── */
    .chart-wrap {{ width: 100%; }}
    .chart-svg {{ width: 100%; height: auto; display: block; }}
    .vbar {{ transition: opacity .12s; cursor: default; }}
    .vbar:hover {{ opacity: .8; }}
    .pdot {{ transition: r .1s; cursor: default; }}
    .pdot:hover {{ stroke: #fff; }}
    .gbar {{ cursor: default; transition: opacity .12s; }}
    .gbar:hover {{ opacity: 1 !important; }}
    .gbar-fill {{ transition: filter .12s; }}
    .gbar:hover .gbar-fill {{ filter: brightness(1.18); }}
    .chart-legend {{ display: flex; gap: 1.1rem; flex-wrap: wrap; margin-top: .6rem;
                     font-size: .76rem; color: #94a3b8; align-items: center; }}
    .chart-legend .ci {{ display: flex; align-items: center; gap: .4rem; }}
    .chart-legend .sw {{ width: 16px; height: 4px; border-radius: 2px; display: inline-block; }}
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
        <p class="hero-sub">Training Dashboard · Iker · Goal: Sub 4:00 &nbsp;·&nbsp; <span style="color:#93c5fd;font-weight:600">{today.strftime('%A, %B %d, %Y')}</span> &nbsp;·&nbsp; Last sync: {last_date}</p>
        <div class="countdown-block">
          <div class="cdown-item">
            <div class="cdown-num">{days_to_race}</div>
            <div class="cdown-label">Days to go</div>
          </div>
          <div class="cdown-sep">·</div>
          <div class="cdown-item">
            <div class="cdown-num">W{current_week_num}<span style="font-size:1.4rem;opacity:.6">/18</span></div>
            <div class="cdown-label">Training week</div>
          </div>
        </div>
      </div>
      <div class="col-md-4 mt-3 mt-md-0 text-md-end">
        <div class="phase-pill mb-2">Week {current_week_num} / 18 — {current_phase}</div><br>
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
        <div class="kpi-value">{last_week_km:.1f}</div>
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
        <div class="kpi-value">{last_week_pace_str}</div>
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

  <!-- CURRENT WEEK CALENDAR -->
  {calendar_html}

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
            <li><strong>Tue:</strong> Quality session — 400m intervals (Base) or VO2/tempo (Build+).</li>
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
            <li><strong>400m intervals (Base, W1–3):</strong> 6×400m with 2 min rest — first 3 reps at constant rhythm (~4:45–4:50/km), last 3 progressive getting faster each rep. Add 2 more reps in W3 when ready.</li>
            <li><strong>VO2 intervals (Build+):</strong> 6×1k or 5×1200m at 3–5k effort with 90 s–2 min recovery.</li>
            <li><strong>Tempo / Threshold:</strong> 20–40 min continuous at comfortably hard pace (4:50–5:20/km).</li>
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

    <div class="row g-3 mt-1">
      <div class="col-12">
        <div class="strategy-card" style="border-color:#f97316">
          <h6 style="color:#f97316">🏷️ Activity Naming Guide — How the plan agent detects your sessions</h6>
          <p style="font-size:.85rem;color:#94a3b8;margin-bottom:.75rem">
            The adaptive plan agent reads your <strong>Garmin / Intervals.icu activity name</strong> to
            decide whether you completed a quality session or just ran easy.
            Name your sessions accordingly so the agent adjusts your week correctly.
          </p>
          <div style="display:flex;flex-wrap:wrap;gap:.75rem">
            <div style="flex:1;min-width:200px;background:#0f172a;border-radius:8px;padding:.75rem">
              <div style="font-size:.7rem;font-weight:700;color:#f97316;text-transform:uppercase;margin-bottom:.5rem">⚡ Quality — include one of these keywords</div>
              <div style="display:flex;flex-wrap:wrap;gap:.3rem">
                <code style="background:#1e293b;color:#fbbf24;padding:.15rem .4rem;border-radius:4px;font-size:.8rem">Intervals</code>
                <code style="background:#1e293b;color:#fbbf24;padding:.15rem .4rem;border-radius:4px;font-size:.8rem">Tempo</code>
                <code style="background:#1e293b;color:#fbbf24;padding:.15rem .4rem;border-radius:4px;font-size:.8rem">MP Run</code>
              </div>
              <div style="font-size:.72rem;color:#64748b;margin-top:.5rem">Examples: <em>"Intervals 6×400m"</em>, <em>"Tempo 8k"</em>, <em>"MP Run 10k"</em></div>
            </div>
            <div style="flex:1;min-width:200px;background:#0f172a;border-radius:8px;padding:.75rem">
              <div style="font-size:.7rem;font-weight:700;color:#22c55e;text-transform:uppercase;margin-bottom:.5rem">🏃 Easy / Long — name freely</div>
              <div style="font-size:.82rem;color:#94a3b8">Any name works — the agent won't flag these as mismatches regardless of name.</div>
              <div style="font-size:.72rem;color:#64748b;margin-top:.5rem">Examples: <em>"Munich Running"</em>, <em>"Easy 10k"</em>, <em>"Long Run Sunday"</em></div>
            </div>
            <div style="flex:1;min-width:200px;background:#0f172a;border-radius:8px;padding:.75rem">
              <div style="font-size:.7rem;font-weight:700;color:#a78bfa;text-transform:uppercase;margin-bottom:.5rem">🔄 How to rename</div>
              <ol style="font-size:.8rem;color:#94a3b8;padding-left:1.1rem;margin:0">
                <li>Open <strong>Intervals.icu</strong> → Activities</li>
                <li>Click the activity → edit the title</li>
                <li>Push the updated CSV or wait for the daily auto-sync</li>
              </ol>
            </div>
          </div>
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
    targets = make_targets()
    build_dashboard(runs, weekly, targets)
