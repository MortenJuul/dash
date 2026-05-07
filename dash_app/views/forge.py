import altair as alt
import pandas as pd
import streamlit as st

from dash_app.config import REVIEW_GATES
from dash_app.formatting import bool_icon, format_local_dt


def _trend_frame(frame: pd.DataFrame, selected_date, columns: list[str]) -> pd.DataFrame:
    trend = frame.loc[frame["entry_date"] <= selected_date, ["entry_date", *columns]].copy()
    trend["entry_date"] = pd.to_datetime(trend["entry_date"])
    for column in columns:
        trend[column] = pd.to_numeric(trend[column], errors="coerce")
    return trend.sort_values("entry_date")


def _single_series_chart(frame: pd.DataFrame, column: str, label: str, suffix: str = "") -> alt.Chart | None:
    chart_frame = frame[["entry_date", column]].dropna(subset=[column]).copy()
    if chart_frame.empty:
        return None

    chart_frame["date_label"] = chart_frame["entry_date"].dt.strftime("%Y-%m-%d")
    chart_frame["value_label"] = chart_frame[column].map(lambda value: f"{value:g}{suffix}")
    value_min = chart_frame[column].min()
    value_max = chart_frame[column].max()
    if value_min == value_max:
        padding = max(abs(value_min) * 0.02, 1.0)
    else:
        padding = (value_max - value_min) * 0.12

    base = alt.Chart(chart_frame).encode(
        x=alt.X("entry_date:T", title="Date", sort="ascending"),
        y=alt.Y(
            f"{column}:Q",
            title=label,
            scale=alt.Scale(domain=[float(value_min - padding), float(value_max + padding)], zero=False, nice=False),
        ),
        tooltip=[
            alt.Tooltip("date_label:N", title="Date"),
            alt.Tooltip("value_label:N", title=label),
        ],
    )
    return (base.mark_line(strokeWidth=2.5) + base.mark_circle(size=70)).properties(height=230)


def render_forge(tracker: pd.DataFrame, selected_date, food_daily: pd.DataFrame | None = None) -> None:
    st.subheader("Forge")
    st.caption("Challenge status, weekly execution, and trends.")

    total_strikes = int(tracker["strikes_today"].fillna(0).sum())
    days_complete = int((tracker["completed_checks"].fillna(0) >= 8).sum())
    selected_match = tracker.loc[tracker["entry_date"] == selected_date]
    current = selected_match.iloc[0] if not selected_match.empty else tracker.iloc[-1]

    kpi = st.columns(4)
    kpi[0].metric("Status", "Failed" if total_strikes >= 3 else "Live", f"{max(0, 3 - total_strikes)} strikes left")
    kpi[1].metric("Total strikes", total_strikes)
    kpi[2].metric("Days fully clean", days_complete)
    kpi[3].metric("Current week", int(current["week_no"]))

    with st.expander("Review gates", expanded=False):
        for gate in REVIEW_GATES:
            st.write(f"- {gate.isoformat()}")

    week_options = sorted(tracker["week_no"].dropna().unique().tolist())
    current_week = current["week_no"] if pd.notna(current.get("week_no")) else week_options[-1]
    default_index = week_options.index(current_week) if current_week in week_options else len(week_options) - 1
    selected_week = st.selectbox("Week", week_options, index=default_index)
    week_df = tracker.loc[tracker["week_no"] == selected_week].copy()

    display = week_df[[
        "entry_date", "day_name", "planned_session", "workout_done", "steps_goal_hit",
        "protein_goal_hit", "food_logged", "hydration_goal_hit", "creatine_taken",
        "progress_photo", "weigh_in", "weight", "weight_unit", "strikes_today",
        "cumulative_strikes", "updated_at_local",
    ]].copy()
    for col in ["workout_done", "steps_goal_hit", "protein_goal_hit", "food_logged", "hydration_goal_hit", "creatine_taken", "progress_photo", "weigh_in"]:
        display[col] = display[col].map(bool_icon)
    display["updated_at_local"] = display["updated_at_local"].apply(format_local_dt)
    st.dataframe(display, use_container_width=True, hide_index=True)

    st.markdown("#### Trends")
    st.caption("Showing logged days up to the selected date; future challenge rows are excluded.")
    tracker_trends = _trend_frame(tracker, selected_date, ["weight", "strikes_today", "cumulative_strikes"])
    challenge_start = tracker["entry_date"].min()
    if food_daily is not None and not food_daily.empty:
        nutrition_source = food_daily.loc[food_daily["entry_date"] >= challenge_start]
        nutrition_trends = _trend_frame(nutrition_source, selected_date, ["protein_g", "water_liters"])
    else:
        nutrition_trends = _trend_frame(tracker, selected_date, ["protein_g", "water_liters"])

    left, right = st.columns(2)
    with left:
        st.markdown("Weight")
        chart = _single_series_chart(tracker_trends, "weight", "Weight", " kg")
        if chart is not None:
            st.altair_chart(chart, use_container_width=True)
        else:
            st.caption("No weigh-ins logged yet.")
        st.markdown("Protein")
        chart = _single_series_chart(nutrition_trends, "protein_g", "Protein", " g")
        if chart is not None:
            st.altair_chart(chart, use_container_width=True)
        else:
            st.caption("No protein totals logged yet.")
    with right:
        st.markdown("Water")
        chart = _single_series_chart(nutrition_trends, "water_liters", "Water", " L")
        if chart is not None:
            st.altair_chart(chart, use_container_width=True)
        else:
            st.caption("No water totals logged yet.")
        st.markdown("Strikes")
        strikes = tracker_trends[["entry_date", "strikes_today", "cumulative_strikes"]].copy()
        strikes = strikes.dropna(how="all", subset=["strikes_today", "cumulative_strikes"])
        if not strikes.empty:
            strikes["strikes_today"] = strikes["strikes_today"].fillna(0)
            strikes["cumulative_strikes"] = strikes["cumulative_strikes"].ffill().fillna(0)
            melted = strikes.melt("entry_date", var_name="series", value_name="value")
            melted["series"] = melted["series"].map({"strikes_today": "Today", "cumulative_strikes": "Cumulative"})
            chart = alt.Chart(melted).mark_line(point=True, strokeWidth=2.5).encode(
                x=alt.X("entry_date:T", title="Date", sort="ascending"),
                y=alt.Y("value:Q", title="Strikes", scale=alt.Scale(domainMin=0, nice=False)),
                color=alt.Color("series:N", title=None),
                tooltip=[alt.Tooltip("entry_date:T", title="Date"), alt.Tooltip("series:N", title="Series"), alt.Tooltip("value:Q", title="Strikes", format=".0f")],
            ).properties(height=230)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.caption("No strike data logged yet.")
