import pandas as pd
import streamlit as st


def _format_utc(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = frame.copy()
    for col in columns:
        if col in result.columns:
            result[col] = pd.to_datetime(result[col], utc=True, errors="coerce").dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    return result


def render_admin(
    tracker: pd.DataFrame,
    food_daily: pd.DataFrame,
    food_daily_error: Exception | None,
    recipes: pd.DataFrame,
    recipe_ingredients: pd.DataFrame,
    recipes_error: Exception | None,
    todos: pd.DataFrame,
    todo_events: pd.DataFrame,
    todos_error: Exception | None,
    ingredients: pd.DataFrame,
    ingredients_error: Exception | None,
) -> None:
    st.subheader("Raw data")
    st.caption("Debug tables live here so the main dashboard can act like a product, not a warehouse spill.")

    with st.expander("Forge raw data", expanded=False):
        raw = tracker.copy()
        raw["entry_date"] = raw["entry_date"].astype(str)
        raw = _format_utc(raw, ["updated_at"])
        if "updated_at_local" in raw.columns:
            raw["updated_at_local"] = raw["updated_at_local"].apply(lambda value: value.strftime('%Y-%m-%d %H:%M:%S %Z') if pd.notna(value) else '—')
        st.dataframe(raw, use_container_width=True, hide_index=True)

    with st.expander("Food raw data", expanded=False):
        if food_daily_error is not None:
            st.exception(food_daily_error)
        elif food_daily.empty:
            st.caption("No food rows.")
        else:
            raw = food_daily.copy()
            raw["entry_date"] = raw["entry_date"].astype(str)
            raw = _format_utc(raw, ["updated_at"])
            st.dataframe(raw, use_container_width=True, hide_index=True)

    with st.expander("Recipe raw data", expanded=False):
        if recipes_error is not None:
            st.exception(recipes_error)
        else:
            st.dataframe(_format_utc(recipes, ["updated_at"]), use_container_width=True, hide_index=True)
            if not recipe_ingredients.empty:
                st.markdown("Recipe ingredients")
                st.dataframe(_format_utc(recipe_ingredients, ["updated_at"]), use_container_width=True, hide_index=True)

    with st.expander("Todo raw data", expanded=False):
        if todos_error is not None:
            st.exception(todos_error)
        else:
            st.dataframe(_format_utc(todos, ["created_at", "updated_at", "completed_at"]), use_container_width=True, hide_index=True)
            if not todo_events.empty:
                st.markdown("Todo events")
                st.dataframe(_format_utc(todo_events, ["event_at"]), use_container_width=True, hide_index=True)

    with st.expander("Ingredient raw data", expanded=False):
        if ingredients_error is not None:
            st.exception(ingredients_error)
        else:
            st.dataframe(_format_utc(ingredients, ["updated_at"]), use_container_width=True, hide_index=True)
