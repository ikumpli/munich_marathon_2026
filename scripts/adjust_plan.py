#!/usr/bin/env python3
"""
Adaptive plan agent — runs daily in GitHub Actions.

1. Loads the latest activity CSV.
2. Fills in actuals for every past day in plan.json.
3. Detects mismatches in the current training week
   (missed quality sessions, missed runs, etc.).
4. If mismatches exist, calls GitHub Models (free with GITHUB_TOKEN)
   to adjust the remaining days of the week.
5. Writes the updated plan.json back to the repo root.

The deploy workflow commits plan.json so adjustments persist across runs.
"""

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
from generate_dashboard import WEEKLY_PLAN, PLAN_START  # type: ignore

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
    if any(x in d for x in ["race day", "race 🏁"]):
        return "race"
    if "long" in d:
        return "long"
    if any(x in d for x in ["interval", "tempo", "vo2", "strides", "progressive↗", "quality"]):
        return "quality"
    if any(x in d for x in ["rest", "swim"]):
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
            "target_km": total_km,
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


# ── Fill actuals ──────────────────────────────────────────────────────────────

def fill_actuals(plan_data: dict, runs_df: pd.DataFrame) -> dict:
    """Match CSV activities to plan days by date and fill in actual_km / pace."""
    today_iso = date.today().isoformat()

    # Build date → aggregated stats from the CSV
    activity_by_date: dict = {}
    for _, row in runs_df.iterrows():
        d = row["Date"].date().isoformat()
        if d not in activity_by_date:
            activity_by_date[d] = {"km": 0.0, "paces": [], "hrs": [], "names": []}
        activity_by_date[d]["km"] += row["distance_km"]
        activity_by_date[d]["paces"].append(row["pace"])
        hr = row.get("avg_hr") if "avg_hr" in row.index else None
        if hr and pd.notna(hr):
            activity_by_date[d]["hrs"].append(float(hr))
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
                if act["paces"]:
                    day["actual_pace_min_km"] = round(
                        sum(act["paces"]) / len(act["paces"]), 4
                    )
                if act["hrs"]:
                    day["actual_hr"] = round(sum(act["hrs"]) / len(act["hrs"]), 0)
                if act["names"]:
                    day["actual_name"] = " + ".join(act["names"])
            else:
                # Explicitly mark past run days as 0 so the dashboard can show ✗
                if day["session_type"] in ("easy", "quality", "long"):
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


# ── LLM adjustment via GitHub Models (free) ──────────────────────────────────

def _fmt_pace(p: float) -> str:
    return f"{int(p)}:{int((p % 1) * 60):02d}"


def adjust_with_llm(week: dict, mismatches: list, github_token: str):
    """
    Calls GitHub Models (gpt-4o-mini, free with GITHUB_TOKEN) to adjust
    the remaining days of the week. Returns a list of updated day dicts,
    or None if the call fails.
    """
    try:
        from openai import OpenAI
    except ImportError:
        print("openai package not installed — skipping LLM adjustment.")
        return None

    today = date.today()
    past_days = [d for d in week["days"] if d["date"] <= today.isoformat()]
    future_days = [d for d in week["days"] if d["date"] > today.isoformat()]

    if not future_days:
        return None  # nothing left to adjust

    # Summarise what already happened
    past_lines = []
    for d in past_days:
        km = d.get("actual_km")
        if km is not None and km > 0:
            pace = _fmt_pace(d["actual_pace_min_km"]) if d.get("actual_pace_min_km") else "?"
            past_lines.append(
                f'- {d["day"]} {d["date"]}: Planned "{d["planned"]}". '
                f"Actual: {km:.1f} km @ {pace}/km."
            )
        else:
            past_lines.append(
                f'- {d["day"]} {d["date"]}: Planned "{d["planned"]}". Actual: no activity.'
            )

    # Summarise mismatches
    mismatch_lines = []
    for m in mismatches:
        if m["issue"] == "missed":
            mismatch_lines.append(f'- {m["day"]}: Missed planned run "{m["planned"]}".')
        elif m["issue"] == "quality_missed":
            mismatch_lines.append(
                f'- {m["day"]}: Planned quality session but ran {m["actual_km"]:.1f} km '
                f'easy @ {_fmt_pace(m["actual_pace"])}/km instead of "{m["planned"]}".'
            )

    # Summarise remaining days
    future_lines = [
        f'- {d["day"]} {d["date"]}: Planned "{d["planned"]}"'
        for d in future_days
    ]

    covered_km = sum((d.get("actual_km") or 0) for d in past_days)
    remaining_budget = week["target_km"] - covered_km

    system_prompt = (
        "You are an expert marathon coach assistant for Iker (25 y/o, marathon debut, goal: sub 4:00). "
        "Your job is MINIMAL adjustments only — change as little as possible. "
        "Return ONLY a valid JSON array — no prose, no markdown fences."
    )

    user_prompt = (
        f"Week {week['week']} — Phase: {week['phase']} — Target: {week['target_km']} km.\n\n"
        f"PAST DAYS:\n" + "\n".join(past_lines) + "\n\n"
        f"MISMATCHES:\n" + ("\n".join(mismatch_lines) if mismatch_lines else "- None") + "\n\n"
        f"REMAINING DAYS (return ALL of these, unchanged unless you must modify):\n" + "\n".join(future_lines) + "\n\n"
        f"RULES — follow strictly:\n"
        f"1. Change ONLY the minimum necessary. If a day does not need to change, return it exactly as planned.\n"
        f"2. If a quality session was missed, reschedule it to the NEXT DAY (tomorrow) if that day is not a rest day. "
        f"Replace whatever was planned there with the quality session. The displaced session is simply dropped.\n"
        f"3. If tomorrow is a rest day, try the day after. Priority order: Wed → Thu → Sat. Never skip to a later day "
        f"when an earlier non-rest day is available.\n"
        f"4. Mon and Fri are rest/swim days — never add runs there.\n"
        f"5. Preserve the long run on Sunday ({week['long_km']} km @ 6:00–6:20/km) exactly as planned. Never put the quality session on Sunday.\n"
        f"6. Do NOT add warm-up/cool-down blocks. Do NOT change distances or descriptions of unchanged days.\n"
        f"7. session_type must be one of: rest, easy, quality, long, race.\n\n"
        f"Return a JSON array for ALL remaining days. For unchanged days, return the planned text as-is. "
        f"When you adjust a day, overwrite its plan text directly:\n"
        f'[{{"date":"YYYY-MM-DD","day":"DDD","session_type":"TYPE","planned":"description"}}]'
    )

    client = OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=github_token,
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=900,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown code blocks if the model wraps the JSON
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]
        return json.loads(raw)
    except Exception as exc:
        print(f"LLM adjustment failed: {exc}")
        return None


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print("GITHUB_TOKEN not set — actuals will be filled but LLM adjustment is skipped.")

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

    # Fill actuals for all past days
    plan_data = fill_actuals(plan_data, runs)

    # Find current training week
    today = date.today()
    current_week_num = ((today - PLAN_START).days // 7) + 1
    current_week_num = max(1, min(current_week_num, len(plan_data["weeks"])))
    current_week = plan_data["weeks"][current_week_num - 1]

    # Detect mismatches and (optionally) call the LLM
    mismatches = detect_mismatches(current_week, today)
    if mismatches:
        issues = [m["issue"] for m in mismatches]
        print(f"Week {current_week_num}: mismatches detected — {issues}")
        if github_token:
            adjusted = adjust_with_llm(current_week, mismatches, github_token)
            if adjusted:
                day_map = {d["date"]: d for d in current_week["days"]}
                for adj in adjusted:
                    if adj["date"] in day_map:
                        target = day_map[adj["date"]]
                        target["planned"] = adj.get("planned", target["planned"])
                        target["session_type"] = adj.get("session_type", target["session_type"])
                print(f"Adjusted {len(adjusted)} remaining day(s).")
            else:
                print("LLM returned no adjustments.")
        else:
            print("No GITHUB_TOKEN — LLM step skipped.")
    else:
        print(f"Week {current_week_num}: plan is on track, no adjustments needed.")

    plan_data["last_adjusted"] = today.isoformat()
    PLAN_JSON.write_text(json.dumps(plan_data, indent=2, ensure_ascii=False))
    print(f"plan.json saved → {PLAN_JSON}")


if __name__ == "__main__":
    main()
