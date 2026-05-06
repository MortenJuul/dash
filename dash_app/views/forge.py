import pandas as pd
import streamlit as st

from dash_app.config import REVIEW_GATES
from dash_app.formatting import bool_icon, format_local_dt


def render_forge(tracker: pd.DataFrame) -> None:
    st.subheader("Forge")
    st.caption("Challenge status, weekly execution, and trends.")

    total_strikes = int(tracker["strikes_today"].fillna(0).sum())
    days_complete = int((tracker["completed_checks"].fillna(0) >= 8).sum())
    current = tracker.iloc[-1]

    kpi = st.columns(4)
    kpi[0].metric("Status", "Failed" if total_strikes >= 3 else "Live", f"{max(0, 3 - total_strikes)} strikes left")
    kpi[1].metric("Total strikes", total_strikes)
    kpi[2].metric("Days fully clean", days_complete)
    kpi[3].metric("Current week", int(current["week_no"]))

    with st.expander("Review gates", expanded=False):
        for gate in REVIEW_GATES:
            st.write(f"- {gate.isoformat()}")

    week_options = sorted(tracker["week_no"].dropna().unique().tolist())
    selected_week = st.selectbox("Week", week_options, index=len(week_options) - 1)
    week_df = tracker.loc[tracker["week_no"] == selected_week].copy()

    display = week_df[[
        "entry_date", "day_name", "planned_session", "workout_done", "steps_goal_hit",
        "protein_goal_hit", "food_logged", "hydration_goal_hit", "creatine_taken",
        "progress_photo", "strikes_today", "cumulative_strikes", "updated_at_local",
    ]].copy()
    for col in ["workout_done", "steps_goal_hit", "protein_goal_hit", "food_logged", "hydration_goal_hit", "creatine_taken", "progress_photo"]:
        display[col] = display[col].map(bool_icon)
    display["updated_at_local"] = display["updated_at_local"].apply(format_local_dt)
    st.dataframe(display, use_container_width=True, hide_index=True)

    chart_df = tracker.set_index("entry_date").copy()
    st.markdown("#### Trends")
    left, right = st.columns(2)
    with left:
        st.markdown("Weight")
        if chart_df["weight"].notna().any():
            st.line_chart(chart_df[["weight"]])
        else:
            st.caption("No weigh-ins logged yet.")
        st.markdown("Protein / water")
        st.line_chart(chart_df[["protein_g", "water_liters"]])
    with right:
        st.markdown("Strikes")
        st.line_chart(chart_df[["strikes_today", "cumulative_strikes"]].fillna(0))
