#!/usr/bin/env python3
import csv
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = Path(os.environ.get('FORGE_TRACKER_CSV', '/home/morty/.openclaw/workspace/fitness/forge-tracker.csv')).expanduser()
DB_URL = os.environ.get('FORGE_DATABASE_URL') or os.environ.get('DATABASE_URL')

if not DB_URL:
    print('FORGE_DATABASE_URL or DATABASE_URL is required', file=sys.stderr)
    sys.exit(2)

if not CSV_PATH.exists():
    print(f'Forge tracker CSV not found: {CSV_PATH}', file=sys.stderr)
    sys.exit(2)


def sql_bool(value: str) -> str:
    value = (value or '').strip().lower()
    if value in {'true', 't', '1', 'yes', 'y'}:
        return 'true'
    if value in {'false', 'f', '0', 'no', 'n'}:
        return 'false'
    return 'null'


def sql_num(value: str) -> str:
    value = (value or '').strip()
    return value if value else 'null'


def sql_int(value: str) -> str:
    value = (value or '').strip()
    return value if value else 'null'


def sql_text(value: str) -> str:
    if value is None:
        return 'null'
    value = value.strip()
    if value == '':
        return 'null'
    return "'" + value.replace("'", "''") + "'"


def get(row: dict[str, str], key: str) -> str:
    return row.get(key, '')

rows = []
with CSV_PATH.open(newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)

values = []
for row in rows:
    values.append("(" + ", ".join([
        sql_text(row['date']),
        sql_int(row['week']),
        sql_int(row['block']),
        sql_text(row['day']),
        sql_text(row['planned_session']),
        sql_bool(row['workout_done']),
        'null',
        sql_bool(row['steps_8k']),
        'null',
        sql_bool(row['protein_150g']),
        sql_bool(row['no_snacks_or_grazing']),
        sql_bool(row['food_logged']),
        sql_num(row['water_liters']),
        sql_bool(row['hydration_3l']),
        sql_bool(row['creatine_3_to_5g']),
        sql_bool(row['progress_photo']),
        sql_bool(get(row, 'scale_available')),
        sql_bool(row['weigh_in']),
        sql_num(row['weight']),
        sql_text(get(row, 'weight_unit')),
        sql_int(row['strikes_today']),
        sql_int(row['cumulative_strikes']),
        sql_text(row['notes']),
    ]) + ")")

sql = """
insert into challenge.forge_daily (
  entry_date, week_no, block_no, day_name, planned_session,
  workout_done, steps_count, steps_goal_hit, protein_g, protein_goal_hit,
  no_snacks_or_grazing, food_logged, water_liters, hydration_goal_hit,
  creatine_taken, progress_photo, scale_available, weigh_in, weight, weight_unit,
  strikes_today, cumulative_strikes, notes
)
values
{values}
on conflict (entry_date) do update set
  week_no = excluded.week_no,
  block_no = excluded.block_no,
  day_name = excluded.day_name,
  planned_session = excluded.planned_session,
  workout_done = excluded.workout_done,
  steps_goal_hit = excluded.steps_goal_hit,
  protein_goal_hit = excluded.protein_goal_hit,
  no_snacks_or_grazing = excluded.no_snacks_or_grazing,
  food_logged = excluded.food_logged,
  water_liters = excluded.water_liters,
  hydration_goal_hit = excluded.hydration_goal_hit,
  creatine_taken = excluded.creatine_taken,
  progress_photo = excluded.progress_photo,
  scale_available = excluded.scale_available,
  weigh_in = excluded.weigh_in,
  weight = excluded.weight,
  weight_unit = excluded.weight_unit,
  strikes_today = excluded.strikes_today,
  cumulative_strikes = excluded.cumulative_strikes,
  notes = excluded.notes;
""".format(values=",\n".join(values))

subprocess.run(['psql', DB_URL, '-v', 'ON_ERROR_STOP=1', '-q'], input=sql, text=True, check=True)
print(f'Synced {len(rows)} Forge rows to Postgres from {CSV_PATH}.')
