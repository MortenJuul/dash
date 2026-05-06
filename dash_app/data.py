from typing import Any

import pandas as pd
import psycopg
import streamlit as st
from psycopg.rows import dict_row

from .config import DATABASE_URL, HYDRATION_GOAL_L, PROTEIN_GOAL_G, STEP_GOAL


@st.cache_data(ttl=60)
def load_tracker() -> pd.DataFrame:
    with psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select entry_date, week_no, block_no, day_name, planned_session,
                  workout_done, steps_count, steps_goal_hit, protein_g,
                  protein_goal_hit, no_snacks_or_grazing, food_logged,
                  water_liters, hydration_goal_hit, creatine_taken,
                  progress_photo, scale_available, weigh_in, weight, weight_unit,
                  strikes_today, cumulative_strikes, completed_checks, notes, updated_at
                from challenge.forge_daily_status
                order by entry_date
                """
            )
            rows = cur.fetchall()
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame["entry_date"] = pd.to_datetime(frame["entry_date"]).dt.date
    return frame


@st.cache_data(ttl=60)
def load_food_daily() -> pd.DataFrame:
    with psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select entry_date, calories_target, protein_target_g, fat_target_g,
                  carbs_target_g, fiber_target_g_low, fiber_target_g_high,
                  water_target_liters, calories, protein_g, fat_g, carbs_g,
                  fiber_g, water_liters, calories_remaining, protein_remaining_g,
                  fat_remaining_g, carbs_remaining_g, fiber_remaining_g_low,
                  fiber_remaining_g_high, water_remaining_liters, calories_pct,
                  protein_pct, fat_pct, carbs_pct, water_pct, entries_markdown,
                  source_file, updated_at
                from challenge.food_daily_status
                order by entry_date
                """
            )
            rows = cur.fetchall()
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame["entry_date"] = pd.to_datetime(frame["entry_date"]).dt.date
    return frame


@st.cache_data(ttl=60)
def load_recipes() -> tuple[pd.DataFrame, pd.DataFrame]:
    with psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select recipe_key, recipe_name, category, total_amount_g, calories,
                  protein_g, fat_g, carbs_g, fiber_g, notes, tags, updated_at
                from challenge.recipe_summaries_status
                order by recipe_name
                """
            )
            recipe_rows = cur.fetchall()
            cur.execute(
                """
                select recipe_key, recipe_name, category, sort_order, ingredient_key,
                  product_name, brand, amount_g, calories, protein_g, fat_g,
                  carbs_g, fiber_g, notes, tags, updated_at
                from challenge.recipe_ingredients_status
                order by recipe_name, sort_order, product_name
                """
            )
            ingredient_rows = cur.fetchall()
    return pd.DataFrame(recipe_rows), pd.DataFrame(ingredient_rows)


@st.cache_data(ttl=60)
def load_ingredients() -> pd.DataFrame:
    with psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select ingredient_key, product_name, brand, label_serving_text,
                  label_serving_g, regular_portion_g, calories_per_100g,
                  protein_g_per_100g, fat_g_per_100g, carbs_g_per_100g,
                  fiber_g_per_100g, sugar_g_per_100g, sodium_mg_per_100g,
                  nicknames, source_kind, source_detail, notes, updated_at
                from challenge.ingredients_status
                order by coalesce(brand, ''), product_name
                """
            )
            rows = cur.fetchall()
    return pd.DataFrame(rows)


@st.cache_data(ttl=60)
def load_todos() -> tuple[pd.DataFrame, pd.DataFrame]:
    with psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select task_key, title, status, priority, area, due_date, tags,
                  notes, source_file, created_at, updated_at, completed_at,
                  is_open, is_overdue
                from challenge.todos_status
                order by is_open desc, is_overdue desc, due_date nulls last, title
                """
            )
            todo_rows = cur.fetchall()
            cur.execute(
                """
                select event_key, task_key, title, event_type, event_at, details,
                  source_file, status, priority, area
                from challenge.todo_events_status
                order by event_at desc, event_key desc
                """
            )
            event_rows = cur.fetchall()
    return pd.DataFrame(todo_rows), pd.DataFrame(event_rows)


def save_forge_entry(payload: dict[str, Any]) -> None:
    steps_count = payload.get("steps_count")
    protein_g = payload.get("protein_g")
    water_liters = payload.get("water_liters")
    scale_available = payload.get("scale_available")
    weigh_in = payload.get("weigh_in") if scale_available else None
    weight = payload.get("weight") if scale_available and weigh_in else None

    steps_goal_hit = steps_count is not None and steps_count >= STEP_GOAL
    protein_goal_hit = protein_g is not None and protein_g >= PROTEIN_GOAL_G
    hydration_goal_hit = water_liters is not None and water_liters >= HYDRATION_GOAL_L

    strike_checks = [
        payload.get("workout_done"), steps_goal_hit, protein_goal_hit,
        payload.get("no_snacks_or_grazing"), payload.get("food_logged"),
        hydration_goal_hit, payload.get("creatine_taken"), payload.get("progress_photo"),
    ]
    strikes_today = sum(value is False for value in strike_checks)
    if scale_available and weigh_in is False:
        strikes_today += 1

    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update challenge.forge_daily
                set workout_done = %(workout_done)s, steps_count = %(steps_count)s,
                  steps_goal_hit = %(steps_goal_hit)s, protein_g = %(protein_g)s,
                  protein_goal_hit = %(protein_goal_hit)s,
                  no_snacks_or_grazing = %(no_snacks_or_grazing)s,
                  food_logged = %(food_logged)s, water_liters = %(water_liters)s,
                  hydration_goal_hit = %(hydration_goal_hit)s,
                  creatine_taken = %(creatine_taken)s,
                  progress_photo = %(progress_photo)s,
                  scale_available = %(scale_available)s, weigh_in = %(weigh_in)s,
                  weight = %(weight)s, weight_unit = %(weight_unit)s,
                  strikes_today = %(strikes_today)s, notes = %(notes)s
                where entry_date = %(entry_date)s
                """,
                {
                    **payload,
                    "steps_goal_hit": steps_goal_hit,
                    "protein_goal_hit": protein_goal_hit,
                    "hydration_goal_hit": hydration_goal_hit,
                    "weigh_in": weigh_in,
                    "weight": weight,
                    "strikes_today": strikes_today,
                    "weight_unit": payload.get("weight_unit") if weight is not None else None,
                },
            )
            cur.execute(
                """
                with running as (
                  select entry_date,
                    sum(coalesce(strikes_today, 0)) over (order by entry_date) as cumulative_strikes
                  from challenge.forge_daily
                )
                update challenge.forge_daily d
                set cumulative_strikes = r.cumulative_strikes
                from running r
                where d.entry_date = r.entry_date
                """
            )
    load_tracker.clear()
    load_food_daily.clear()
    load_recipes.clear()
