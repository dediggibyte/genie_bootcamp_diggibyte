-- ================================================================================================
-- consumer.dtc_sales_metrics - webshop KPIs: GMV, orders, AOV, return rate, active shoppers (EUR).
-- Created by 01_notebooks/job_tasks/02a_create_metric_views.py. Definitions: Pages gmv, return_rate,
-- active_shopper (05_context/pages/).
-- ================================================================================================
CREATE OR REPLACE VIEW ${catalog}.consumer.`dtc_sales_metrics`
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: >-
    DTC webshop KPIs at order grain, EUR: GMV and orders of placed orders (delivered or returned, never
    cancelled), average order value, return rate and active shoppers, by order date / month / quarter /
    year, market, order status and loyalty tier.
  source: ${catalog}.consumer.dtc_order
  joins:
    - name: shopper
      source: ${catalog}.consumer.shopper
      'on': source.shopper_id = shopper.shopper_id
  dimensions:
    - name: order_date
      expr: source.order_date
      display_name: Order date
    - name: order_month
      expr: CAST(DATE_TRUNC('MONTH', source.order_date) AS DATE)
      display_name: Order month
      synonyms: [month]
    - name: order_quarter
      expr: concat(YEAR(source.order_date), '-Q', QUARTER(source.order_date))
      display_name: Order quarter
      synonyms: [quarter]
    - name: order_year
      expr: YEAR(source.order_date)
      display_name: Order year
      synonyms: [year]
    - name: company_code
      expr: source.company_code
      display_name: Market entity
      comment: SE01, NO01, DK01, FI01, DE01 (Germany and the Netherlands).
    - name: country_code
      expr: source.country_code
      display_name: Market country
      synonyms: [country, market]
    - name: order_status
      expr: source.order_status
      display_name: Order status
    - name: loyalty_tier
      expr: COALESCE(shopper.loyalty_tier, 'Not a member')
      display_name: Loyalty tier
      synonyms: [tier, loyalty level]
  measures:
    - name: orders
      expr: COUNT(source.order_id) FILTER (WHERE source.order_status <> 'cancelled')
      display_name: Placed orders
      comment: Orders that were not cancelled (delivered or returned).
      synonyms: [number of orders, order count]
      format:
        type: number
        decimal_places: {type: exact, places: 0}
    - name: gmv_eur
      expr: SUM(source.order_amount_eur) FILTER (WHERE source.order_status <> 'cancelled')
      display_name: GMV (EUR)
      comment: Gross merchandise value = order value of placed orders, net of VAT, excl. shipping, EUR.
      synonyms: [GMV, gross merchandise value, webshop sales, order value]
      format:
        type: currency
        currency_code: EUR
        decimal_places: {type: exact, places: 2}
    - name: average_order_value_eur
      expr: MEASURE(gmv_eur) / MEASURE(orders)
      display_name: Average order value (EUR)
      synonyms: [AOV, basket size]
      format:
        type: currency
        currency_code: EUR
        decimal_places: {type: exact, places: 2}
    - name: returned_orders
      expr: COUNT(source.order_id) FILTER (WHERE source.order_status = 'returned')
      display_name: Returned orders
      format:
        type: number
        decimal_places: {type: exact, places: 0}
    - name: return_rate_pct
      expr: 100 * MEASURE(returned_orders) / MEASURE(orders)
      display_name: Return rate %
      comment: Returned orders / placed orders in percent.
      synonyms: [returns, return rate]
      format:
        type: number
        decimal_places: {type: exact, places: 1}
    - name: active_shoppers
      expr: COUNT(DISTINCT source.shopper_id) FILTER (WHERE source.order_status <> 'cancelled')
      display_name: Active shoppers
      comment: Distinct shoppers with a placed order in the filtered period (the Page uses the last 12 months).
      synonyms: [active customers, buying shoppers]
      format:
        type: number
        decimal_places: {type: exact, places: 0}
$$
