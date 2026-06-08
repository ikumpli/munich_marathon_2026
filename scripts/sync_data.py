#!/usr/bin/env python3
"""Sync activities from Intervals.icu API and write to i600311_activities.csv.

Usage (local):
  export INTERVALS_ICU_API_KEY="your_key_here"
  python scripts/sync_data.py

In GitHub Actions the key is read from the INTERVALS_ICU_API_KEY secret.
Never hardcode the key in this file.
"""
import os
import sys
import requests
import pandas as pd
from pathlib import Path

ATHLETE_ID = "i600311"
BASE_URL = f"https://intervals.icu/api/v1/athlete/{ATHLETE_ID}/activities"

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "i600311_activities.csv"

# Columns produced — match the Intervals.icu manual CSV export format
COLUMNS = ["id", "Type", "Date", "Distance", "Moving Time", "Name", "Avg HR", "Intensity", "Load"]


def fetch_activities(api_key: str, oldest: str = "2024-01-01") -> list:
    """Fetch all activities from the Intervals.icu REST API."""
    response = requests.get(
        BASE_URL,
        params={"oldest": oldest},
        auth=("API_KEY", api_key),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def activities_to_df(activities: list) -> pd.DataFrame:
    """Map API JSON fields to the CSV column names used by generate_dashboard.py."""
    rows = []
    for act in activities:
        rows.append({
            "id":           act.get("id", ""),
            "Type":         act.get("type", ""),
            "Date":         act.get("start_date_local", ""),
            "Distance":     act.get("distance") or 0,
            "Moving Time":  act.get("moving_time") or 0,
            "Name":         act.get("name", ""),
            "Avg HR":       act.get("average_heartrate", ""),
            "Intensity":    act.get("icu_intensity", ""),
            "Load":         act.get("icu_training_load", ""),
        })
    df = pd.DataFrame(rows, columns=COLUMNS)
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%dT%H:%M:%S")
    return df


def sync():
    api_key = os.environ.get("INTERVALS_ICU_API_KEY", "").strip()
    if not api_key:
        print("ERROR: INTERVALS_ICU_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching activities for athlete {ATHLETE_ID} from Intervals.icu...")
    activities = fetch_activities(api_key)
    print(f"  Received {len(activities)} activities from the API.")

    df = activities_to_df(activities)
    df.to_csv(CSV_PATH, index=False)
    print(f"  Wrote {len(df)} rows to {CSV_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    sync()
