"""Regression checks for return-plan refresh and calendar consistency."""
import copy
import unittest
from datetime import date
from unittest.mock import patch
import tempfile
from pathlib import Path
import pandas as pd

import adjust_plan as tracker
import generate_dashboard as dashboard


class ReturnPlanTests(unittest.TestCase):
    def test_refresh_replaces_stale_prescriptions_preserves_actuals_and_history(self):
        plan = tracker.generate_plan_json()
        history = copy.deepcopy(plan['weeks'][:15])
        monday = copy.deepcopy(plan['weeks'][15]['days'][0])
        day = plan['weeks'][15]['days'][1]
        day.update(planned='Rest or swim', session_type='rest', actual_km=2.8,
                   actual_pace_min_km=6.4, actual_hr=130, actual_name='Return run')
        tracker.refresh_return_plan(plan)
        self.assertEqual(plan['weeks'][:15], history)
        self.assertEqual(plan['weeks'][15]['days'][0], monday)
        self.assertTrue(day['planned'].startswith('Easy 5k'))
        self.assertEqual(day['session_type'], 'easy')
        self.assertEqual(day['actual_km'], 2.8)
        self.assertEqual(day['actual_name'], 'Return run')
        refreshed = copy.deepcopy(plan)
        tracker.refresh_return_plan(plan)
        self.assertEqual(plan, refreshed)

    def test_daily_sums_and_run_counts(self):
        weeks = tracker.generate_plan_json()['weeks'][15:]
        self.assertEqual([w['target_km'] for w in weeks], [29, 20, 49.195])
        self.assertEqual([sum(d['session_type'] != 'rest' for d in w['days']) for w in weeks],
                         [3, 3, 3])
        self.assertEqual([w['long_km'] for w in weeks], [18, 10, 0])
        self.assertEqual(tracker.classify_session('Rest; review before longer run'), 'rest')
        self.assertEqual(dashboard._day_planned_km(weeks[-1]['days'][-1]['planned']), 42.195)
        self.assertAlmostEqual(weeks[-1]['target_km'] - 42.195, 7)
        self.assertEqual(tracker.classify_session('Easy 6k; practice race effort'), 'easy')

    def test_calendar_dates_updated_prescription_and_stable_uid(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(dashboard, 'OUT', Path(directory)):
            dashboard.build_ics()
            raw = (Path(directory) / 'training.ics').read_bytes()
            self.assertTrue(all(len(line) <= 75 for line in raw.split(b'\r\n')))
            text = raw.decode().replace('\r\n ', '').replace('\r\n', '\n')
        events = text.split('BEGIN:VEVENT')[1:]
        self.assertEqual(len(events), 126)
        proposed = next(e for e in events if 'DTSTART;VALUE=DATE:20260927' in e)
        self.assertIn('UID:20260927-w16-sun@munich-marathon-2026', proposed)
        self.assertIn('Long 18k maximum OR 110 min', proposed)
        self.assertIn('STATUS:CONFIRMED', proposed)
        self.assertIn('SEQUENCE:20260922', proposed)
        self.assertIn(dashboard.RETURN_PLAN_NOTE.replace(',', '\\,').replace(';', '\\;'), proposed)
        saturday = next(e for e in events if 'DTSTART;VALUE=DATE:20260912' in e)
        self.assertIn('SUMMARY:💤 Rest', saturday)
        historical = next(e for e in events if 'DTSTART;VALUE=DATE:20260809' in e)
        self.assertNotIn('STATUS:TENTATIVE', historical)

    def test_dashboard_counts_four_complete_calendar_weeks(self):
        class ReportingDate(date):
            @classmethod
            def today(cls):
                return cls(2026, 9, 7)
        runs = dashboard.load_and_clean(dashboard.DATA)
        weekly = dashboard.weekly_aggregates(runs)
        with tempfile.TemporaryDirectory() as directory, patch.object(dashboard, 'OUT', Path(directory)), patch.object(dashboard, 'date', ReportingDate):
            dashboard.build_dashboard(runs, weekly, dashboard.make_targets())
            html = (Path(directory) / 'index.html').read_text()
        self.assertIn('<div class="kpi-value">0.0</div>\n        <div class="kpi-label">km/week (last 4 complete weeks)</div>', html)
        self.assertIn('PROPOSED long 10k ceiling', html)
        self.assertIn('7 km training + 42.195 km', html)

    def test_calendar_gaps_and_weighted_pace(self):
        self.assertEqual(dashboard.pace_clock(5.875), '5:53')
        self.assertEqual(dashboard.pace_clock(5.9999), '6:00')
        runs = dashboard.load_and_clean(dashboard.DATA)
        weekly = dashboard.weekly_aggregates(runs).set_index('week_start')
        gap = weekly.loc['2026-08-10':'2026-08-31']
        self.assertEqual(len(gap), 4)
        self.assertEqual(gap.total_km.sum(), 0)
        self.assertTrue(gap.avg_pace.isna().all())
        self.assertEqual(weekly.loc['2026-08-31', 'rolling_km_4w'], 0)
        self.assertAlmostEqual(weekly.loc['2026-09-14', 'rolling_km_4w'], 15.3859225)
        self.assertAlmostEqual(weekly.loc['2026-09-14', 'avg_pace'], 187.75 / 32.59793)

    def test_multi_run_day_uses_distance_and_duration_weights(self):
        runs = pd.DataFrame([
            {'Date': pd.Timestamp('2026-09-15'), 'distance_km': 2, 'moving_time_min': 12,
             'pace': 6, 'avg_hr': 130, 'Name': 'Warmup'},
            {'Date': pd.Timestamp('2026-09-15'), 'distance_km': 8, 'moving_time_min': 40,
             'pace': 5, 'avg_hr': 160, 'Name': 'Run'},
        ])
        plan = tracker.generate_plan_json()
        tracker.fill_actuals(plan, runs)
        day = plan['weeks'][14]['days'][1]
        self.assertEqual(day['actual_km'], 10)
        self.assertEqual(day['actual_pace_min_km'], 5.2)
        self.assertEqual(day['actual_hr'], round((12 * 130 + 40 * 160) / 52))

    def test_review_curve_evidence_and_missing_curves(self):
        runs = dashboard.load_and_clean(dashboard.DATA)
        review = dashboard.review_metrics(runs, dashboard._load_run_curves())
        self.assertEqual(len(review['runs']), 63)
        self.assertAlmostEqual(review['runs'].distance_km.sum(), 536.41988)
        self.assertEqual(sum(s['n'] for s in review['segments']), 164)
        self.assertAlmostEqual(review['segments'][-1]['hr'], 165.925)
        missing = dashboard.review_metrics(runs, {})
        self.assertEqual(sum(s['n'] for s in missing['segments']), 0)
        self.assertIn('—', dashboard.strategy_html(missing, 'No curves available'))


if __name__ == '__main__':
    unittest.main()
