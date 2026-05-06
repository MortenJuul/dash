import pandas as pd
import streamlit as st

from dash_app.formatting import format_local_dt, join_list


def render_planning(
    todos: pd.DataFrame,
    todo_events: pd.DataFrame,
    todos_error: Exception | None,
    browser_timezone: str,
) -> None:
    if todos_error is not None:
        st.warning("Todo data is unavailable right now.")
        with st.expander("Error details"):
            st.exception(todos_error)
        return
    if todos.empty:
        st.caption("No todo rows synced yet.")
        return

    view = todos.copy()
    for src, dest in [("created_at", "created_at_local"), ("updated_at", "updated_at_local"), ("completed_at", "completed_at_local")]:
        view[dest] = pd.to_datetime(view[src], utc=True, errors="coerce").dt.tz_convert(browser_timezone)

    metrics = st.columns(5)
    metrics[0].metric("Open", int(view["is_open"].fillna(False).sum()))
    metrics[1].metric("In progress", int((view["status"] == "in_progress").sum()))
    metrics[2].metric("Blocked", int((view["status"] == "blocked").sum()))
    metrics[3].metric("Done", int((view["status"] == "done").sum()))
    metrics[4].metric("Overdue", int(view["is_overdue"].fillna(False).sum()))

    table = view[["title", "status", "priority", "area", "due_date", "tags", "is_overdue", "updated_at_local"]].copy()
    table["tags"] = table["tags"].apply(join_list)
    table["is_overdue"] = table["is_overdue"].map(lambda value: "⚠️" if value else "")
    table["updated_at_local"] = table["updated_at_local"].apply(format_local_dt)
    st.dataframe(table, use_container_width=True, hide_index=True)

    titles = view["title"].tolist()
    selected_title = st.selectbox("Todo details", titles, key="todo_select")
    selected = view.loc[view["title"] == selected_title].iloc[0]
    detail_cols = st.columns(5)
    detail_cols[0].metric("Status", selected["status"])
    detail_cols[1].metric("Priority", selected["priority"] or "—")
    detail_cols[2].metric("Area", selected["area"] or "—")
    detail_cols[3].metric("Due", str(selected["due_date"]) if pd.notna(selected["due_date"]) else "—")
    detail_cols[4].metric("Overdue", "Yes" if bool(selected["is_overdue"]) else "No")
    if selected.get("notes"):
        st.caption(selected["notes"])
    if not todo_events.empty:
        events = todo_events.loc[todo_events["task_key"] == selected["task_key"]].copy()
        if not events.empty:
            events["event_at_local"] = pd.to_datetime(events["event_at"], utc=True, errors="coerce").dt.tz_convert(browser_timezone)
            events["event_at_local"] = events["event_at_local"].apply(format_local_dt)
            with st.expander("Recent task events", expanded=False):
                st.dataframe(events[["event_at_local", "event_type", "details"]], use_container_width=True, hide_index=True)
