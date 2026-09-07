"""Regression checks for return-plan refresh and calendar consistency."""
import copy
import unittest
from datetime import date
from unittest.mock import patch
import tempfile
from pathlib import Path

import adjust_plan as tracker
import generate_dashboard as dashboard


class ReturnPlanTests(unittest.TestCase):
    def test_refresh_replaces_stale_prescriptions_preserves_actuals_and_history(self):
        plan = tracker.generate_plan_json()
        history = copy.deepcopy(plan['weeks'][:13])
        day = plan['weeks'][13]['days'][0]
        day.update(planned='Rest or swim', session_type='rest', actual_km=2.8,
                   actual_pace_min_km=6.4, actual_hr=130, actual_name='Return run')
        tracker.refresh_return_plan(plan)
        self.assertEqual(plan['weeks'][:13], history)
        self.assertTrue(day['planned'].startswith('Easy 3k'))
        self.assertEqual(day['session_type'], 'easy')
        self.assertEqual(day['actual_km'], 2.8)
        self.assertEqual(day['actual_name'], 'Return run')
        refreshed = copy.deepcopy(plan)
        tracker.refresh_return_plan(plan)
        self.assertEqual(plan, refreshed)

    def test_daily_sums_and_run_counts(self):
        weeks = tracker.generate_plan_json()['weeks'][13:]
        self.assertEqual([w['target_km'] for w in weeks], [23, 30, 36, 24, 48.2])
        self.assertEqual([sum(d['session_type'] != 'rest' for d in w['days']) for w in weeks],
                         [4, 5, 5, 5, 3])
        self.assertEqual([w['long_km'] for w in weeks], [10, 14, 20, 10, 0])
        self.assertEqual(tracker.classify_session('Rest; review before longer run'), 'rest')
        self.assertEqual(dashboard._day_planned_km(weeks[-1]['days'][-1]['planned']), 42.2)

    def test_calendar_dates_draft_status_and_stable_uid(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(dashboard, 'OUT', Path(directory)):
            dashboard.build_ics()
            text = (Path(directory) / 'training.ics').read_text().replace('\n ', '')
        events = text.split('BEGIN:VEVENT')[1:]
        self.assertEqual(len(events), 126)
        proposed = next(e for e in events if 'DTSTART;VALUE=DATE:20260927' in e)
        self.assertIn('UID:20260927-w16-sun@munich-marathon-2026', proposed)
        self.assertIn('PROPOSED long 20k ceiling', proposed)
        self.assertIn('STATUS:TENTATIVE', proposed)
        self.assertIn(dashboard.RETURN_PLAN_NOTE.replace(',', '\\,').replace(';', '\\;'), proposed)
        saturday = next(e for e in events if 'DTSTART;VALUE=DATE:20260912' in e)
        self.assertIn('SUMMARY:DRAFT — 💤 Rest', saturday)
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
        self.assertIn('6 km training + 42.2 km', html)


if __name__ == '__main__':
    unittest.main()
