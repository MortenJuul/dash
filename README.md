# Dash

Streamlit dashboard placeholder for the OpenClaw habit dashboard.

## Local Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

`DATABASE_URL` is optional for now. The app runs without a database connection.

## DB helpers

DB-related app assets live in this repo now:

- `db/forge_daily.sql`
- `db/food_daily.sql`
- `scripts/sync_forge_tracker.py`
- `scripts/sync_food_logs.py`

The sync scripts default to Morty’s workspace paths, but can be pointed elsewhere with env vars:

- `FORGE_TRACKER_CSV`
- `FOOD_LOG_DIR`
- `DATABASE_URL` / `FORGE_DATABASE_URL` / `FOOD_DATABASE_URL`
