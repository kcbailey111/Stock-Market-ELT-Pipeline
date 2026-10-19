-- Fact model: the "what happened" table. One row per stock per trading day.
-- It keeps the prices and adds calculations on top of them.
-- "Fact" is just the warehouse word for a table of measurable events.

with prices as (

    select * from {{ ref('stg_stock_prices') }}

),

with_metrics as (

    select
        trade_date,
        symbol,
        open_price,
        high_price,
        low_price,
        close_price,
        volume,
        -- Daily return: how much the close changed since the previous close.
        -- lag() looks back one row. 0.01 means "up 1%". The first day for each
        -- stock has no previous day, so this comes out null.
        close_price / lag(close_price) over w - 1 as daily_return,
        -- How wide the day's swing was, compared with the closing price.
        (high_price - low_price) / close_price as intraday_range_pct,
        -- Average close over this day and the 6 before it (7 trading days).
        avg(close_price) over (w rows between 6 preceding and current row) as moving_avg_7d,
        -- Same idea over 30 trading days. With less history, it averages whatever exists.
        avg(close_price) over (w rows between 29 preceding and current row) as moving_avg_30d,
        -- So a reader can see when the 30-day average is based on too few days.
        count(*) over (w rows between 29 preceding and current row) as days_in_30d_window
    from prices
    -- "w" is a window: do the math separately for each stock, in date order.
    -- Without "partition by symbol", Monday's KO price would follow Friday's AAPL price.
    window w as (partition by symbol order by trade_date)

)

select * from with_metrics
