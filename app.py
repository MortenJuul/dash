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

st.title("The 12-Week Forge")
st.caption("Today first. Details when needed. Raw tables banished to the basement where they belong.")

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

latest_update = tracker["updated_at_local"].dropna().max()
with st.sidebar:
    st.header("System")
    st.caption(f"Timezone: {browser_timezone}")
    if pd.notna(latest_update):
        st.caption(f"Latest Forge update: {latest_update.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    st.caption("Dash sections are grouped by job-to-be-done, not database table.")

section = st.sidebar.radio(
    "Section",
    ["Today", "Forge", "Food", "Planning", "Admin"],
    index=0,
)

if section == "Today":
    render_today(tracker, food_daily, todos, browser_timezone, browser_now.date())
elif section == "Forge":
    render_forge(tracker)
elif section == "Food":
    render_food(food_daily, food_daily_error, browser_timezone)
elif section == "Planning":
    render_planning(
        todos,
        todo_events,
        todos_error,
        recipes,
        recipe_ingredients,
        recipes_error,
        ingredients,
        ingredients_error,
        browser_timezone,
    )
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
