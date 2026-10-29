-- ================================================================================================
-- manufacturing.production_metrics - yield, scrap, on-time completion, downtime and cost of production orders.
-- Created by 01_notebooks/job_tasks/02a_create_metric_views.py. Definitions: Pages yield, downtime
-- (05_context/pages/).
-- ================================================================================================
CREATE OR REPLACE VIEW ${catalog}.manufacturing.`production_metrics`
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: >-
    Production KPIs at production-order grain: yield, scrap rate and on-time completion of COMPLETED orders,
    downtime minutes and cost (EUR), by plant, line, product, brand, status and finish month / quarter / year.
  source: ${catalog}.manufacturing.production_order
  joins:
    - name: line
      source: ${catalog}.manufacturing.production_line
      'on': source.line_code = line.line_code
    - name: plant
      source: ${catalog}.manufacturing.plant
      'on': source.plant_code = plant.plant_code
    - name: stops
      source: |-
        SELECT production_order_id, SUM(duration_min) AS downtime_min
        FROM ${catalog}.manufacturing.downtime_event
        GROUP BY production_order_id
      'on': source.production_order_id = stops.production_order_id
  dimensions:
    - name: plant_code
      expr: source.plant_code
      display_name: Plant
      synonyms: [plant, site, factory]
    - name: plant_name
      expr: plant.plant_name
      display_name: Plant name
    - name: line_code
      expr: source.line_code
      display_name: Line
      synonyms: [production line]
    - name: line_name
      expr: line.line_name
      display_name: Line name
    - name: product_name
      expr: source.product_name
      display_name: Product
    - name: brand
      expr: source.brand
      display_name: Brand
    - name: order_status
      expr: source.order_status
      display_name: Order status
    - name: finish_month
      expr: CAST(DATE_TRUNC('MONTH', source.actual_finish_date) AS DATE)
      display_name: Finish month
      comment: Month the order was completed (NULL if not completed).
      synonyms: [month]
    - name: finish_quarter
      expr: concat(YEAR(source.actual_finish_date), '-Q', QUARTER(source.actual_finish_date))
      display_name: Finish quarter
      synonyms: [quarter]
    - name: finish_year
      expr: YEAR(source.actual_finish_date)
      display_name: Finish year
      synonyms: [year]
  measures:
    - name: production_orders
      expr: COUNT(source.production_order_id)
      display_name: Production orders
      format:
        type: number
        decimal_places: {type: exact, places: 0}
    - name: completed_orders
      expr: COUNT(source.production_order_id) FILTER (WHERE source.order_status = 'completed')
      display_name: Completed orders
      format:
        type: number
        decimal_places: {type: exact, places: 0}
    - name: good_qty
      expr: SUM(source.good_qty) FILTER (WHERE source.order_status = 'completed')
      display_name: Good quantity
      synonyms: [output, good units]
      format:
        type: number
        decimal_places: {type: exact, places: 0}
    - name: scrap_qty
      expr: SUM(source.scrap_qty) FILTER (WHERE source.order_status = 'completed')
      display_name: Scrap quantity
      format:
        type: number
        decimal_places: {type: exact, places: 0}
    - name: yield_pct
      expr: 100 * MEASURE(good_qty) / (MEASURE(good_qty) + MEASURE(scrap_qty))
      display_name: Yield %
      comment: Good units / (good + scrap units) of completed orders, in percent.
      synonyms: [yield, first pass yield]
      format:
        type: number
        decimal_places: {type: exact, places: 2}
    - name: scrap_rate_pct
      expr: 100 * MEASURE(scrap_qty) / (MEASURE(good_qty) + MEASURE(scrap_qty))
      display_name: Scrap rate %
      synonyms: [scrap, scrap rate, waste]
      format:
        type: number
        decimal_places: {type: exact, places: 2}
    - name: on_time_completion_pct
      expr: >-
        100 * COUNT(source.production_order_id) FILTER (WHERE source.order_status = 'completed'
                                                         AND source.actual_finish_date <= source.planned_finish_date)
            / MEASURE(completed_orders)
      display_name: On-time completion %
      comment: Completed orders finished on or before the planned finish date, in percent.
      synonyms: [on time, schedule adherence]
      format:
        type: number
        decimal_places: {type: exact, places: 1}
    - name: downtime_minutes
      expr: SUM(stops.downtime_min)
      display_name: Downtime (minutes)
      synonyms: [downtime, stop time]
      format:
        type: number
        decimal_places: {type: exact, places: 0}
    - name: planned_cost_eur
      expr: SUM(source.planned_cost_eur) FILTER (WHERE source.order_status = 'completed')
      display_name: Planned cost (EUR)
      format:
        type: currency
        currency_code: EUR
        decimal_places: {type: exact, places: 2}
    - name: actual_cost_eur
      expr: SUM(source.actual_cost_eur) FILTER (WHERE source.order_status = 'completed')
      display_name: Actual cost (EUR)
      comment: Actual production cost of completed orders, EUR.
      synonyms: [production cost]
      format:
        type: currency
        currency_code: EUR
        decimal_places: {type: exact, places: 2}
    - name: cost_variance_eur
      expr: MEASURE(actual_cost_eur) - MEASURE(planned_cost_eur)
      display_name: Cost variance (EUR)
      comment: Actual - planned cost of completed orders (positive = over plan).
      format:
        type: currency
        currency_code: EUR
        decimal_places: {type: exact, places: 2}
$$
