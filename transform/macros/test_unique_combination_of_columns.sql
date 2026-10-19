-- A macro is a reusable SQL template. This one is a test.
-- dbt runs it and the test passes only when the query returns zero rows.
--
-- Example: called with trade_date and symbol, it groups the rows by those two
-- columns and returns any pair that shows up more than once. No rows returned
-- means every stock has at most one row per day.

{% test unique_combination_of_columns(model, combination_of_columns) %}

select
    {{ combination_of_columns | join(', ') }},
    count(*) as row_count
from {{ model }}
group by {{ combination_of_columns | join(', ') }}
having count(*) > 1

{% endtest %}
