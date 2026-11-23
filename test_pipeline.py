import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from build_fact import build, synthetic
from make_wren_project import COLUMNS, generate


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.start, self.end = date(2026, 1, 1), date(2026, 1, 3)
        self.subscriptions, self.events = synthetic()

    def test_grain_and_retry_deduplication(self):
        rows, profile = build(self.subscriptions, self.events, self.start, self.end)
        self.assertEqual(len(rows), 8)
        self.assertEqual(profile["exact_duplicate_events_removed"], 1)
        self.assertTrue(all(profile["checks"].values()))
        self.assertEqual(sum(r["revenue_minor"] for r in rows), 2400)

    def test_conflicting_event_fails_closed(self):
        self.events[-1]["amount_minor"] = 300
        with self.assertRaisesRegex(ValueError, "Conflicting duplicate"):
            build(self.subscriptions, self.events, self.start, self.end)

    def test_payment_outside_subscription_fails_closed(self):
        self.events[0]["day"] = date(2026, 1, 4)
        with self.assertRaisesRegex(ValueError, "outside a known subscription interval"):
            build(self.subscriptions, self.events, self.start, self.end)

    def test_governed_sql_distinguishes_payers_from_transactions(self):
        rows, _ = build(self.subscriptions, self.events, self.start, self.end)
        with sqlite3.connect(":memory:") as database:
            columns = ", ".join(COLUMNS)
            database.execute(f"CREATE TABLE subscription_day ({columns})")
            placeholders = ", ".join("?" for _ in COLUMNS)
            database.executemany(
                f"INSERT INTO subscription_day VALUES ({placeholders})",
                [tuple(r[n] for n in COLUMNS) for r in rows],
            )
            query = Path(__file__).with_name("daily_kpis.sql").read_text(encoding="utf-8")
            result = database.execute(query).fetchall()
        self.assertIn(("2026-01-01", "AE", 1, 1, 0, 1, 1, 2, 1500), result)
        self.assertIn(("2026-01-03", "AE", 1, 0, 1, 0, 0, 0, 0), result)

    def test_wren_view_points_to_governed_fact(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            generate(root)
            view = (root / "views/daily_market_kpis/metadata.yml").read_text()
            self.assertIn("FROM wren.public.subscription_day", view)
            self.assertIn("SUM(has_successful_payment) AS paying_subscriptions", view)
            self.assertIn("data_source: redshift", (root / "wren_project.yml").read_text())
