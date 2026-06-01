# Munich Marathon 2026 — Training dashboard

This repository contains your training data export and tools to generate an interactive dashboard and publish it to GitHub Pages.

Quick start (local)

1. Create a Python environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Generate the dashboard locally:

```bash
python scripts/generate_dashboard.py
# open docs/index.html in your browser
```

3. Push to GitHub. The included GitHub Actions workflow will run on push to `main` or `master` and publish `docs/` to GitHub Pages.

Notes
- The generator reads `i600311_activities.csv` (Intervals.icu export). It filters running activities, computes weekly totals and rolling averages, and writes `docs/index.html`.
- The workflow uses `peaceiris/actions-gh-pages` to publish the `docs/` folder.
# munich_marathon_2026
Panel to prepare for the Munich Marathon 2026
