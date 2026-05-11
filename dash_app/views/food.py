import pandas as pd
import streamlit as st

from dash_app.charts import render_food_chart
from dash_app.formatting import format_local_dt, join_list, safe_int


def _warn_error(label: str, error: Exception | None) -> bool:
    if error is None:
        return False
    st.warning(f"{label} is unavailable right now.")
    with st.expander("Error details"):
        st.exception(error)
    return True


def render_food(
    food_daily: pd.DataFrame,
    food_daily_error: Exception | None,
    recipes: pd.DataFrame,
    recipe_ingredients: pd.DataFrame,
    recipes_error: Exception | None,
    ingredients: pd.DataFrame,
    ingredients_error: Exception | None,
    browser_timezone: str,
) -> None:
    daily_tab, recipes_tab, ingredients_tab = st.tabs(["Daily", "Recipes", "Ingredients"])

    with daily_tab:
        if _warn_error("Food data", food_daily_error):
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
        metrics[0].metric("Calories", f"{safe_int(latest.get('calories'))} / {safe_int(latest.get('calories_target'))} kcal", f"{safe_int(latest.get('calories_remaining'))} left")
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

    with recipes_tab:
        if not _warn_error("Recipe data", recipes_error):
            if recipes.empty:
                st.caption("No saved recipes yet.")
            else:
                view = recipes.copy()
                view["updated_at_local"] = pd.to_datetime(view["updated_at"], utc=True).dt.tz_convert(browser_timezone)
                metrics = st.columns(4)
                metrics[0].metric("Recipes", len(view))
                metrics[1].metric("Avg protein", f"{view['protein_g'].fillna(0).mean():.1f} g")
                metrics[2].metric("Avg calories", f"{view['calories'].fillna(0).mean():.0f} kcal")
                metrics[3].metric("Latest update", view["updated_at_local"].max().strftime('%Y-%m-%d'))
                table = view[["recipe_name", "category", "total_amount_g", "calories", "protein_g", "fat_g", "carbs_g", "fiber_g", "tags", "updated_at_local"]].copy()
                table["tags"] = table["tags"].apply(join_list)
                table["updated_at_local"] = table["updated_at_local"].apply(format_local_dt)
                st.dataframe(table, use_container_width=True, hide_index=True)

                names = view["recipe_name"].tolist()
                selected_name = st.selectbox("Recipe details", names, key="recipe_select")
                selected = view.loc[view["recipe_name"] == selected_name].iloc[0]
                detail = recipe_ingredients.loc[recipe_ingredients["recipe_key"] == selected["recipe_key"]].copy()
                cols = st.columns(6)
                cols[0].metric("Total grams", f"{selected['total_amount_g']:.1f} g" if pd.notna(selected["total_amount_g"]) else "—")
                cols[1].metric("Calories", f"{selected['calories']:.0f}" if pd.notna(selected["calories"]) else "—")
                cols[2].metric("Protein", f"{selected['protein_g']:.1f} g" if pd.notna(selected["protein_g"]) else "—")
                cols[3].metric("Fat", f"{selected['fat_g']:.1f} g" if pd.notna(selected["fat_g"]) else "—")
                cols[4].metric("Carbs", f"{selected['carbs_g']:.1f} g" if pd.notna(selected["carbs_g"]) else "—")
                cols[5].metric("Fiber", f"{selected['fiber_g']:.1f} g" if pd.notna(selected["fiber_g"]) else "—")
                if selected.get("notes"):
                    st.caption(selected["notes"])
                if not detail.empty:
                    with st.expander("Recipe ingredients", expanded=True):
                        st.dataframe(detail[["sort_order", "product_name", "brand", "amount_g", "calories", "protein_g", "fat_g", "carbs_g", "fiber_g", "notes"]], use_container_width=True, hide_index=True)

    with ingredients_tab:
        if not _warn_error("Ingredient data", ingredients_error):
            if ingredients.empty:
                st.caption("No ingredient records yet.")
            else:
                view = ingredients.copy()
                view["updated_at_local"] = pd.to_datetime(view["updated_at"], utc=True).dt.tz_convert(browser_timezone)
                metrics = st.columns(4)
                metrics[0].metric("Ingredients", len(view))
                metrics[1].metric("With nicknames", int(view["nicknames"].apply(lambda values: len(values or []) > 0).sum()))
                metrics[2].metric("Brands", view["brand"].fillna("Unknown").nunique())
                metrics[3].metric("Latest update", view["updated_at_local"].max().strftime('%Y-%m-%d'))
                table = view[["product_name", "brand", "regular_portion_g", "calories_per_100g", "protein_g_per_100g", "fat_g_per_100g", "carbs_g_per_100g", "fiber_g_per_100g", "nicknames", "updated_at_local"]].copy()
                table["nicknames"] = table["nicknames"].apply(join_list)
                table["updated_at_local"] = table["updated_at_local"].apply(format_local_dt)
                st.dataframe(table, use_container_width=True, hide_index=True)
