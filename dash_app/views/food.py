import pandas as pd
import streamlit as st

from dash_app.charts import render_food_chart
from dash_app.formatting import format_local_dt


def render_food(food_daily: pd.DataFrame, food_daily_error: Exception | None, browser_timezone: str) -> None:
    st.subheader("Food")
    st.caption("Daily nutrition and hydration rollups. Ingredient/recipe reference lives under Planning.")
    if food_daily_error is not None:
        st.warning("Food data is unavailable right now.")
        with st.expander("Error details"):
            st.exception(food_daily_error)
        return
    if food_daily.empty:
        st.caption("No food rows synced yet.")
        return

    food = food_daily.copy()
    food["updated_at_local"] = pd.to_datetime(food["updated_at"], utc=True).dt.tz_convert(browser_timezone)
    food = food.set_index("entry_date")
    latest = food.iloc[-1]

    st.caption(f"Latest logged day: {food.index[-1]}")
    metrics = st.columns(5)
    metrics[0].metric("Calories", f"{int(latest['calories'])} / {int(latest['calories_target'])} kcal", f"{int(latest['calories_remaining'])} left")
    metrics[1].metric("Protein", f"{latest['protein_g']:.1f} / {latest['protein_target_g']:.1f} g", f"{latest['protein_remaining_g']:.1f} g left")
    metrics[2].metric("Fat", f"{latest['fat_g']:.1f} / {latest['fat_target_g']:.1f} g", f"{latest['fat_remaining_g']:.1f} g left")
    metrics[3].metric("Carbs", f"{latest['carbs_g']:.1f} / {latest['carbs_target_g']:.1f} g", f"{latest['carbs_remaining_g']:.1f} g left")
    metrics[4].metric("Water", f"{latest['water_liters']:.2f} / {latest['water_target_liters']:.2f} L", f"{latest['water_remaining_liters']:.2f} L left")

    calories_chart = food[["calories", "calories_target"]].copy()
    calories_chart.loc[calories_chart["calories"].isna(), "calories_target"] = pd.NA
    macros_chart = food[["protein_g", "fat_g", "carbs_g", "fiber_g"]].copy()
    water_chart = food[["water_liters", "water_target_liters"]].copy()
    water_chart.loc[water_chart["water_liters"].isna(), "water_target_liters"] = pd.NA

    left, right = st.columns(2)
    with left:
        st.altair_chart(render_food_chart(calories_chart, ["calories", "calories_target"], "Calories"), use_container_width=True)
    with right:
        st.altair_chart(render_food_chart(macros_chart, ["protein_g", "fat_g", "carbs_g", "fiber_g"], "Macros"), use_container_width=True)
    st.altair_chart(render_food_chart(water_chart, ["water_liters", "water_target_liters"], "Water"), use_container_width=True)

    recent = food.reset_index().sort_values("entry_date", ascending=False).copy()
    recent["entry_date"] = recent["entry_date"].astype(str)
    recent["updated_at_local"] = recent["updated_at_local"].apply(format_local_dt)
    with st.expander("Recent rollup", expanded=True):
        st.dataframe(recent[["entry_date", "calories", "protein_g", "fat_g", "carbs_g", "fiber_g", "water_liters", "updated_at_local"]], use_container_width=True, hide_index=True)
    if latest.get("entries_markdown"):
        with st.expander("Latest day entry details"):
            st.markdown(latest["entries_markdown"])
