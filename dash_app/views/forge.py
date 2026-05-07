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


def _latest_metric_delta(frame: pd.DataFrame, column: str) -> tuple[float | None, float | None]:
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    if values.empty:
        return None, None
    latest = float(values.iloc[-1])
    previous = float(values.iloc[-2]) if len(values) > 1 else None
    return latest, (latest - previous) if previous is not None else None


def _metric_value(value: float | None, suffix: str = "", decimals: int = 1) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:.{decimals}f}{suffix}"


def _metric_delta(delta: float | None, suffix: str = "", decimals: int = 1, invert: bool = False) -> str | None:
    if delta is None or pd.isna(delta):
        return None
    shown = -delta if invert else delta
    return f"{shown:+.{decimals}f}{suffix}"


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

    weighins = tracker.loc[(tracker["entry_date"] <= selected_date) & tracker["weight"].notna()].copy()
    if not weighins.empty:
        weighins = weighins.sort_values("entry_date")
        first_weight = float(weighins.iloc[0]["weight"])
        latest_weight = float(weighins.iloc[-1]["weight"])
        previous_weight = float(weighins.iloc[-2]["weight"]) if len(weighins) > 1 else None
        weight_lost = first_weight - latest_weight
        weight_unit = weighins.iloc[-1].get("weight_unit") if pd.notna(weighins.iloc[-1].get("weight_unit")) else "kg"

        st.markdown("#### Weigh-in stats")
        stats = st.columns(4)
        stats[0].metric("Weight lost", f"{weight_lost:.2f} {weight_unit}", "since first Forge weigh-in")
        stats[1].metric(
            "Latest weight",
            f"{latest_weight:.2f} {weight_unit}",
            f"{latest_weight - previous_weight:+.2f} vs prior" if previous_weight is not None else None,
            delta_color="inverse",
        )
        latest_bmi, bmi_delta = _latest_metric_delta(weighins, "bmi")
        latest_body_fat, body_fat_delta = _latest_metric_delta(weighins, "body_fat_pct")
        stats[2].metric("BMI", _metric_value(latest_bmi), _metric_delta(bmi_delta, decimals=1), delta_color="inverse")
        stats[3].metric("Body fat", _metric_value(latest_body_fat, "%"), _metric_delta(body_fat_delta, "%"), delta_color="inverse")

        with st.expander("More scale metrics", expanded=True):
            metric_cols = st.columns(3)
            latest_muscle, muscle_delta = _latest_metric_delta(weighins, "skeletal_muscle_pct")
            latest_water, water_delta = _latest_metric_delta(weighins, "body_water_pct")
            latest_bmr, bmr_delta = _latest_metric_delta(weighins, "bmr_kcal")
            metric_cols[0].metric("Skeletal muscle", _metric_value(latest_muscle, "%"), _metric_delta(muscle_delta, "%"))
            metric_cols[1].metric("Body water", _metric_value(latest_water, "%"), _metric_delta(water_delta, "%"))
            metric_cols[2].metric("BMR", _metric_value(latest_bmr, " kcal", 0), _metric_delta(bmr_delta, " kcal", 0))
            metric_cols = st.columns(3)
            metric_cols[0].metric("First weigh-in", f"{first_weight:.2f} {weight_unit}")
            metric_cols[1].metric("Weigh-ins logged", len(weighins))
            metric_cols[2].metric("Average / week", f"{(weight_lost / max((weighins.iloc[-1]['entry_date'] - weighins.iloc[0]['entry_date']).days, 1) * 7):.2f} {weight_unit}")
            detail_cols = ["entry_date", "weight", "weight_unit", "bmi", "body_fat_pct", "skeletal_muscle_pct", "body_water_pct", "bmr_kcal"]
            st.dataframe(weighins[detail_cols], use_container_width=True, hide_index=True)

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
        "progress_photo", "weigh_in", "weight", "weight_unit", "bmi", "body_fat_pct",
        "skeletal_muscle_pct", "body_water_pct", "bmr_kcal", "strikes_today",
        "cumulative_strikes", "updated_at_local",
    ]].copy()
    for col in ["workout_done", "steps_goal_hit", "protein_goal_hit", "food_logged", "hydration_goal_hit", "creatine_taken", "progress_photo", "weigh_in"]:
        display[col] = display[col].map(bool_icon)
    display["updated_at_local"] = display["updated_at_local"].apply(format_local_dt)
    st.dataframe(display, use_container_width=True, hide_index=True)

    st.markdown("#### Trends")
    st.caption("Showing logged days up to the selected date; future challenge rows are excluded.")
    tracker_trends = _trend_frame(tracker, selected_date, ["weight", "bmi", "body_fat_pct", "skeletal_muscle_pct", "body_water_pct", "bmr_kcal", "strikes_today", "cumulative_strikes"])
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
    with st.expander("Scale metric trends", expanded=False):
        body_left, body_right = st.columns(2)
        with body_left:
            st.markdown("Body fat")
            chart = _single_series_chart(tracker_trends, "body_fat_pct", "Body fat", "%")
            st.altair_chart(chart, use_container_width=True) if chart is not None else st.caption("No body-fat readings logged yet.")
            st.markdown("Skeletal muscle")
            chart = _single_series_chart(tracker_trends, "skeletal_muscle_pct", "Skeletal muscle", "%")
            st.altair_chart(chart, use_container_width=True) if chart is not None else st.caption("No skeletal-muscle readings logged yet.")
        with body_right:
            st.markdown("Body water")
            chart = _single_series_chart(tracker_trends, "body_water_pct", "Body water", "%")
            st.altair_chart(chart, use_container_width=True) if chart is not None else st.caption("No body-water readings logged yet.")
            st.markdown("BMR")
            chart = _single_series_chart(tracker_trends, "bmr_kcal", "BMR", " kcal")
            st.altair_chart(chart, use_container_width=True) if chart is not None else st.caption("No BMR readings logged yet.")
