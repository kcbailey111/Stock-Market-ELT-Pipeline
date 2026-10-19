-- A singular test: one fixed check, unlike the macro test which takes arguments.
-- dbt passes this test only when the query returns zero rows.
-- A day whose highest price is below its lowest price is bad source data.

select *
from {{ ref('stg_stock_prices') }}
where high_price < low_price
