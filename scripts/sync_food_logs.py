#!/usr/bin/env python3
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOOD_LOG_DIR = Path(os.environ.get('FOOD_LOG_DIR', '/home/morty/.openclaw/workspace/food-log')).expanduser()
DB_URL = os.environ.get('FOOD_DATABASE_URL') or os.environ.get('FORGE_DATABASE_URL') or os.environ.get('DATABASE_URL')

if not DB_URL:
    print('FOOD_DATABASE_URL, FORGE_DATABASE_URL, or DATABASE_URL is required', file=sys.stderr)
    sys.exit(2)

if not FOOD_LOG_DIR.exists():
    print(f'Food log directory not found: {FOOD_LOG_DIR}', file=sys.stderr)
    sys.exit(2)

SECTION_RE = re.compile(r'^##\s+(.+?)\s*$', re.MULTILINE)
LINE_RE = re.compile(r'^-\s+([^:]+):\s+(.+?)\s*$', re.MULTILINE)
NUMBER_RE = re.compile(r'-?\d+(?:\.\d+)?')


def sql_num(value):
    return str(value) if value is not None else 'null'


def sql_text(value: str | None) -> str:
    if value is None:
        return 'null'
    value = value.strip()
    if not value:
        return 'null'
    return "'" + value.replace("'", "''") + "'"


def parse_first_number(value: str):
    if not value:
        return None
    match = NUMBER_RE.search(value)
    if not match:
        return None
    number = float(match.group(0))
    if number.is_integer():
        return int(number)
    return number


def parse_range(value: str):
    if not value:
        return (None, None)
    numbers = [float(part) for part in NUMBER_RE.findall(value)]
    if not numbers:
        return (None, None)
    if len(numbers) == 1:
        return (numbers[0], numbers[0])
    return (numbers[0], numbers[1])


def section_map(content: str):
    matches = list(SECTION_RE.finditer(content))
    sections = {}
    for index, match in enumerate(matches):
        name = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        sections[name] = content[start:end].strip()
    return sections


def bullet_map(section_body: str):
    return {match.group(1).strip(): match.group(2).strip() for match in LINE_RE.finditer(section_body or '')}


def entry_markdown(content: str):
    entry_start = content.find('## Entries')
    if entry_start == -1:
        entry_start = content.find('## Entry 1')
    if entry_start == -1:
        return None
    return content[entry_start:].strip()


rows = []
for path in sorted(FOOD_LOG_DIR.glob('*.md')):
    if path.name == 'README.md':
        continue
    content = path.read_text(encoding='utf-8')
    sections = section_map(content)
    targets = bullet_map(sections.get('Daily Targets', ''))
    totals = bullet_map(sections.get('Running Totals So Far', ''))
    remaining = bullet_map(sections.get('Remaining For Today', ''))

    fiber_target_low, fiber_target_high = parse_range(targets.get('Fiber', ''))
    fiber_remaining_low, fiber_remaining_high = parse_range(remaining.get('Fiber', ''))

    rows.append({
        'entry_date': path.stem,
        'calories_target': parse_first_number(targets.get('Calories', '')),
        'protein_target_g': parse_first_number(targets.get('Protein', '')),
        'fat_target_g': parse_first_number(targets.get('Fat', '')),
        'carbs_target_g': parse_first_number(targets.get('Carbohydrates', '')),
        'fiber_target_g_low': fiber_target_low,
        'fiber_target_g_high': fiber_target_high,
        'water_target_liters': parse_first_number(targets.get('Water', '')),
        'calories': parse_first_number(totals.get('Calories', '')),
        'protein_g': parse_first_number(totals.get('Protein', '')),
        'fat_g': parse_first_number(totals.get('Fat', '')),
        'carbs_g': parse_first_number(totals.get('Carbohydrates', '')),
        'fiber_g': parse_first_number(totals.get('Fiber', '')),
        'water_liters': parse_first_number(totals.get('Water', '')),
        'calories_remaining': parse_first_number(remaining.get('Calories', '')),
        'protein_remaining_g': parse_first_number(remaining.get('Protein', '')),
        'fat_remaining_g': parse_first_number(remaining.get('Fat', '')),
        'carbs_remaining_g': parse_first_number(remaining.get('Carbohydrates', '')),
        'fiber_remaining_g_low': fiber_remaining_low,
        'fiber_remaining_g_high': fiber_remaining_high,
        'water_remaining_liters': parse_first_number(remaining.get('Water', '')),
        'entries_markdown': entry_markdown(content),
        'source_file': str(path),
    })

values = []
for row in rows:
    values.append('(' + ', '.join([
        sql_text(row['entry_date']),
        sql_num(row['calories_target']),
        sql_num(row['protein_target_g']),
        sql_num(row['fat_target_g']),
        sql_num(row['carbs_target_g']),
        sql_num(row['fiber_target_g_low']),
        sql_num(row['fiber_target_g_high']),
        sql_num(row['water_target_liters']),
        sql_num(row['calories']),
        sql_num(row['protein_g']),
        sql_num(row['fat_g']),
        sql_num(row['carbs_g']),
        sql_num(row['fiber_g']),
        sql_num(row['water_liters']),
        sql_num(row['calories_remaining']),
        sql_num(row['protein_remaining_g']),
        sql_num(row['fat_remaining_g']),
        sql_num(row['carbs_remaining_g']),
        sql_num(row['fiber_remaining_g_low']),
        sql_num(row['fiber_remaining_g_high']),
        sql_num(row['water_remaining_liters']),
        sql_text(row['entries_markdown']),
        sql_text(row['source_file']),
    ]) + ')')

sql = """
insert into challenge.food_daily (
  entry_date,
  calories_target,
  protein_target_g,
  fat_target_g,
  carbs_target_g,
  fiber_target_g_low,
  fiber_target_g_high,
  water_target_liters,
  calories,
  protein_g,
  fat_g,
  carbs_g,
  fiber_g,
  water_liters,
  calories_remaining,
  protein_remaining_g,
  fat_remaining_g,
  carbs_remaining_g,
  fiber_remaining_g_low,
  fiber_remaining_g_high,
  water_remaining_liters,
  entries_markdown,
  source_file
)
values
{values}
on conflict (entry_date) do update set
  calories_target = excluded.calories_target,
  protein_target_g = excluded.protein_target_g,
  fat_target_g = excluded.fat_target_g,
  carbs_target_g = excluded.carbs_target_g,
  fiber_target_g_low = excluded.fiber_target_g_low,
  fiber_target_g_high = excluded.fiber_target_g_high,
  water_target_liters = excluded.water_target_liters,
  calories = excluded.calories,
  protein_g = excluded.protein_g,
  fat_g = excluded.fat_g,
  carbs_g = excluded.carbs_g,
  fiber_g = excluded.fiber_g,
  water_liters = excluded.water_liters,
  calories_remaining = excluded.calories_remaining,
  protein_remaining_g = excluded.protein_remaining_g,
  fat_remaining_g = excluded.fat_remaining_g,
  carbs_remaining_g = excluded.carbs_remaining_g,
  fiber_remaining_g_low = excluded.fiber_remaining_g_low,
  fiber_remaining_g_high = excluded.fiber_remaining_g_high,
  water_remaining_liters = excluded.water_remaining_liters,
  entries_markdown = excluded.entries_markdown,
  source_file = excluded.source_file;
""".format(values=',\n'.join(values))

subprocess.run(['psql', DB_URL, '-v', 'ON_ERROR_STOP=1', '-q'], input=sql, text=True, check=True)
print(f'Synced {len(rows)} food log rows to Postgres from {FOOD_LOG_DIR}.')
