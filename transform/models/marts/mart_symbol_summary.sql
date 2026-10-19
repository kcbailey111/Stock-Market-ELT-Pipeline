-- Mart model: one row per stock summarizing its whole saved history.
-- This is the table a dashboard would show as a scoreboard.
-- It joins the daily facts to the dimension so each row carries the sector too.

with prices as (

    select * from {{ ref('fct_daily_prices') }}

),

symbols as (

    select * from {{ ref('dim_symbols') }}

),

summary as (

    select
        symbol,
        min(trade_date) as first_date,
        max(trade_date) as last_date,
        count(*) as trading_days,
        -- arg_max returns the close from whichever row has the latest date,
        -- i.e. the most recent price rather than the biggest price.
        arg_max(close_price, trade_date) as latest_close,
        min(low_price) as period_low,
        max(high_price) as period_high,
        avg(volume)::bigint as avg_volume,
        -- Standard deviation of the daily return. Bigger means the price jumps around more.
        -- Needs at least two returns, so it is null until a stock has a few days of history.
        stddev_samp(daily_return) as daily_volatility
    from prices
    group by symbol

)

select
    summary.symbol,
    symbols.company_name,
    symbols.sector,
    summary.first_date,
    summary.last_date,
    summary.trading_days,
    summary.latest_close,
    summary.period_low,
    summary.period_high,
    summary.avg_volume,
    summary.daily_volatility
from summary
-- left join keeps the stock even if it is missing from dim_symbols.
-- A test on the sector column fails in that case, so the gap gets noticed.
left join symbols
    on summary.symbol = symbols.symbol
