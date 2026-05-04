import os
from datetime import date, datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

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

tab_log, tab_week, tab_trends, tab_food, tab_data = st.tabs(["Daily check-in", "Week view", "Trends", "Food", "Raw data"])

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

        st.markdown("### Calories")
        st.line_chart(food_daily[["calories", "calories_target"]])

        st.markdown("### Macros")
        st.line_chart(food_daily[["protein_g", "fat_g", "carbs_g", "fiber_g"]])

        st.markdown("### Water")
        st.line_chart(food_daily[["water_liters", "water_target_liters"]])

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
