import pandas as pd
import streamlit as st

from dash_app.config import CHALLENGE_END, CHALLENGE_START, HYDRATION_GOAL_L, PROTEIN_GOAL_G, STEP_GOAL
from dash_app.data import save_forge_entry
from dash_app.formatting import challenge_day, format_local_dt, format_status


def _missing_items(row: pd.Series, latest_food: pd.Series | None, open_todos: pd.DataFrame) -> list[str]:
    items: list[str] = []
    if row.get("workout_done") is not True:
        items.append("Scheduled workout / recovery is not marked done")
    if not bool(row.get("steps_goal_hit")):
        steps = int(row["steps_count"]) if pd.notna(row.get("steps_count")) else 0
        items.append(f"Steps below {STEP_GOAL:,} ({steps:,} logged)")
    if not bool(row.get("protein_goal_hit")):
        protein = float(row["protein_g"]) if pd.notna(row.get("protein_g")) else 0.0
        items.append(f"Forge protein below {PROTEIN_GOAL_G:g} g ({protein:.1f} g logged)")
    if not bool(row.get("hydration_goal_hit")):
        water = float(row["water_liters"]) if pd.notna(row.get("water_liters")) else 0.0
        items.append(f"Forge water below {HYDRATION_GOAL_L:g} L ({water:.2f} L logged)")
    for col, label in [
        ("food_logged", "Food is not marked fully logged"),
        ("creatine_taken", "Creatine is not marked taken"),
        ("progress_photo", "Progress photo is not marked taken"),
    ]:
        if row.get(col) is not True:
            items.append(label)
    if bool(row.get("scale_available")) and row.get("weigh_in") is not True:
        items.append("Scale is available, but weigh-in is not marked done")
    if latest_food is not None and pd.notna(latest_food.get("protein_remaining_g")) and latest_food["protein_remaining_g"] > 0:
        items.append(f"Food log protein remaining: {latest_food['protein_remaining_g']:.1f} g")
    if latest_food is not None and pd.notna(latest_food.get("water_remaining_liters")) and latest_food["water_remaining_liters"] > 0:
        items.append(f"Food log water remaining: {latest_food['water_remaining_liters']:.2f} L")
    if not open_todos.empty:
        overdue_count = int(open_todos["is_overdue"].fillna(False).sum())
        if overdue_count:
            items.append(f"{overdue_count} overdue todo(s)")
    return items


def render_today(
    tracker: pd.DataFrame,
    food_daily: pd.DataFrame,
    todos: pd.DataFrame,
    browser_timezone: str,
    browser_today,
) -> None:
    st.subheader("Today")
    st.caption("Command center: what matters now, then the details if you need them.")

    default_date = min(max(browser_today, CHALLENGE_START), CHALLENGE_END)
    available_dates = set(tracker["entry_date"].tolist())
    if default_date not in available_dates:
        default_date = tracker.iloc[-1]["entry_date"]

    selected_date = st.date_input(
        "Review / update date",
        value=default_date,
        min_value=CHALLENGE_START,
        max_value=CHALLENGE_END,
        key="today_date",
    )
    selected_match = tracker.loc[tracker["entry_date"] == selected_date]
    if selected_match.empty:
        st.warning("No Forge row exists for that date yet.")
        return
    row = selected_match.iloc[0]

    food_for_day = None
    if not food_daily.empty:
        food_match = food_daily.loc[food_daily["entry_date"] == selected_date]
        if not food_match.empty:
            food_for_day = food_match.iloc[0]

    open_todos = pd.DataFrame()
    if not todos.empty:
        open_todos = todos.loc[todos["is_open"].fillna(False)].copy()

    kpi = st.columns(5)
    kpi[0].metric("Challenge day", challenge_day(row["entry_date"]))
    kpi[1].metric("Session", row["planned_session"])
    kpi[2].metric("Strikes today", int(row["strikes_today"] or 0))
    if food_for_day is not None:
        kpi[3].metric("Food protein", f"{food_for_day['protein_g']:.1f} g", f"{food_for_day['protein_remaining_g']:.1f} g left")
        kpi[4].metric("Water", f"{food_for_day['water_liters']:.2f} L", f"{food_for_day['water_remaining_liters']:.2f} L left")
    else:
        kpi[3].metric("Food protein", "No food row")
        kpi[4].metric("Water", "No food row")

    attention = _missing_items(row, food_for_day, open_todos)
    if attention:
        st.warning("Needs attention")
        for item in attention[:8]:
            st.write(f"- {item}")
    else:
        st.success("Nothing obvious is screaming. Suspicious, but good.")

    with st.expander("Update Forge checklist", expanded=True):
        with st.form("forge-daily-checkin"):
            c1, c2 = st.columns(2)
            with c1:
                workout_done = st.checkbox("Scheduled workout / recovery done", value=bool(row["workout_done"]) if pd.notna(row["workout_done"]) else False)
                steps_count = st.number_input("Steps", min_value=0, max_value=100000, value=int(row["steps_count"]) if pd.notna(row["steps_count"]) else 0, step=500)
                protein_g = st.number_input("Protein (g)", min_value=0.0, max_value=500.0, value=float(row["protein_g"]) if pd.notna(row["protein_g"]) else 0.0, step=5.0)
                water_liters = st.number_input("Water (L)", min_value=0.0, max_value=10.0, value=float(row["water_liters"]) if pd.notna(row["water_liters"]) else 0.0, step=0.25)
            with c2:
                no_snacks_or_grazing = st.checkbox("No candy / snacks / grazing", value=bool(row["no_snacks_or_grazing"]) if pd.notna(row["no_snacks_or_grazing"]) else False)
                food_logged = st.checkbox("Food fully logged", value=bool(row["food_logged"]) if pd.notna(row["food_logged"]) else False)
                creatine_taken = st.checkbox("Creatine taken", value=bool(row["creatine_taken"]) if pd.notna(row["creatine_taken"]) else False)
                progress_photo = st.checkbox("Progress photo taken", value=bool(row["progress_photo"]) if pd.notna(row["progress_photo"]) else False)

            scale_available = st.checkbox("Scale available today", value=bool(row["scale_available"]) if pd.notna(row["scale_available"]) else False)
            weigh_in = st.checkbox("Weighed in", value=bool(row["weigh_in"]) if pd.notna(row["weigh_in"]) else False, disabled=not scale_available)
            weight = st.number_input("Body weight", min_value=0.0, max_value=1000.0, value=float(row["weight"]) if pd.notna(row["weight"]) else 0.0, step=0.1, disabled=not (scale_available and weigh_in))
            weight_unit = st.selectbox("Weight unit", options=["lb", "kg"], index=0 if row.get("weight_unit") != "kg" else 1, disabled=not (scale_available and weigh_in))
            notes = st.text_area("Notes", value=row["notes"] or "", height=90)
            submitted = st.form_submit_button("Save day")

        if submitted:
            save_forge_entry({
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
            })
            st.success("Saved.")
            st.rerun()

    status_cols = st.columns(5)
    status_cols[0].metric("Workout", format_status(row["workout_done"], "Done", "Missed"))
    status_cols[1].metric("Steps", format_status(row["steps_goal_hit"], "8k hit", "Under 8k"))
    status_cols[2].metric("Protein", format_status(row["protein_goal_hit"], "150g hit", "Under 150g"))
    status_cols[3].metric("Hydration", format_status(row["hydration_goal_hit"], "3 L hit", "Under 3 L"))
    if pd.notna(row.get("updated_at_local")):
        status_cols[4].metric("Last saved", format_local_dt(row["updated_at_local"]))

    if not open_todos.empty:
        st.markdown("#### Open todos")
        todo_table = open_todos[["title", "status", "priority", "area", "due_date", "is_overdue"]].copy().head(8)
        todo_table["is_overdue"] = todo_table["is_overdue"].map(lambda value: "⚠️" if value else "")
        st.dataframe(todo_table, use_container_width=True, hide_index=True)
