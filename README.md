# Munich Marathon 2026 — Training Dashboard

An auto-generated interactive dashboard published to **GitHub Pages** — tracking Iker's training for the Munich Marathon on **October 11, 2026**.

**Live dashboard:** [ikumpli.github.io/munich_marathon_2026](https://ikumpli.github.io/munich_marathon_2026)

---

## Tech stack

| Layer | Tool |
|---|---|
| Data | `pandas` — reads Intervals.icu CSV export |
| Charts | `plotly` — interactive HTML charts |
| Styling | Bootstrap 5 (CDN) — responsive layout |
| Hosting | GitHub Pages (static `docs/index.html`) |
| CI/CD | GitHub Actions — auto-deploys on push to `main` |

---

## Updating your training data

1. Go to [Intervals.icu](https://intervals.icu) → **Activities**.
2. Select all activities → **Export CSV**.
3. Replace `i600311_activities.csv` in the repo root with the downloaded file.
4. Commit and push to `main` — GitHub Actions will rebuild and deploy the dashboard automatically.

> The CSV must be the **English** export from Intervals.icu.  
> Key columns used: `id`, `Type`, `Date`, `Distance` (m), `Moving Time` (s), `Name`, `Avg HR`.

---

## Local development

```bash
# 1. Create a Python environment and install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Generate the dashboard
python scripts/generate_dashboard.py
# → open docs/index.html in your browser

# 3. Push to GitHub to publish on GitHub Pages
git add i600311_activities.csv docs/
git commit -m "Update training data"
git push
```

---

## GitHub Pages setup (first time)

1. Push the repo to GitHub.
2. Go to **Settings → Pages → Source** and set it to **Deploy from the `gh-pages` branch** (the workflow uses `peaceiris/actions-gh-pages`).
3. The first push to `main` will trigger the build and deploy.

---

## Dashboard panels

- **KPI cards** — days to race, 4-week avg km/week, last week km, longest run, current avg pace, target marathon pace.
- **Weekly volume chart** — observed km bars vs planned target line + 4-week rolling average.
- **Pace history chart** — session pace scatter + rolling average + target marathon pace reference.
- **Recent sessions table** — last 10 runs with distance, pace, and average HR.


## Coaching revision — 22 September 2026

The updated dashboard includes a full training review, the remaining daily schedule,
and a rebuilt Race Strategy tab with HR trends, staged pacing, slowdown rules and fueling.
Weekly training ceilings are 29 km, 20 km and 7 km before the 42.195 km race.
`scripts/coaching.py` owns the dated review and final three weekly prescriptions.
Future data syncs refresh activity charts; they do not silently rewrite coaching advice.

Regenerate locally with `python scripts/adjust_plan.py` followed by
`python scripts/generate_dashboard.py`. Run regression checks using
`python -m unittest discover -s scripts -p 'test_*.py'`.

This local revision does not publish to GitHub Pages until you push it through the existing workflow.

The race strategy now includes a user-requested conditional sub-4 attempt, verified elapsed-time splits, fallback checkpoints and an optional short goal-pace rehearsal inside the existing 6 km session. Training-volume ceilings remain unchanged.
