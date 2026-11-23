# Binary KPI Semantic Layer

Synthetic subscription analytics with a one-row-per-subscription-per-day fact, Python data profiling, Amazon S3 staging, Redshift and Wren MDL.

## Metric design

A daily payer flag counts a subscription once even if two payments succeed. Transaction count captures both. Failed and successful flags can coexist, and the churn day is excluded from the end-of-day active base. Revenue is expressed in market-local minor units.

## Local verification

Run `python3 build_fact.py`, `python3 make_wren_project.py`, then `python3 -m unittest -v`. The generated snapshot and quality report are under `output/`. Five tests cover event deduplication, lifecycle validation, grain, SQL aggregation and Wren view wiring. AWS deployment and live Wren execution have not been verified.
