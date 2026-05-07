import pandas as pd
import streamlit as st

from dash_app.config import DATABASE_URL
from dash_app.data import load_food_daily, load_ingredients, load_recipes, load_todos, load_tracker
from dash_app.time_utils import get_browser_context
from dash_app.views.admin import render_admin
from dash_app.views.food import render_food
from dash_app.views.forge import render_forge
from dash_app.views.planning import render_planning
from dash_app.views.today import render_today


st.set_page_config(page_title="The 12-Week Forge", page_icon=":bar_chart:", layout="wide")
st.markdown(
    """
    <style>
      .block-container { padding-top: 1.25rem; padding-bottom: 2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

if not DATABASE_URL:
    st.error("DATABASE_URL is not configured for this app yet.")
    st.stop()

browser_timezone, browser_now = get_browser_context()

try:
    tracker = load_tracker()
except Exception as exc:
    st.error("Could not load Forge data from Postgres.")
    st.exception(exc)
    st.stop()

if tracker.empty:
    st.warning("No Forge rows found in the database.")
    st.stop()

tracker["updated_at_local"] = pd.to_datetime(tracker["updated_at"], utc=True).dt.tz_convert(browser_timezone)

food_daily = pd.DataFrame()
food_daily_error = None
try:
    food_daily = load_food_daily()
except Exception as exc:
    food_daily_error = exc

recipes = pd.DataFrame()
recipe_ingredients = pd.DataFrame()
recipes_error = None
try:
    recipes, recipe_ingredients = load_recipes()
except Exception as exc:
    recipes_error = exc

ingredients = pd.DataFrame()
ingredients_error = None
try:
    ingredients = load_ingredients()
except Exception as exc:
    ingredients_error = exc

todos = pd.DataFrame()
todo_events = pd.DataFrame()
todos_error = None
try:
    todos, todo_events = load_todos()
except Exception as exc:
    todos_error = exc

default_date = min(max(browser_now.date(), tracker["entry_date"].min()), tracker["entry_date"].max())
if default_date not in set(tracker["entry_date"].tolist()):
    default_date = tracker.iloc[-1]["entry_date"]

latest_update = tracker["updated_at_local"].dropna().max()
with st.sidebar:
    st.markdown("## The 12-Week Forge")
    st.caption("Daily operating dashboard")
    if st.button("Refresh data", key="refresh_data", type="tertiary"):
        st.cache_data.clear()
        st.toast("Data refreshed")
        st.rerun()
    section = st.radio(
        "Section",
        ["Home", "Forge", "Food", "Planning", "Raw data"],
        index=0,
        label_visibility="collapsed",
    )
    st.divider()
    selected_date = st.date_input(
        "Date",
        value=default_date,
        min_value=tracker["entry_date"].min(),
        max_value=tracker["entry_date"].max(),
        key="global_date",
    )
    selected_match = tracker.loc[tracker["entry_date"] == selected_date]
    selected_row = selected_match.iloc[0] if not selected_match.empty else tracker.iloc[-1]
    food_match = food_daily.loc[food_daily["entry_date"] == selected_date] if not food_daily.empty else pd.DataFrame()
    food_row = food_match.iloc[0] if not food_match.empty else None

    st.markdown("#### At a glance")
    required_checks = 8 + (1 if selected_row.get("scale_available") is True else 0)
    checks_done = min(int(selected_row["completed_checks"] or 0), required_checks)
    st.progress(checks_done / required_checks, text=f"Forge checks: {checks_done}/{required_checks}")
    st.metric("Strikes", int(selected_row["strikes_today"] or 0))
    if pd.notna(selected_row.get("weight")):
        weight_unit = selected_row.get("weight_unit") if pd.notna(selected_row.get("weight_unit")) else "kg"
        st.metric("Weight", f"{selected_row['weight']:.2f} {weight_unit}")
    if food_row is not None:
        st.metric("Protein", f"{food_row['protein_g']:.1f} g", f"{food_row['protein_remaining_g']:.1f} g left")
        st.metric("Water", f"{food_row['water_liters']:.2f} L", f"{food_row['water_remaining_liters']:.2f} L left")
    else:
        st.caption("No food row for selected date")
    st.divider()
    st.caption(f"Timezone: {browser_timezone}")
    if pd.notna(latest_update):
        st.caption(f"Updated: {latest_update.strftime('%Y-%m-%d %H:%M %Z')}")

if section == "Home":
    render_today(tracker, food_daily, todos, browser_timezone, selected_date)
elif section == "Forge":
    render_forge(tracker, selected_date, food_daily)
elif section == "Food":
    render_food(
        food_daily,
        food_daily_error,
        recipes,
        recipe_ingredients,
        recipes_error,
        ingredients,
        ingredients_error,
        browser_timezone,
    )
elif section == "Planning":
    render_planning(todos, todo_events, todos_error, browser_timezone)
else:
    render_admin(
        tracker,
        food_daily,
        food_daily_error,
        recipes,
        recipe_ingredients,
        recipes_error,
        todos,
        todo_events,
        todos_error,
        ingredients,
        ingredients_error,
    )
