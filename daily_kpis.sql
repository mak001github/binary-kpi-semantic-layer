SELECT report_date, market,
       SUM(is_active) AS active_subscriptions_eod,
       SUM(is_acquired) AS acquired_subscriptions,
       SUM(is_churned) AS churned_subscriptions,
       SUM(has_successful_payment) AS paying_subscriptions,
       SUM(has_failed_payment) AS subscriptions_with_failed_payment,
       SUM(paid_transaction_count) AS paid_transactions,
       SUM(revenue_minor) AS revenue_minor
FROM subscription_day
GROUP BY report_date, market
