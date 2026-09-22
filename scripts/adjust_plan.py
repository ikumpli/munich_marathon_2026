#!/usr/bin/env python3
"""
Plan-tracking agent — runs daily in GitHub Actions.

1. Loads the latest activity CSV.
2. Fills in actuals for every past day in plan.json.
3. Detects mismatches in the current training week
   (missed quality sessions, missed runs, etc.) for informational logging only.

No automatic rewriting of the plan happens — the static WEEKLY_PLAN in
generate_dashboard.py is always the source of truth for `planned`/`session_type`.
The deploy workflow commits plan.json so actuals persist across runs.
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
from generate_dashboard import WEEKLY_PLAN, PLAN_START, RETURN_PLAN_START, RETURN_PLAN_NOTE, _week_planned_km  # type: ignore

DATA = ROOT / "i600311_activities.csv"
PLAN_JSON = ROOT / "plan.json"

DAYS_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAYS_DEFAULTS = {
    "Mon": "Rest or swim",
    "Tue": "Quality session",
    "Wed": "Easy recovery run @6:10–6:30/km",
    "Thu": "Easy run @6:10–6:30/km",
    "Fri": "Rest",
    "Sat": "Steady run @5:50–6:10/km",
    "Sun": "Long run",
}


# ── Session classification ────────────────────────────────────────────────────

def classify_session(desc: str) -> str:
    d = desc.lower()
    if d.startswith("rest"):
        return "rest"
    if d.startswith(("race ", "conditional race")):
        return "race"
    if "long" in d:
        return "long"
    # Guard against negated phrases like "no strides, save legs" (an easy day
    # that explicitly avoids strides) being misread as a quality keyword match.
    d_check = d.replace("no strides", "").replace("without strides", "")
    if any(x in d_check for x in ["interval", "tempo", "vo2", "strides", "progressive↗", "quality"]):
        return "quality"
    if d.startswith(("rest", "swim")):
        return "rest"
    return "easy"


# ── Plan JSON initialisation ──────────────────────────────────────────────────

def _parse_day_sessions(quality: str) -> dict:
    result = {}
    for part in quality.split(" · "):
        if ": " in part:
            day, desc = part.split(": ", 1)
            result[day.strip()] = desc.strip()
    return result


def generate_plan_json() -> dict:
    """Build the full plan.json from the static WEEKLY_PLAN definition."""
    weeks = []
    for wnum, wdate_str, total_km, long_km, quality, phase in WEEKLY_PLAN:
        week_start = PLAN_START + timedelta(weeks=wnum - 1)
        day_sessions = _parse_day_sessions(quality)
        days = []
        for i, day_name in enumerate(DAYS_ORDER):
            day_date = week_start + timedelta(days=i)
            desc = day_sessions.get(day_name, DAYS_DEFAULTS.get(day_name, "Rest"))
            days.append({
                "date": day_date.isoformat(),
                "day": day_name,
                "session_type": classify_session(desc),
                "planned": desc,
                "actual_km": None,
                "actual_pace_min_km": None,
                "actual_hr": None,
                "actual_name": None,
            })
        weeks.append({
            "week": wnum,
            "date": week_start.isoformat(),
            "phase": phase,
            # Same per-day-sum computation generate_dashboard.py uses for the plan
            # table/charts/calendar, so this never drifts from what's displayed.
            "target_km": _week_planned_km(quality),
            "long_km": long_km,
            "days": days,
        })
    return {
        "generated": date.today().isoformat(),
        "last_adjusted": None,
        "weeks": weeks,
    }


def load_or_init_plan() -> dict:
    if PLAN_JSON.exists():
        with open(PLAN_JSON) as f:
            return json.load(f)
    plan = generate_plan_json()
    PLAN_JSON.write_text(json.dumps(plan, indent=2, ensure_ascii=False))
    print("plan.json created from WEEKLY_PLAN.")
    return plan


def refresh_return_plan(plan_data: dict) -> None:
    """Refresh revised prescriptions without replacing historical days or actuals."""
    revised = {w["week"]: w for w in generate_plan_json()["weeks"]
               if any(d["date"] >= RETURN_PLAN_START.isoformat() for d in w["days"])}
    for week in plan_data["weeks"]:
        new = revised.get(week["week"])
        if new is None:
            continue
        for field in ("phase", "target_km", "long_km"):
            week[field] = new[field]
        by_date = {day["date"]: day for day in new["days"]}
        for day in week["days"]:
            if day["date"] in by_date and day["date"] >= RETURN_PLAN_START.isoformat():
                for field in ("planned", "session_type"):
                    day[field] = by_date[day["date"]][field]
    plan_data["revision"] = {
        "effective_from": RETURN_PLAN_START.isoformat(),
        "status": "taper_review_2026_09_22",
        "note": RETURN_PLAN_NOTE,
    }


# ── Fill actuals ──────────────────────────────────────────────────────────────

def fill_actuals(plan_data: dict, runs_df: pd.DataFrame) -> dict:
    """Match CSV activities to plan days by date and fill in actual_km / pace."""
    today_iso = date.today().isoformat()

    # Build date → aggregated stats from the CSV
    activity_by_date: dict = {}
    for _, row in runs_df.iterrows():
        d = row["Date"].date().isoformat()
        if d not in activity_by_date:
            activity_by_date[d] = {"km": 0.0, "minutes": 0.0, "hr_minutes": 0.0, "hr_duration": 0.0, "names": []}
        activity_by_date[d]["km"] += row["distance_km"]
        activity_by_date[d]["minutes"] += row["moving_time_min"]
        hr = row.get("avg_hr") if "avg_hr" in row.index else None
        if hr and pd.notna(hr):
            activity_by_date[d]["hr_minutes"] += float(hr) * row["moving_time_min"]
            activity_by_date[d]["hr_duration"] += row["moving_time_min"]
        name = row.get("Name") if "Name" in row.index else None
        if name and pd.notna(name):
            activity_by_date[d]["names"].append(str(name))

    for week in plan_data["weeks"]:
        for day in week["days"]:
            d = day["date"]
            if d > today_iso:
                continue  # don't touch future days (but do fill today)
            if d in activity_by_date:
                act = activity_by_date[d]
                day["actual_km"] = round(act["km"], 2)
                day["actual_pace_min_km"] = round(act["minutes"] / act["km"], 4)
                if act["hr_duration"]:
                    day["actual_hr"] = round(act["hr_minutes"] / act["hr_duration"], 0)
                if act["names"]:
                    day["actual_name"] = " + ".join(act["names"])
            else:
                # Explicitly mark past run days as 0 so the dashboard can show ✗
                if d < today_iso and day["session_type"] in ("easy", "quality", "long"):
                    day["actual_km"] = 0.0

    return plan_data


# ── Mismatch detection ────────────────────────────────────────────────────────

# Keywords in the Garmin activity Name that confirm a quality session was done
_QUALITY_KEYWORDS = (
    "interval", "intervals", "tempo", "mp run", "mp pace",
)


def _activity_looks_like_quality(day: dict) -> bool:
    """Return True if the actual activity signals a quality session was performed."""
    name = (day.get("actual_name") or "").lower()
    if any(kw in name for kw in _QUALITY_KEYWORDS):
        return True
    # Interval sessions produce short total distances (warmup + reps + cooldown ≈ 4–7 km)
    # AND a clearly fast average pace (sub-5:10/km reflects hard rep efforts)
    pace = day.get("actual_pace_min_km")
    km = day.get("actual_km") or 0
    if pace and pace < 5.17 and km < 9:
        return True
    return False


def detect_mismatches(week: dict, today: date) -> list:
    """Return mismatches for past days in this week only."""
    mismatches = []
    for day in week["days"]:
        if day["date"] > today.isoformat():
            break  # only examine past days and today
        stype = day["session_type"]
        actual_km = day.get("actual_km")

        if stype in ("quality", "easy", "long") and (actual_km is None or actual_km < 1.0):
            mismatches.append({
                "date": day["date"],
                "day": day["day"],
                "issue": "missed",
                "planned": day["planned"],
                "actual_km": actual_km,
            })
        elif stype == "quality" and actual_km and actual_km > 1.0:
            # Quality planned — check if it was actually a quality session
            if not _activity_looks_like_quality(day):
                mismatches.append({
                    "date": day["date"],
                    "day": day["day"],
                    "issue": "quality_missed",
                    "planned": day["planned"],
                    "actual_km": actual_km,
                    "actual_pace": day.get("actual_pace_min_km"),
                    "actual_name": day.get("actual_name"),
                })
    return mismatches


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not DATA.exists():
        print(f"Data file not found: {DATA}. Skipping.")
        return

    # Load and parse runs from CSV
    df = pd.read_csv(DATA)
    df["Date"] = pd.to_datetime(df["Date"])
    runs = df[df["Type"].str.lower() == "run"].copy()
    runs["distance_km"] = runs["Distance"].astype(float) / 1000.0
    runs["moving_time_min"] = runs["Moving Time"].astype(float) / 60.0
    runs = runs[runs["distance_km"] > 0].copy()
    runs["pace"] = runs["moving_time_min"] / runs["distance_km"]
    runs = runs[runs["pace"].apply(lambda p: pd.notna(p) and p != float("inf"))].copy()
    runs["avg_hr"] = pd.to_numeric(runs.get("Avg HR", float("nan")), errors="coerce")

    # Load or create plan.json
    plan_data = load_or_init_plan()
    refresh_return_plan(plan_data)

    # Refresh weekly targets from WEEKLY_PLAN so an existing plan.json follows
    # any change to the planned-km parsing (e.g. interval-session estimates)
    quality_by_week = {row[0]: row[4] for row in WEEKLY_PLAN}
    for week in plan_data["weeks"]:
        if week["week"] in quality_by_week:
            week["target_km"] = _week_planned_km(quality_by_week[week["week"]])

    # Fill actuals for all past days
    plan_data = fill_actuals(plan_data, runs)

    # Find current training week
    today = date.today()
    current_week_num = ((today - PLAN_START).days // 7) + 1
    current_week_num = max(1, min(current_week_num, len(plan_data["weeks"])))
    current_week = plan_data["weeks"][current_week_num - 1]

    # Detect mismatches — informational only, the plan is never auto-rewritten.
    mismatches = detect_mismatches(current_week, today)
    if mismatches:
        issues = [m["issue"] for m in mismatches]
        print(f"Week {current_week_num}: mismatches detected (no auto-adjustment) — {issues}")
    else:
        print(f"Week {current_week_num}: plan is on track.")

    plan_data["last_adjusted"] = today.isoformat()
    PLAN_JSON.write_text(json.dumps(plan_data, indent=2, ensure_ascii=False))
    print(f"plan.json saved → {PLAN_JSON}")


if __name__ == "__main__":
    main()
