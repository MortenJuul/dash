import os
from datetime import date, datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import psycopg
import streamlit as st
from dotenv import load_dotenv
from psycopg.rows import dict_row
from streamlit_js_eval import streamlit_js_eval


load_dotenv()


def read_secret_file(path: str) -> str:
    if not path:
        return ""
    try:
        with open(path, encoding="utf-8") as secret_file:
            return secret_file.read().strip()
    except OSError:
        return ""

st.set_page_config(page_title="The 12-Week Forge", page_icon=":bar_chart:", layout="wide")

DATABASE_URL = os.getenv("DATABASE_URL") or read_secret_file(os.getenv("DATABASE_URL_FILE", ""))
CHALLENGE_START = date(2026, 5, 4)
CHALLENGE_END = date(2026, 7, 26)
REVIEW_GATES = [date(2026, 5, 31), date(2026, 6, 28), date(2026, 7, 26)]
STEP_GOAL = 8_000
PROTEIN_GOAL_G = 150
HYDRATION_GOAL_L = 3.0


@st.cache_data(ttl=60)
def load_tracker() -> pd.DataFrame:
    with psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                  entry_date,
                  week_no,
                  block_no,
                  day_name,
                  planned_session,
                  workout_done,
                  steps_count,
                  steps_goal_hit,
                  protein_g,
                  protein_goal_hit,
                  no_snacks_or_grazing,
                  food_logged,
                  water_liters,
                  hydration_goal_hit,
                  creatine_taken,
                  progress_photo,
                  scale_available,
                  weigh_in,
                  weight,
                  weight_unit,
                  strikes_today,
                  cumulative_strikes,
                  completed_checks,
                  notes,
                  updated_at
                from challenge.forge_daily_status
                order by entry_date
                """
            )
            rows = cur.fetchall()
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["entry_date"] = pd.to_datetime(frame["entry_date"]).dt.date
    return frame


@st.cache_data(ttl=60)
def load_food_daily() -> pd.DataFrame:
    with psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                  entry_date,
                  calories_target,
                  protein_target_g,
                  fat_target_g,
                  carbs_target_g,
                  fiber_target_g_low,
                  fiber_target_g_high,
                  water_target_liters,
                  calories,
                  protein_g,
                  fat_g,
                  carbs_g,
                  fiber_g,
                  water_liters,
                  calories_remaining,
                  protein_remaining_g,
                  fat_remaining_g,
                  carbs_remaining_g,
                  fiber_remaining_g_low,
                  fiber_remaining_g_high,
                  water_remaining_liters,
                  calories_pct,
                  protein_pct,
                  fat_pct,
                  carbs_pct,
                  water_pct,
                  entries_markdown,
                  source_file,
                  updated_at
                from challenge.food_daily_status
                order by entry_date
                """
            )
            rows = cur.fetchall()
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["entry_date"] = pd.to_datetime(frame["entry_date"]).dt.date
    return frame


@st.cache_data(ttl=60)
def load_recipes() -> tuple[pd.DataFrame, pd.DataFrame]:
    with psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                  recipe_key,
                  recipe_name,
                  category,
                  total_amount_g,
                  calories,
                  protein_g,
                  fat_g,
                  carbs_g,
                  fiber_g,
                  notes,
                  tags,
                  updated_at
                from challenge.recipe_summaries_status
                order by recipe_name
                """
            )
            recipe_rows = cur.fetchall()
            cur.execute(
                """
                select
                  recipe_key,
                  recipe_name,
                  category,
                  sort_order,
                  ingredient_key,
                  product_name,
                  brand,
                  amount_g,
                  calories,
                  protein_g,
                  fat_g,
                  carbs_g,
                  fiber_g,
                  notes,
                  tags,
                  updated_at
                from challenge.recipe_ingredients_status
                order by recipe_name, sort_order, product_name
                """
            )
            ingredient_rows = cur.fetchall()
    return pd.DataFrame(recipe_rows), pd.DataFrame(ingredient_rows)


@st.cache_data(ttl=60)
def load_ingredients() -> pd.DataFrame:
    with psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                  ingredient_key,
                  product_name,
                  brand,
                  label_serving_text,
                  label_serving_g,
                  regular_portion_g,
                  calories_per_100g,
                  protein_g_per_100g,
                  fat_g_per_100g,
                  carbs_g_per_100g,
                  fiber_g_per_100g,
                  sugar_g_per_100g,
                  sodium_mg_per_100g,
                  nicknames,
                  source_kind,
                  source_detail,
                  notes,
                  updated_at
                from challenge.ingredients_status
                order by coalesce(brand, ''), product_name
                """
            )
            rows = cur.fetchall()
    return pd.DataFrame(rows)


@st.cache_data(ttl=60)
def load_todos() -> tuple[pd.DataFrame, pd.DataFrame]:
    with psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                  task_key,
                  title,
                  status,
                  priority,
                  area,
                  due_date,
                  tags,
                  notes,
                  source_file,
                  created_at,
                  updated_at,
                  completed_at,
                  is_open,
                  is_overdue
                from challenge.todos_status
                order by is_open desc, is_overdue desc, due_date nulls last, title
                """
            )
            todo_rows = cur.fetchall()
            cur.execute(
                """
                select
                  event_key,
                  task_key,
                  title,
                  event_type,
                  event_at,
                  details,
                  source_file,
                  status,
                  priority,
                  area
                from challenge.todo_events_status
                order by event_at desc, event_key desc
                """
            )
            event_rows = cur.fetchall()
    return pd.DataFrame(todo_rows), pd.DataFrame(event_rows)


def get_browser_context() -> tuple[str, datetime]:
    browser_timezone = streamlit_js_eval(
        js_expressions="Intl.DateTimeFormat().resolvedOptions().timeZone",
        key="browser_timezone",
    ) or "UTC"
    browser_now_iso = streamlit_js_eval(
        js_expressions="new Date().toISOString()",
        key="browser_now_iso",
    )

    try:
        tzinfo = ZoneInfo(browser_timezone)
    except Exception:
        browser_timezone = "UTC"
        tzinfo = ZoneInfo("UTC")

    if browser_now_iso:
        try:
            browser_now = datetime.fromisoformat(browser_now_iso.replace("Z", "+00:00")).astimezone(tzinfo)
        except ValueError:
            browser_now = datetime.now(timezone.utc).astimezone(tzinfo)
    else:
        browser_now = datetime.now(timezone.utc).astimezone(tzinfo)

    return browser_timezone, browser_now


def save_entry(payload: dict[str, Any]) -> None:
    steps_count = payload.get("steps_count")
    protein_g = payload.get("protein_g")
    water_liters = payload.get("water_liters")
    scale_available = payload.get("scale_available")
    weigh_in = payload.get("weigh_in") if scale_available else None
    weight = payload.get("weight") if scale_available and weigh_in else None

    steps_goal_hit = steps_count is not None and steps_count >= STEP_GOAL
    protein_goal_hit = protein_g is not None and protein_g >= PROTEIN_GOAL_G
    hydration_goal_hit = water_liters is not None and water_liters >= HYDRATION_GOAL_L

    strike_checks = [
        payload.get("workout_done"),
        steps_goal_hit,
        protein_goal_hit,
        payload.get("no_snacks_or_grazing"),
        payload.get("food_logged"),
        hydration_goal_hit,
        payload.get("creatine_taken"),
        payload.get("progress_photo"),
    ]
    strikes_today = sum(value is False for value in strike_checks)
    if scale_available and weigh_in is False:
        strikes_today += 1

    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update challenge.forge_daily
                set
                  workout_done = %(workout_done)s,
                  steps_count = %(steps_count)s,
                  steps_goal_hit = %(steps_goal_hit)s,
                  protein_g = %(protein_g)s,
                  protein_goal_hit = %(protein_goal_hit)s,
                  no_snacks_or_grazing = %(no_snacks_or_grazing)s,
                  food_logged = %(food_logged)s,
                  water_liters = %(water_liters)s,
                  hydration_goal_hit = %(hydration_goal_hit)s,
                  creatine_taken = %(creatine_taken)s,
                  progress_photo = %(progress_photo)s,
                  scale_available = %(scale_available)s,
                  weigh_in = %(weigh_in)s,
                  weight = %(weight)s,
                  weight_unit = %(weight_unit)s,
                  strikes_today = %(strikes_today)s,
                  notes = %(notes)s
                where entry_date = %(entry_date)s
                """,
                {
                    **payload,
                    "steps_goal_hit": steps_goal_hit,
                    "protein_goal_hit": protein_goal_hit,
                    "hydration_goal_hit": hydration_goal_hit,
                    "weigh_in": weigh_in,
                    "weight": weight,
                    "strikes_today": strikes_today,
                    "weight_unit": payload.get("weight_unit") if weight is not None else None,
                },
            )
            cur.execute(
                """
                with running as (
                  select
                    entry_date,
                    sum(coalesce(strikes_today, 0)) over (order by entry_date) as cumulative_strikes
                  from challenge.forge_daily
                )
                update challenge.forge_daily d
                set cumulative_strikes = r.cumulative_strikes
                from running r
                where d.entry_date = r.entry_date
                """
            )
    load_tracker.clear()
    load_food_daily.clear()
    load_recipes.clear()


def bool_icon(value: Any) -> str:
    if value is True:
        return "✅"
    if value is False:
        return "❌"
    return "—"


def format_status(value: bool | None, good: str, bad: str, unknown: str = "Not logged") -> str:
    if value is True:
        return good
    if value is False:
        return bad
    return unknown


def render_food_chart(frame: pd.DataFrame, series: list[str], title: str) -> alt.Chart:
    chart_frame = frame.reset_index()[["entry_date", *series]].copy()
    chart_frame["entry_date"] = pd.to_datetime(chart_frame["entry_date"])
    chart_frame = chart_frame.sort_values("entry_date", ascending=True)

    for column in series:
        chart_frame[column] = pd.to_numeric(chart_frame[column], errors="coerce")

    melted = chart_frame.melt("entry_date", var_name="series", value_name="value")
    value_min = melted["value"].min(skipna=True)
    value_max = melted["value"].max(skipna=True)

    if pd.isna(value_min) or pd.isna(value_max):
        value_min, value_max = 0.0, 1.0
    elif value_min == value_max:
        padding = max(abs(value_min) * 0.1, 1.0)
        value_min -= padding
        value_max += padding
    else:
        padding = (value_max - value_min) * 0.08
        value_min -= padding
        value_max += padding

    base = alt.Chart(melted).encode(
        x=alt.X("entry_date:T", title="Date", sort="ascending"),
        y=alt.Y(
            "value:Q",
            title=None,
            scale=alt.Scale(domain=[float(value_min), float(value_max)], reverse=False, nice=False, zero=False),
        ),
        color=alt.Color("series:N", title=None),
        detail="series:N",
        tooltip=[
            alt.Tooltip("yearmonthdate(entry_date):T", title="Date"),
            alt.Tooltip("series:N", title="Series"),
            alt.Tooltip("value:Q", title="Value", format=".2f"),
        ],
    )

    line = base.transform_filter("isValid(datum.value)").mark_line(point=True)

    return line.properties(height=260, title=title)


def challenge_day(selected_date: date) -> int:
    return (selected_date - CHALLENGE_START).days + 1


browser_timezone, browser_now = get_browser_context()

st.title("The 12-Week Forge")
st.caption("Dashboard gremlin online. Track the challenge, log the day, and watch the strike counter like it owes you money.")

if not DATABASE_URL:
    st.error("DATABASE_URL is not configured for this app yet.")
    st.stop()

try:
    tracker = load_tracker()
except Exception as exc:
    st.error("Could not load Forge data from Postgres.")
    st.exception(exc)
    st.stop()

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

if tracker.empty:
    st.warning("No Forge rows found in the database.")
    st.stop()

tracker["updated_at_local"] = pd.to_datetime(tracker["updated_at"], utc=True).dt.tz_convert(browser_timezone)

total_strikes = int(tracker["strikes_today"].fillna(0).sum())
logged_mask = tracker[
    [
        "workout_done",
        "steps_count",
        "protein_g",
        "no_snacks_or_grazing",
        "food_logged",
        "water_liters",
        "creatine_taken",
        "progress_photo",
        "scale_available",
        "weigh_in",
        "notes",
    ]
].notna().any(axis=1)
days_logged = int(logged_mask.sum())
days_complete = int((tracker["completed_checks"].fillna(0) >= 8).sum())
default_date = min(max(browser_now.date(), CHALLENGE_START), CHALLENGE_END)
current_row_df = tracker.loc[tracker["entry_date"] == default_date]
if current_row_df.empty:
    current_row_df = tracker.iloc[[0]]
current_row = current_row_df.iloc[0]

status_text = "Failed" if total_strikes >= 3 else "Live"
status_delta = f"{3 - total_strikes} strikes left" if total_strikes < 3 else "Strike cap reached"

with st.sidebar:
    st.header("Challenge status")
    st.caption(f"Browser timezone: {browser_timezone}")
    st.metric("Status", status_text, status_delta)
    st.metric("Total strikes", total_strikes)
    st.metric("Days fully clean", days_complete)
    st.metric("Current week", int(current_row["week_no"]))
    st.markdown("### Review gates")
    for gate in REVIEW_GATES:
        st.write(f"- {gate.isoformat()}")

left, mid, right, far_right = st.columns(4)
left.metric("Today", current_row["entry_date"].isoformat())
mid.metric("Challenge day", challenge_day(current_row["entry_date"]))
right.metric("Planned session", current_row["planned_session"])
far_right.metric("Days logged", days_logged)

last_updated_local = tracker["updated_at_local"].dropna().max()
if pd.notna(last_updated_local):
    st.caption(f"Latest DB update shown in your browser time: {last_updated_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")

selected_date = st.date_input(
    "Log / review date",
    value=current_row["entry_date"],
    min_value=CHALLENGE_START,
    max_value=CHALLENGE_END,
)
selected_row = tracker.loc[tracker["entry_date"] == selected_date].iloc[0]

st.info(
    f"Week {int(selected_row['week_no'])}, Block {int(selected_row['block_no'])}, {selected_row['day_name']} — {selected_row['planned_session']}"
)

tab_log, tab_week, tab_trends, tab_food, tab_meals, tab_todos, tab_ingredients, tab_data = st.tabs(["Daily check-in", "Week view", "Trends", "Food", "Meals", "Todos", "Ingredients", "Raw data"])

with tab_log:
    with st.form("forge-daily-checkin"):
        c1, c2 = st.columns(2)
        with c1:
            workout_done = st.checkbox(
                "Scheduled workout / recovery done",
                value=bool(selected_row["workout_done"]) if pd.notna(selected_row["workout_done"]) else False,
            )
            steps_count = st.number_input(
                "Steps",
                min_value=0,
                max_value=100000,
                value=int(selected_row["steps_count"]) if pd.notna(selected_row["steps_count"]) else 0,
                step=500,
            )
            protein_g = st.number_input(
                "Protein (g)",
                min_value=0.0,
                max_value=500.0,
                value=float(selected_row["protein_g"]) if pd.notna(selected_row["protein_g"]) else 0.0,
                step=5.0,
            )
            water_liters = st.number_input(
                "Water (L)",
                min_value=0.0,
                max_value=10.0,
                value=float(selected_row["water_liters"]) if pd.notna(selected_row["water_liters"]) else 0.0,
                step=0.25,
            )
        with c2:
            no_snacks_or_grazing = st.checkbox(
                "No candy / snacks / grazing",
                value=bool(selected_row["no_snacks_or_grazing"]) if pd.notna(selected_row["no_snacks_or_grazing"]) else False,
            )
            food_logged = st.checkbox(
                "Food fully logged",
                value=bool(selected_row["food_logged"]) if pd.notna(selected_row["food_logged"]) else False,
            )
            creatine_taken = st.checkbox(
                "Creatine taken",
                value=bool(selected_row["creatine_taken"]) if pd.notna(selected_row["creatine_taken"]) else False,
            )
            progress_photo = st.checkbox(
                "Progress photo taken",
                value=bool(selected_row["progress_photo"]) if pd.notna(selected_row["progress_photo"]) else False,
            )

        st.markdown("### Scale / weigh-in")
        scale_available = st.checkbox(
            "Scale available today",
            value=bool(selected_row["scale_available"]) if pd.notna(selected_row["scale_available"]) else False,
        )
        weigh_in = st.checkbox(
            "Weighed in",
            value=bool(selected_row["weigh_in"]) if pd.notna(selected_row["weigh_in"]) else False,
            disabled=not scale_available,
        )
        weight = st.number_input(
            "Body weight",
            min_value=0.0,
            max_value=1000.0,
            value=float(selected_row["weight"]) if pd.notna(selected_row["weight"]) else 0.0,
            step=0.1,
            disabled=not (scale_available and weigh_in),
        )
        weight_unit = st.selectbox(
            "Weight unit",
            options=["lb", "kg"],
            index=0 if selected_row.get("weight_unit") != "kg" else 1,
            disabled=not (scale_available and weigh_in),
        )
        notes = st.text_area("Notes", value=selected_row["notes"] or "", height=120)

        submitted = st.form_submit_button("Save day")

    if submitted:
        save_entry(
            {
                "entry_date": selected_date,
                "workout_done": workout_done,
                "steps_count": int(steps_count),
                "protein_g": float(protein_g),
                "no_snacks_or_grazing": no_snacks_or_grazing,
                "food_logged": food_logged,
                "water_liters": float(water_liters),
                "creatine_taken": creatine_taken,
                "progress_photo": progress_photo,
                "scale_available": scale_available,
                "weigh_in": weigh_in,
                "weight": float(weight),
                "weight_unit": weight_unit,
                "notes": notes.strip() or None,
            }
        )
        st.success("Saved. The gremlin fed the database.")
        st.rerun()

    if pd.notna(selected_row["updated_at_local"]):
        st.caption(
            f"Last saved for this day: {selected_row['updated_at_local'].strftime('%Y-%m-%d %H:%M:%S %Z')}"
        )

    summary_cols = st.columns(5)
    summary_cols[0].metric("Workout", format_status(selected_row["workout_done"], "Done", "Missed"))
    summary_cols[1].metric("Steps", format_status(selected_row["steps_goal_hit"], "8k hit", "Under 8k"))
    summary_cols[2].metric("Protein", format_status(selected_row["protein_goal_hit"], "150g hit", "Under 150g"))
    summary_cols[3].metric("Hydration", format_status(selected_row["hydration_goal_hit"], "3 L hit", "Under 3 L"))
    summary_cols[4].metric("Strikes today", int(selected_row["strikes_today"] or 0))

with tab_week:
    week_df = tracker.loc[tracker["week_no"] == selected_row["week_no"]].copy()
    display = week_df[
        [
            "entry_date",
            "day_name",
            "planned_session",
            "workout_done",
            "steps_goal_hit",
            "protein_goal_hit",
            "food_logged",
            "hydration_goal_hit",
            "creatine_taken",
            "progress_photo",
            "strikes_today",
            "cumulative_strikes",
            "updated_at_local",
        ]
    ].copy()
    for col in [
        "workout_done",
        "steps_goal_hit",
        "protein_goal_hit",
        "food_logged",
        "hydration_goal_hit",
        "creatine_taken",
        "progress_photo",
    ]:
        display[col] = display[col].map(bool_icon)
    display["updated_at_local"] = display["updated_at_local"].apply(
        lambda value: value.strftime('%Y-%m-%d %H:%M:%S %Z') if pd.notna(value) else '—'
    )
    st.dataframe(display, use_container_width=True, hide_index=True)

with tab_trends:
    chart_df = tracker.copy()
    chart_df = chart_df.set_index("entry_date")
    st.markdown("### Weight")
    if chart_df["weight"].notna().any():
        st.line_chart(chart_df[["weight"]])
    else:
        st.caption("No weigh-ins logged yet.")

    trend_left, trend_right = st.columns(2)
    with trend_left:
        st.markdown("### Protein / water")
        st.line_chart(chart_df[["protein_g", "water_liters"]])
    with trend_right:
        st.markdown("### Strikes")
        st.line_chart(chart_df[["strikes_today", "cumulative_strikes"]].fillna(0))

with tab_food:
    st.markdown("### Food daily totals")
    if food_daily_error is not None:
        st.warning("Food tab data is unavailable right now.")
        st.caption(str(food_daily_error))
    elif food_daily.empty:
        st.caption("No food rows synced yet.")
    else:
        food_daily = food_daily.copy()
        food_daily["updated_at_local"] = pd.to_datetime(food_daily["updated_at"], utc=True).dt.tz_convert(browser_timezone)
        food_daily = food_daily.set_index("entry_date")
        latest_food = food_daily.iloc[-1]

        st.caption(f"Latest logged day: {food_daily.index[-1]}")

        food_metrics = st.columns(5)
        food_metrics[0].metric(
            "Calories",
            f"{int(latest_food['calories'])} / {int(latest_food['calories_target'])} kcal" if pd.notna(latest_food["calories"]) and pd.notna(latest_food["calories_target"]) else "—",
            f"{int(latest_food['calories_remaining'])} left" if pd.notna(latest_food["calories_remaining"]) else None,
        )
        food_metrics[1].metric(
            "Protein",
            f"{latest_food['protein_g']:.1f} / {latest_food['protein_target_g']:.1f} g" if pd.notna(latest_food["protein_g"]) and pd.notna(latest_food["protein_target_g"]) else "—",
            f"{latest_food['protein_remaining_g']:.1f} g left" if pd.notna(latest_food["protein_remaining_g"]) else None,
        )
        food_metrics[2].metric(
            "Fat",
            f"{latest_food['fat_g']:.1f} / {latest_food['fat_target_g']:.1f} g" if pd.notna(latest_food["fat_g"]) and pd.notna(latest_food["fat_target_g"]) else "—",
            f"{latest_food['fat_remaining_g']:.1f} g left" if pd.notna(latest_food["fat_remaining_g"]) else None,
        )
        food_metrics[3].metric(
            "Carbs",
            f"{latest_food['carbs_g']:.1f} / {latest_food['carbs_target_g']:.1f} g" if pd.notna(latest_food["carbs_g"]) and pd.notna(latest_food["carbs_target_g"]) else "—",
            f"{latest_food['carbs_remaining_g']:.1f} g left" if pd.notna(latest_food["carbs_remaining_g"]) else None,
        )
        food_metrics[4].metric(
            "Water",
            f"{latest_food['water_liters']:.2f} / {latest_food['water_target_liters']:.2f} L" if pd.notna(latest_food["water_liters"]) and pd.notna(latest_food["water_target_liters"]) else "—",
            f"{latest_food['water_remaining_liters']:.2f} L left" if pd.notna(latest_food["water_remaining_liters"]) else None,
        )

        calories_chart = food_daily[["calories", "calories_target"]].copy()
        calories_chart.loc[calories_chart["calories"].isna(), "calories_target"] = pd.NA

        macros_chart = food_daily[["protein_g", "fat_g", "carbs_g", "fiber_g"]].copy()

        water_chart = food_daily[["water_liters", "water_target_liters"]].copy()
        water_chart.loc[water_chart["water_liters"].isna(), "water_target_liters"] = pd.NA

        chart_left, chart_right = st.columns(2)
        with chart_left:
            st.altair_chart(render_food_chart(calories_chart, ["calories", "calories_target"], "Calories"), use_container_width=True)
        with chart_right:
            st.altair_chart(render_food_chart(macros_chart, ["protein_g", "fat_g", "carbs_g", "fiber_g"], "Macros"), use_container_width=True)

        st.altair_chart(render_food_chart(water_chart, ["water_liters", "water_target_liters"], "Water"), use_container_width=True)

        recent_food = food_daily.reset_index().copy()
        recent_food = recent_food.sort_values("entry_date", ascending=False)
        recent_food["entry_date"] = recent_food["entry_date"].astype(str)
        recent_food["updated_at_local"] = recent_food["updated_at_local"].apply(
            lambda value: value.strftime('%Y-%m-%d %H:%M:%S %Z') if pd.notna(value) else '—'
        )
        st.markdown("### Recent food log rollup")
        st.dataframe(
            recent_food[[
                "entry_date",
                "calories",
                "protein_g",
                "fat_g",
                "carbs_g",
                "fiber_g",
                "water_liters",
                "calories_target",
                "protein_target_g",
                "water_target_liters",
                "updated_at_local",
            ]],
            use_container_width=True,
            hide_index=True,
        )

        latest_entries = latest_food.get("entries_markdown")
        if latest_entries:
            with st.expander("Latest day entry details"):
                st.markdown(latest_entries)

with tab_meals:
    st.markdown("### Saved recipes")
    if recipes_error is not None:
        st.warning("Meals tab data is unavailable right now.")
        st.caption(str(recipes_error))
    elif recipes.empty:
        st.caption("No saved recipes yet.")
    else:
        recipes_view = recipes.copy()
        recipes_view["updated_at_local"] = pd.to_datetime(recipes_view["updated_at"], utc=True).dt.tz_convert(browser_timezone)

        top_cols = st.columns(4)
        top_cols[0].metric("Saved recipes", len(recipes_view))
        top_cols[1].metric("Avg protein", f"{recipes_view['protein_g'].fillna(0).mean():.1f} g")
        top_cols[2].metric("Avg calories", f"{recipes_view['calories'].fillna(0).mean():.0f} kcal")
        top_cols[3].metric("Latest update", recipes_view['updated_at_local'].max().strftime('%Y-%m-%d'))

        table = recipes_view[[
            "recipe_name",
            "category",
            "total_amount_g",
            "calories",
            "protein_g",
            "fat_g",
            "carbs_g",
            "fiber_g",
            "tags",
            "updated_at_local",
        ]].copy()
        table["tags"] = table["tags"].apply(lambda values: ", ".join(values or []))
        table["updated_at_local"] = table["updated_at_local"].apply(
            lambda value: value.strftime('%Y-%m-%d %H:%M:%S %Z') if pd.notna(value) else '—'
        )
        st.dataframe(table, use_container_width=True, hide_index=True)

        recipe_names = recipes_view["recipe_name"].tolist()
        selected_recipe_name = st.selectbox("Recipe details", recipe_names, key="recipe_select")
        selected_recipe = recipes_view.loc[recipes_view["recipe_name"] == selected_recipe_name].iloc[0]
        selected_recipe_ingredients = recipe_ingredients.loc[
            recipe_ingredients["recipe_key"] == selected_recipe["recipe_key"]
        ].copy()

        detail_cols = st.columns(6)
        detail_cols[0].metric("Total grams", f"{selected_recipe['total_amount_g']:.1f} g" if pd.notna(selected_recipe["total_amount_g"]) else "—")
        detail_cols[1].metric("Calories", f"{selected_recipe['calories']:.0f}" if pd.notna(selected_recipe["calories"]) else "—")
        detail_cols[2].metric("Protein", f"{selected_recipe['protein_g']:.1f} g" if pd.notna(selected_recipe["protein_g"]) else "—")
        detail_cols[3].metric("Fat", f"{selected_recipe['fat_g']:.1f} g" if pd.notna(selected_recipe["fat_g"]) else "—")
        detail_cols[4].metric("Carbs", f"{selected_recipe['carbs_g']:.1f} g" if pd.notna(selected_recipe["carbs_g"]) else "—")
        detail_cols[5].metric("Fiber", f"{selected_recipe['fiber_g']:.1f} g" if pd.notna(selected_recipe["fiber_g"]) else "—")

        if selected_recipe.get("notes"):
            st.caption(selected_recipe["notes"])
        if not selected_recipe_ingredients.empty:
            ingredient_table = selected_recipe_ingredients[[
                "sort_order",
                "product_name",
                "brand",
                "amount_g",
                "calories",
                "protein_g",
                "fat_g",
                "carbs_g",
                "fiber_g",
                "notes",
            ]].copy()
            st.markdown("#### Recipe ingredients")
            st.dataframe(ingredient_table, use_container_width=True, hide_index=True)

with tab_todos:
    st.markdown("### Todo system")
    if todos_error is not None:
        st.warning("Todo data is unavailable right now.")
        st.caption(str(todos_error))
    elif todos.empty:
        st.caption("No todo rows synced yet.")
    else:
        todos_view = todos.copy()
        todos_view["created_at_local"] = pd.to_datetime(todos_view["created_at"], utc=True, errors="coerce").dt.tz_convert(browser_timezone)
        todos_view["updated_at_local"] = pd.to_datetime(todos_view["updated_at"], utc=True, errors="coerce").dt.tz_convert(browser_timezone)
        todos_view["completed_at_local"] = pd.to_datetime(todos_view["completed_at"], utc=True, errors="coerce").dt.tz_convert(browser_timezone)

        top_cols = st.columns(5)
        top_cols[0].metric("Open", int(todos_view["is_open"].fillna(False).sum()))
        top_cols[1].metric("In progress", int((todos_view["status"] == "in_progress").sum()))
        top_cols[2].metric("Blocked", int((todos_view["status"] == "blocked").sum()))
        top_cols[3].metric("Done", int((todos_view["status"] == "done").sum()))
        top_cols[4].metric("Overdue", int(todos_view["is_overdue"].fillna(False).sum()))

        todo_table = todos_view[[
            "title",
            "status",
            "priority",
            "area",
            "due_date",
            "tags",
            "is_overdue",
            "updated_at_local",
        ]].copy()
        todo_table["tags"] = todo_table["tags"].apply(lambda values: ", ".join(values or []))
        todo_table["is_overdue"] = todo_table["is_overdue"].map(lambda value: "⚠️" if value else "")
        todo_table["updated_at_local"] = todo_table["updated_at_local"].apply(
            lambda value: value.strftime('%Y-%m-%d %H:%M:%S %Z') if pd.notna(value) else '—'
        )
        st.dataframe(todo_table, use_container_width=True, hide_index=True)

        todo_titles = todos_view["title"].tolist()
        selected_todo_title = st.selectbox("Todo details", todo_titles, key="todo_select")
        selected_todo = todos_view.loc[todos_view["title"] == selected_todo_title].iloc[0]
        selected_events = todo_events.loc[todo_events["task_key"] == selected_todo["task_key"]].copy() if not todo_events.empty else pd.DataFrame()

        detail_cols = st.columns(5)
        detail_cols[0].metric("Status", selected_todo["status"])
        detail_cols[1].metric("Priority", selected_todo["priority"] or "—")
        detail_cols[2].metric("Area", selected_todo["area"] or "—")
        detail_cols[3].metric("Due", str(selected_todo["due_date"]) if pd.notna(selected_todo["due_date"]) else "—")
        detail_cols[4].metric("Overdue", "Yes" if bool(selected_todo["is_overdue"]) else "No")

        tags = selected_todo.get("tags") or []
        if tags:
            st.caption(f"Tags: {', '.join(tags)}")
        if selected_todo.get("notes"):
            st.caption(selected_todo["notes"])
        if not selected_events.empty:
            selected_events["event_at_local"] = pd.to_datetime(selected_events["event_at"], utc=True, errors="coerce").dt.tz_convert(browser_timezone)
            selected_events["event_at_local"] = selected_events["event_at_local"].apply(
                lambda value: value.strftime('%Y-%m-%d %H:%M:%S %Z') if pd.notna(value) else '—'
            )
            st.markdown("#### Recent task events")
            st.dataframe(
                selected_events[["event_at_local", "event_type", "details"]],
                use_container_width=True,
                hide_index=True,
            )

with tab_ingredients:
    st.markdown("### Ingredient catalog")
    if ingredients_error is not None:
        st.warning("Ingredients tab data is unavailable right now.")
        st.caption(str(ingredients_error))
    elif ingredients.empty:
        st.caption("No ingredient records yet.")
    else:
        ingredients_view = ingredients.copy()
        ingredients_view["updated_at_local"] = pd.to_datetime(ingredients_view["updated_at"], utc=True).dt.tz_convert(browser_timezone)

        top_cols = st.columns(4)
        top_cols[0].metric("Ingredients", len(ingredients_view))
        top_cols[1].metric("With nicknames", int(ingredients_view["nicknames"].apply(lambda values: len(values or []) > 0).sum()))
        top_cols[2].metric("Brands", ingredients_view["brand"].fillna("Unknown").nunique())
        top_cols[3].metric("Latest update", ingredients_view["updated_at_local"].max().strftime('%Y-%m-%d'))

        ingredient_table = ingredients_view[[
            "product_name",
            "brand",
            "label_serving_text",
            "label_serving_g",
            "regular_portion_g",
            "calories_per_100g",
            "protein_g_per_100g",
            "fat_g_per_100g",
            "carbs_g_per_100g",
            "fiber_g_per_100g",
            "nicknames",
            "source_kind",
            "updated_at_local",
        ]].copy()
        ingredient_table["nicknames"] = ingredient_table["nicknames"].apply(lambda values: ", ".join(values or []))
        ingredient_table["updated_at_local"] = ingredient_table["updated_at_local"].apply(
            lambda value: value.strftime('%Y-%m-%d %H:%M:%S %Z') if pd.notna(value) else '—'
        )
        st.dataframe(ingredient_table, use_container_width=True, hide_index=True)

        ingredient_labels = ingredients_view.apply(
            lambda row: f"{row['product_name']} ({row['brand']})" if pd.notna(row['brand']) and row['brand'] else row['product_name'],
            axis=1,
        ).tolist()
        selected_ingredient_label = st.selectbox("Ingredient details", ingredient_labels, key="ingredient_select")
        selected_ingredient = ingredients_view.iloc[ingredient_labels.index(selected_ingredient_label)]

        detail_cols = st.columns(6)
        detail_cols[0].metric("Calories / 100g", f"{selected_ingredient['calories_per_100g']:.1f}" if pd.notna(selected_ingredient["calories_per_100g"]) else "—")
        detail_cols[1].metric("Protein / 100g", f"{selected_ingredient['protein_g_per_100g']:.1f} g" if pd.notna(selected_ingredient["protein_g_per_100g"]) else "—")
        detail_cols[2].metric("Fat / 100g", f"{selected_ingredient['fat_g_per_100g']:.1f} g" if pd.notna(selected_ingredient["fat_g_per_100g"]) else "—")
        detail_cols[3].metric("Carbs / 100g", f"{selected_ingredient['carbs_g_per_100g']:.1f} g" if pd.notna(selected_ingredient["carbs_g_per_100g"]) else "—")
        detail_cols[4].metric("Fiber / 100g", f"{selected_ingredient['fiber_g_per_100g']:.1f} g" if pd.notna(selected_ingredient["fiber_g_per_100g"]) else "—")
        detail_cols[5].metric("Sodium / 100g", f"{selected_ingredient['sodium_mg_per_100g']:.0f} mg" if pd.notna(selected_ingredient["sodium_mg_per_100g"]) else "—")

        st.caption(f"Label serving reference: {selected_ingredient['label_serving_text'] or '—'}")
        if pd.notna(selected_ingredient['label_serving_g']):
            st.caption(f"Label serving grams: {selected_ingredient['label_serving_g']:.1f} g")
        if pd.notna(selected_ingredient['regular_portion_g']):
            st.caption(f"Your regular portion: {selected_ingredient['regular_portion_g']:.1f} g")
        nicknames = selected_ingredient.get("nicknames") or []
        if nicknames:
            st.caption(f"Nicknames: {', '.join(nicknames)}")
        source_bits = [selected_ingredient.get("source_kind"), selected_ingredient.get("source_detail")]
        source_text = " — ".join([bit for bit in source_bits if bit])
        if source_text:
            st.caption(f"Source: {source_text}")
        if selected_ingredient.get("notes"):
            st.caption(selected_ingredient["notes"])

with tab_data:
    raw = tracker.copy()
    raw["entry_date"] = raw["entry_date"].astype(str)
    raw["updated_at"] = pd.to_datetime(raw["updated_at"], utc=True).dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    raw["updated_at_local"] = raw["updated_at_local"].apply(
        lambda value: value.strftime('%Y-%m-%d %H:%M:%S %Z') if pd.notna(value) else '—'
    )
    st.markdown("### Forge raw data")
    st.dataframe(raw, use_container_width=True, hide_index=True)

    if food_daily_error is not None:
        st.markdown("### Food raw data")
        st.caption("Unavailable because the food query failed.")
    elif not food_daily.empty:
        food_raw = food_daily.reset_index().copy()
        food_raw["entry_date"] = food_raw["entry_date"].astype(str)
        food_raw["updated_at"] = pd.to_datetime(food_raw["updated_at"], utc=True).dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        st.markdown("### Food raw data")
        st.dataframe(food_raw, use_container_width=True, hide_index=True)

    if recipes_error is not None:
        st.markdown("### Recipe raw data")
        st.caption("Unavailable because the recipe query failed.")
    elif not recipes.empty:
        recipes_raw = recipes.copy()
        recipes_raw["updated_at"] = pd.to_datetime(recipes_raw["updated_at"], utc=True).dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        st.markdown("### Recipe raw data")
        st.dataframe(recipes_raw, use_container_width=True, hide_index=True)
        if not recipe_ingredients.empty:
            recipe_ingredients_raw = recipe_ingredients.copy()
            recipe_ingredients_raw["updated_at"] = pd.to_datetime(recipe_ingredients_raw["updated_at"], utc=True).dt.strftime('%Y-%m-%d %H:%M:%S UTC')
            st.markdown("### Recipe ingredient raw data")
            st.dataframe(recipe_ingredients_raw, use_container_width=True, hide_index=True)

    if todos_error is not None:
        st.markdown("### Todo raw data")
        st.caption("Unavailable because the todo query failed.")
    elif not todos.empty:
        todos_raw = todos.copy()
        for col in ["created_at", "updated_at", "completed_at"]:
            todos_raw[col] = pd.to_datetime(todos_raw[col], utc=True, errors="coerce").dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        st.markdown("### Todo raw data")
        st.dataframe(todos_raw, use_container_width=True, hide_index=True)
        if not todo_events.empty:
            todo_events_raw = todo_events.copy()
            todo_events_raw["event_at"] = pd.to_datetime(todo_events_raw["event_at"], utc=True, errors="coerce").dt.strftime('%Y-%m-%d %H:%M:%S UTC')
            st.markdown("### Todo event raw data")
            st.dataframe(todo_events_raw, use_container_width=True, hide_index=True)

    if ingredients_error is not None:
        st.markdown("### Ingredient raw data")
        st.caption("Unavailable because the ingredient query failed.")
    elif not ingredients.empty:
        ingredients_raw = ingredients.copy()
        ingredients_raw["updated_at"] = pd.to_datetime(ingredients_raw["updated_at"], utc=True).dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        st.markdown("### Ingredient raw data")
        st.dataframe(ingredients_raw, use_container_width=True, hide_index=True)
