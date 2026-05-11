import pandas as pd
import streamlit as st

from dash_app.config import HYDRATION_GOAL_L, PROTEIN_GOAL_G, STEP_GOAL
from dash_app.data import save_forge_entry
from dash_app.formatting import bool_icon, format_local_dt, safe_int


FORGE_CHECKS = [
    ("workout_done", "Workout"),
    ("steps_goal_hit", "Steps"),
    ("protein_goal_hit", "Protein"),
    ("no_snacks_or_grazing", "No snacks"),
    ("food_logged", "Food logged"),
    ("hydration_goal_hit", "Water"),
    ("creatine_taken", "Creatine"),
    ("progress_photo", "Photo"),
]


def _required_check_count(row: pd.Series) -> int:
    return len(FORGE_CHECKS) + (1 if row.get("scale_available") is True else 0)


def _completed_check_count(row: pd.Series) -> int:
    value = safe_int(row.get("completed_checks"))
    return min(value, _required_check_count(row))


def _format_weight(row: pd.Series) -> str:
    if pd.isna(row.get("weight")):
        return "—"
    unit = row.get("weight_unit") if pd.notna(row.get("weight_unit")) else "kg"
    return f"{float(row['weight']):.2f} {unit}"


def _safe_progress(value: float, target: float) -> float:
    if not target or pd.isna(value):
        return 0.0
    return max(0.0, min(float(value) / float(target), 1.0))


def _open_todos(todos: pd.DataFrame) -> pd.DataFrame:
    if todos.empty:
        return pd.DataFrame()
    return todos.loc[todos["is_open"].fillna(False)].copy()


def _attention_items(row: pd.Series, food_row: pd.Series | None, open_todos: pd.DataFrame) -> list[str]:
    items: list[str] = []
    if row.get("workout_done") is not True:
        items.append("Workout/recovery not done")
    if not bool(row.get("steps_goal_hit")):
        steps = int(row["steps_count"]) if pd.notna(row.get("steps_count")) else 0
        items.append(f"Steps: {steps:,}/{STEP_GOAL:,}")
    if not bool(row.get("protein_goal_hit")):
        protein = float(row["protein_g"]) if pd.notna(row.get("protein_g")) else 0.0
        items.append(f"Forge protein: {protein:.1f}/{PROTEIN_GOAL_G:g} g")
    if not bool(row.get("hydration_goal_hit")):
        water = float(row["water_liters"]) if pd.notna(row.get("water_liters")) else 0.0
        items.append(f"Forge water: {water:.2f}/{HYDRATION_GOAL_L:g} L")
    for col, label in [("food_logged", "Food not marked complete"), ("creatine_taken", "Creatine"), ("progress_photo", "Progress photo")]:
        if row.get(col) is not True:
            items.append(label)
    if row.get("scale_available") is True and row.get("weigh_in") is not True:
        items.append("Weigh-in missing")
    if food_row is not None and pd.notna(food_row.get("protein_remaining_g")) and food_row["protein_remaining_g"] > 0:
        items.append(f"Food protein left: {food_row['protein_remaining_g']:.1f} g")
    if food_row is not None and pd.notna(food_row.get("water_remaining_liters")) and food_row["water_remaining_liters"] > 0:
        items.append(f"Water left: {food_row['water_remaining_liters']:.2f} L")
    if not open_todos.empty:
        overdue_count = int(open_todos["is_overdue"].fillna(False).sum())
        blocked_count = int((open_todos["status"] == "blocked").sum())
        if overdue_count:
            items.append(f"{overdue_count} overdue todo(s)")
        if blocked_count:
            items.append(f"{blocked_count} blocked todo(s)")
    return items


def _render_challenge_card(row: pd.Series) -> None:
    checks_done = _completed_check_count(row)
    required_checks = _required_check_count(row)
    st.markdown("#### Challenge")
    st.progress(_safe_progress(checks_done, required_checks), text=f"{checks_done}/{required_checks} Forge checks")
    c1, c2, c3 = st.columns(3)
    c1.metric("Session", row["planned_session"])
    c2.metric("Strikes", safe_int(row.get("strikes_today")), f"{safe_int(row.get('cumulative_strikes'))} total")
    c3.metric("Weight", _format_weight(row), "logged" if row.get("weigh_in") is True else "not logged")

    checklist_rows = [{"Check": label, "Done": bool_icon(row.get(column))} for column, label in FORGE_CHECKS]
    if row.get("scale_available") is True:
        checklist_rows.append({"Check": "Weigh-in", "Done": bool_icon(row.get("weigh_in"))})
    checklist = pd.DataFrame(checklist_rows)
    st.dataframe(checklist, use_container_width=True, hide_index=True, height=315)


def _render_food_card(food_row: pd.Series | None) -> None:
    st.markdown("#### Food")
    if food_row is None:
        st.info("No food log synced for this date yet.")
        return

    calories = float(food_row["calories"]) if pd.notna(food_row.get("calories")) else 0.0
    calories_target = float(food_row["calories_target"]) if pd.notna(food_row.get("calories_target")) else 0.0
    protein = float(food_row["protein_g"]) if pd.notna(food_row.get("protein_g")) else 0.0
    protein_target = float(food_row["protein_target_g"]) if pd.notna(food_row.get("protein_target_g")) else 0.0
    water = float(food_row["water_liters"]) if pd.notna(food_row.get("water_liters")) else 0.0
    water_target = float(food_row["water_target_liters"]) if pd.notna(food_row.get("water_target_liters")) else 0.0

    st.progress(_safe_progress(calories, calories_target), text=f"Calories: {calories:.0f}/{calories_target:.0f} kcal")
    st.progress(_safe_progress(protein, protein_target), text=f"Protein: {protein:.1f}/{protein_target:.1f} g")
    st.progress(_safe_progress(water, water_target), text=f"Water: {water:.2f}/{water_target:.2f} L")

    c1, c2, c3 = st.columns(3)
    c1.metric("Fat", f"{food_row['fat_g']:.1f} g", f"{food_row['fat_remaining_g']:.1f} left")
    c2.metric("Carbs", f"{food_row['carbs_g']:.1f} g", f"{food_row['carbs_remaining_g']:.1f} left")
    c3.metric("Fiber", f"{food_row['fiber_g']:.1f} g")

    if food_row.get("entries_markdown"):
        with st.expander("Food entries", expanded=False):
            st.markdown(food_row["entries_markdown"])


def _render_todo_card(open_todos: pd.DataFrame) -> None:
    st.markdown("#### Todos")
    if open_todos.empty:
        st.success("No open todos. Dangerous levels of competence.")
        return

    overdue = int(open_todos["is_overdue"].fillna(False).sum())
    in_progress = int((open_todos["status"] == "in_progress").sum())
    blocked = int((open_todos["status"] == "blocked").sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Open", len(open_todos))
    c2.metric("Overdue", overdue)
    c3.metric("Doing", in_progress)
    c4.metric("Blocked", blocked)

    todo_table = open_todos[["title", "status", "priority", "area", "due_date", "is_overdue"]].copy().head(8)
    todo_table["is_overdue"] = todo_table["is_overdue"].map(lambda value: "⚠️" if value else "")
    st.dataframe(todo_table, use_container_width=True, hide_index=True, height=315)


def _render_forge_form(row: pd.Series, selected_date) -> None:
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


def render_today(
    tracker: pd.DataFrame,
    food_daily: pd.DataFrame,
    todos: pd.DataFrame,
    browser_timezone: str,
    selected_date,
) -> None:
    selected_match = tracker.loc[tracker["entry_date"] == selected_date]
    if selected_match.empty:
        st.warning("No Forge row exists for that date yet.")
        return
    row = selected_match.iloc[0]

    food_row = None
    if not food_daily.empty:
        food_match = food_daily.loc[food_daily["entry_date"] == selected_date]
        if not food_match.empty:
            food_row = food_match.iloc[0]
    open_todos = _open_todos(todos)

    st.caption(f"{selected_date} · {row['day_name']} · {row['planned_session']}")

    attention = _attention_items(row, food_row, open_todos)
    if attention:
        st.warning("Today's attention list")
        st.write(" · ".join(attention[:6]))
    else:
        st.success("Today is currently clean. Suspicious, but good.")

    challenge_col, food_col = st.columns([1, 1])
    with challenge_col:
        _render_challenge_card(row)
    with food_col:
        _render_food_card(food_row)

    st.divider()
    _render_todo_card(open_todos)

    with st.expander("Edit Forge check-in", expanded=False):
        _render_forge_form(row, selected_date)

    if pd.notna(row.get("updated_at_local")):
        st.caption(f"Last Forge save: {format_local_dt(row['updated_at_local'])} · Browser timezone: {browser_timezone}")
