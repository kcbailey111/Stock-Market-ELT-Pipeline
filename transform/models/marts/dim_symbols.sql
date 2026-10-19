-- Dimension model: the "who" table. One row per stock, describing the company.
-- Prices change every day; a company's name and sector almost never do,
-- so they live here instead of being repeated on every price row.

with symbols as (

    -- ref() means "this comes from another dbt object."
    -- symbols is the table dbt built by loading seeds/symbols.csv.
    select * from {{ ref('symbols') }}

)

select
    symbol,
    company_name,
    sector,
    industry
from symbols
