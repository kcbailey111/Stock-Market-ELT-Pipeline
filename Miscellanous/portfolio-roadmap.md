# Portfolio roadmap

What is left to turn this project into something you can talk through in an analytics engineering or data engineering interview. Each item says what to build and what skill it proves.

## Already in place

- [x] Extract, validate, and load daily prices from Alpha Vantage into DuckDB
- [x] Idempotent loads (`ON CONFLICT DO NOTHING`) and per-symbol failure handling
- [x] Scheduled GitHub Actions run that commits the updated database
- [x] API key kept in `.env` locally and in a GitHub secret in CI
- [x] Pinned dependencies and the same Python version locally and in CI
- [x] dbt project with a staging model, a dimension, a fact table, and a summary mart
- [x] dbt tests for grain, keys, relationships, and price sanity, plus a source freshness check
- [x] README with an architecture diagram, data model, and design decisions

## Do next (this project)

These three are the highest-leverage gaps. Employers can see them without cloning the repo or reading the code.

- [ ] **Publish the dbt docs.** Run `dbt docs generate` in CI and push the site to GitHub Pages. Proves you document models, columns, and lineage, which is daily analytics engineering work.
- [ ] **Add a dashboard.** Streamlit or Evidence on top of `fct_daily_prices` and `mart_symbol_summary`: price trend, daily return, and a sector comparison. Deploy it and put the link at the top of the README. Proves the pipeline ends in a decision, not a database file.
- [ ] **Add pytest.** Test `validate_data` with bad rows (nulls, negative price, high below low, duplicates) and test that loading the same data twice does not create duplicate rows. Mock the API so tests do not spend Alpha Vantage calls. Proves you test data quality in code, not only in dbt.

## Make the pipeline look like a job

- [ ] **Split `pipeline.py` into a small package.** Separate modules for extract, validate, load, and config. Proves you can navigate a project that is bigger than one file.
- [ ] **Replace `print` with the `logging` module.** Write a log line per symbol with rows fetched and rows inserted. Proves you know how production jobs are debugged.
- [ ] **Retry failed API calls.** Use a bounded retry with a pause between attempts, then skip the symbol. Proves you design for flaky network calls.
- [ ] **Save the raw API response before parsing it.** Write each JSON payload to a `raw/` folder (or cloud storage) and load from that. Proves you can replay a load without calling the API again.
- [ ] **Run checks on pull requests.** A workflow that runs `pytest` and `dbt build` on every PR, plus a linter (`ruff`). Proves changes are verified before they land.
- [ ] **Alert when the scheduled run fails.** Email or Slack from GitHub Actions when the pipeline or a dbt test fails. Proves you think about operating the job, not only building it.
- [ ] **Stop committing `data.duckdb`.** Move the warehouse to MotherDuck or to a file in cloud storage. Binary files in git do not scale, and this is the design you will defend in an interview.

## Deepen the analytics

- [ ] **Add a second source.** Company overview from Alpha Vantage, or CPI and Treasury yields from FRED. Land it in its own raw table and model it in dbt. Proves you can integrate sources, which is when an intermediate layer starts to earn its place.
- [ ] **Add portfolio-style metrics.** Rolling volatility, max drawdown, and the correlation between symbols, each as a tested dbt model. Proves you can define a metric once and keep it consistent.
- [ ] **Backfill real history.** One successful pipeline run loads about 100 trading days per symbol. Until that is in the warehouse, the moving averages and volatility are not meaningful, and the dashboard will look empty.

## Presentation

- [ ] Open the README with one sentence on what the project does, then the dashboard link and the docs link.
- [ ] Add a short "What I would do differently" section. Interviewers ask this directly.
- [ ] Add a CI status badge once the pull request workflow exists.
- [ ] Keep notes and scratch files out of git. `Miscellanous/ToDo` currently contains a live API key and is not gitignored.

## After this project

One strong project is not a portfolio. Two more, each teaching a different skill:

- [ ] **A cloud warehouse project.** Same modeling ideas on Snowflake or BigQuery free tier: loading from object storage, separate dev and prod schemas, and roles. Proves you have used the tools in most job postings.
- [ ] **A batch orchestration project.** Dagster or Airflow wrapping this pipeline and the dbt build as assets with retries and a run history. Proves you can schedule and observe jobs outside of GitHub Actions.
- [ ] **Optional: a streaming project.** A small Kafka or Redpanda flow (events in, a consumer writing to a table). Only worth it if the jobs you want mention streaming.
