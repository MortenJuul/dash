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
