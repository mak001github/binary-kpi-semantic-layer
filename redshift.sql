-- Run on Redshift. Replace the S3 URI and IAM role before executing COPY.
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE TABLE IF NOT EXISTS analytics.subscription_day (
    fact_id VARCHAR(160) NOT NULL,
    subscription_id VARCHAR(120) NOT NULL,
    report_date DATE NOT NULL,
    market VARCHAR(16) NOT NULL,
    is_active SMALLINT NOT NULL,
    is_acquired SMALLINT NOT NULL,
    is_churned SMALLINT NOT NULL,
    has_successful_payment SMALLINT NOT NULL,
    has_failed_payment SMALLINT NOT NULL,
    paid_transaction_count BIGINT NOT NULL,
    revenue_minor BIGINT NOT NULL,
    PRIMARY KEY (fact_id)
) DISTSTYLE AUTO SORTKEY (report_date, market);

-- This demo replaces a complete snapshot. Do not run concurrent refreshes.
BEGIN;
LOCK TABLE analytics.subscription_day;
CREATE TEMP TABLE subscription_day_stage (LIKE analytics.subscription_day);
COPY subscription_day_stage
FROM 's3://YOUR_BUCKET/semantic-demo/subscription_day.csv'
IAM_ROLE 'arn:aws:iam::YOUR_ACCOUNT:role/YOUR_REDSHIFT_COPY_ROLE'
FORMAT AS CSV IGNOREHEADER 1;

DELETE FROM analytics.subscription_day;
INSERT INTO analytics.subscription_day SELECT * FROM subscription_day_stage;
DROP TABLE subscription_day_stage;
COMMIT;
