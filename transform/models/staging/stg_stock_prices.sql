-- Staging model: a clean version of the raw stock_metrics table.
-- Staging does light tidying only. No math, no averages, no combining tables.
-- It is built as a view (see dbt_project.yml), so it always shows current data.

with source as (

    -- source() means "this table was loaded by something outside dbt."
    -- The name raw.stock_metrics is defined in _sources.yml.
    select * from {{ source('raw', 'stock_metrics') }}

),

renamed as (

    select
        -- The raw column is called "date", which is vague. trade_date says which date it is.
        cast(date as date) as trade_date,
        -- "aapl" and "AAPL" would count as two stocks. Force one spelling.
        upper(trim(symbol)) as symbol,
        open_price,
        high_price,
        low_price,
        close_price,
        volume,
        loaded_at
    from source

)

select * from renamed
