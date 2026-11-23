"""Build a subscription-day fact and a quality report from synthetic source data."""
import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path


def build(subscriptions, events, start, end):
    if start > end:
        raise ValueError("start must be on or before end")
    by_id = {}
    for sub in subscriptions:
        key = sub["subscription_id"]
        if not key.strip() or key in by_id or not sub["market"].strip():
            raise ValueError(f"Invalid or duplicate subscription: {key!r}")
        if sub["end"] and sub["end"] < sub["start"]:
            raise ValueError(f"Invalid subscription interval: {key}")
        by_id[key] = sub
    seen = {}
    daily_payments = defaultdict(list)
    duplicates = 0
    for event in events:
        key = event["event_id"]
        if not key.strip():
            raise ValueError("Event ID is required")
        if key in seen:
            if seen[key] != event:
                raise ValueError(f"Conflicting duplicate event: {key}")
            duplicates += 1
            continue
        sub = by_id.get(event["subscription_id"])
        if not sub or not (sub["start"] <= event["day"] <= (sub["end"] or date.max)):
            raise ValueError(f"Event outside a known subscription interval: {key}")
        if event["status"] not in {"paid", "failed"}:
            raise ValueError(f"Unknown payment status: {key}")
        amount = event["amount_minor"]
        if amount < 0 or (event["status"] == "failed" and amount != 0):
            raise ValueError(f"Invalid payment amount: {key}")
        seen[key] = event
        if start <= event["day"] <= end:
            daily_payments[(event["subscription_id"], event["day"])].append(event)
    rows = []
    for sub_id, sub in sorted(by_id.items()):
        day = max(start, sub["start"])
        last_day = min(end, sub["end"] or end)
        while day <= last_day:
            payments = daily_payments[(sub_id, day)]
            rows.append({
                "fact_id": f"{sub_id}:{day.isoformat()}",
                "subscription_id": sub_id,
                "report_date": day.isoformat(),
                "market": sub["market"],
                "is_active": int(sub["end"] != day),
                "is_acquired": int(sub["start"] == day),
                "is_churned": int(sub["end"] == day),
                "has_successful_payment": int(any(p["status"] == "paid" for p in payments)),
                "has_failed_payment": int(any(p["status"] == "failed" for p in payments)),
                "paid_transaction_count": sum(p["status"] == "paid" for p in payments),
                "revenue_minor": sum(p["amount_minor"] for p in payments if p["status"] == "paid"),
            })
            day += timedelta(days=1)
    flags = ("is_active", "is_acquired", "is_churned", "has_successful_payment", "has_failed_payment")
    keys = {row["fact_id"] for row in rows}
    revenue = sum(row["revenue_minor"] for row in rows)
    source_revenue = sum(
        p["amount_minor"] for p in seen.values()
        if p["status"] == "paid" and start <= p["day"] <= end
    )
    checks = {
        "unique_subscription_days": len(keys) == len(rows),
        "flags_are_binary": all(r[f] in (0, 1) for r in rows for f in flags),
        "revenue_reconciles": revenue == source_revenue,
    }
    if not all(checks.values()):
        raise RuntimeError(f"Quality checks failed: {checks}")
    return rows, {
        "report_start": start.isoformat(), "report_end": end.isoformat(),
        "fact_rows": len(rows), "exact_duplicate_events_removed": duplicates,
        "events_outside_report_window": sum(not start <= p["day"] <= end for p in seen.values()),
        "rows_by_market": dict(Counter(r["market"] for r in rows)),
        "flag_counts": {flag: sum(r[flag] for r in rows) for flag in flags},
        "checks": checks,
    }


def synthetic():
    d = date.fromisoformat
    subscriptions = [
        dict(subscription_id="a1", market="AE", start=d("2026-01-01"), end=d("2026-01-03")),
        dict(subscription_id="a2", market="AE", start=d("2026-01-02"), end=None),
        dict(subscription_id="b1", market="DE", start=d("2026-01-01"), end=None),
    ]
    events = [
        dict(event_id=f"e{i}", subscription_id=key, day=d(day), status=status, amount_minor=amount)
        for i, (key, day, status, amount) in enumerate([
            ("a1", "2026-01-01", "paid", 1000), ("a1", "2026-01-01", "paid", 500),
            ("a1", "2026-01-01", "failed", 0), ("b1", "2026-01-02", "paid", 900),
        ], 1)
    ]
    return subscriptions, events + [events[0].copy()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("output"))
    args = parser.parse_args()
    rows, profile = build(*synthetic(), date(2026, 1, 1), date(2026, 1, 3))
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "subscription_day.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (args.out / "profile.json").write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
