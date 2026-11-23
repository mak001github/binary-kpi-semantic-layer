"""Scaffold a Redshift-backed Wren MDL project without storing credentials."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COLUMNS = {
    "fact_id": ("VARCHAR", "Unique key for a subscription on a reporting day."),
    "subscription_id": ("VARCHAR", "Synthetic subscription identifier."),
    "report_date": ("DATE", "Calendar day at which metrics are evaluated."),
    "market": ("VARCHAR", "Market code. Revenue uses a market-local currency."),
    "is_active": ("SMALLINT", "One when active at end of day. Excludes the churn day."),
    "is_acquired": ("SMALLINT", "One on the subscription start date."),
    "is_churned": ("SMALLINT", "One on the subscription end date."),
    "has_successful_payment": ("SMALLINT", "One when at least one payment succeeded that day."),
    "has_failed_payment": ("SMALLINT", "One when at least one payment failed that day."),
    "paid_transaction_count": ("BIGINT", "Count of successful transactions for the subscription-day."),
    "revenue_minor": ("BIGINT", "Successful payment amount in market-local minor currency units."),
}


def generate(target):
    model = target / "models" / "subscription_day"
    view = target / "views" / "daily_market_kpis"
    for directory in (model, view):
        directory.mkdir(parents=True, exist_ok=True)
    (target / "wren_project.yml").write_text(
        'schema_version: 5\nname: binary_kpi_semantic_layer\nversion: "1.0"\n'
        'catalog: wren\nschema: public\ndata_source: redshift\n', encoding="utf-8",
    )
    lines = [
        "name: subscription_day", "table_reference:", "  schema: analytics",
        "  table: subscription_day", "primary_key: fact_id", "columns:",
    ]
    for name, (datatype, description) in COLUMNS.items():
        lines.extend([f"  - name: {name}", f"    type: {datatype}", "    not_null: true",
                      "    properties:", f"      description: {json.dumps(description)}"])
    (model / "metadata.yml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    query = (ROOT / "daily_kpis.sql").read_text(encoding="utf-8").replace(
        "FROM subscription_day", "FROM wren.public.subscription_day"
    )
    (view / "metadata.yml").write_text(
        "name: daily_market_kpis\nstatement: |\n"
        + "".join(f"  {line}\n" for line in query.splitlines())
        + "properties:\n  description: Daily market KPIs. Revenue is in market-local minor units.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("wren-project"))
    generate(parser.parse_args().out)
