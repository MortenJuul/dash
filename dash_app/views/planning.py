import pandas as pd
import streamlit as st

from dash_app.formatting import format_local_dt, join_list


def _warn_error(label: str, error: Exception | None) -> bool:
    if error is None:
        return False
    st.warning(f"{label} is unavailable right now.")
    with st.expander("Error details"):
        st.exception(error)
    return True


def render_planning(
    todos: pd.DataFrame,
    todo_events: pd.DataFrame,
    todos_error: Exception | None,
    recipes: pd.DataFrame,
    recipe_ingredients: pd.DataFrame,
    recipes_error: Exception | None,
    ingredients: pd.DataFrame,
    ingredients_error: Exception | None,
    browser_timezone: str,
) -> None:
    st.subheader("Planning")
    st.caption("Todos first. Meals and ingredients are reference tools, not the main dashboard.")

    todo_tab, recipes_tab, ingredients_tab = st.tabs(["Todos", "Recipes", "Ingredients"])

    with todo_tab:
        if not _warn_error("Todo data", todos_error):
            if todos.empty:
                st.caption("No todo rows synced yet.")
            else:
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
