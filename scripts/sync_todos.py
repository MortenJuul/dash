#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path

TODO_FILE = Path(os.environ.get('TODO_FILE', '/home/morty/.openclaw/workspace/todo/todos.json')).expanduser()
TODO_EVENTS_FILE = Path(os.environ.get('TODO_EVENTS_FILE', '/home/morty/.openclaw/workspace/todo/todo-events.jsonl')).expanduser()
DB_URL = os.environ.get('TODO_DATABASE_URL') or os.environ.get('FORGE_DATABASE_URL') or os.environ.get('DATABASE_URL')

if not DB_URL:
    print('TODO_DATABASE_URL, FORGE_DATABASE_URL, or DATABASE_URL is required', file=sys.stderr)
    sys.exit(2)

if not TODO_FILE.exists():
    print(f'Todo file not found: {TODO_FILE}', file=sys.stderr)
    sys.exit(2)

if not TODO_EVENTS_FILE.exists():
    print(f'Todo events file not found: {TODO_EVENTS_FILE}', file=sys.stderr)
    sys.exit(2)


def sql_text(value):
    if value is None:
        return 'null'
    value = str(value).strip()
    if value == '':
        return 'null'
    return "'" + value.replace("'", "''") + "'"


def sql_date(value):
    return sql_text(value)


def sql_timestamptz(value):
    return sql_text(value)


def sql_tags(values):
    if not values:
        return "'{}'::text[]"
    escaped = [v.replace('\\', '\\\\').replace('"', '\\"') for v in values]
    return "ARRAY[" + ", ".join(sql_text(v) for v in escaped) + "]::text[]"


with TODO_FILE.open(encoding='utf-8') as f:
    tasks = json.load(f)

with TODO_EVENTS_FILE.open(encoding='utf-8') as f:
    events = [json.loads(line) for line in f if line.strip()]

task_values = []
for task in tasks:
    task_values.append('(' + ', '.join([
        sql_text(task.get('task_key')),
        sql_text(task.get('title')),
        sql_text(task.get('status')),
        sql_text(task.get('priority')),
        sql_text(task.get('area')),
        sql_date(task.get('due_date')),
        sql_tags(task.get('tags') or []),
        sql_text(task.get('notes')),
        sql_text(str(TODO_FILE)),
        sql_timestamptz(task.get('created_at')),
        sql_timestamptz(task.get('updated_at')),
        sql_timestamptz(task.get('completed_at')),
    ]) + ')')

event_values = []
for event in events:
    event_values.append('(' + ', '.join([
        sql_text(event.get('event_key')),
        sql_text(event.get('task_key')),
        sql_text(event.get('event_type')),
        sql_timestamptz(event.get('event_at')),
        sql_text(event.get('details')),
        sql_text(str(TODO_EVENTS_FILE)),
    ]) + ')')

sql_parts = [
    'delete from challenge.todo_events where source_file = {events_file};'.format(events_file=sql_text(str(TODO_EVENTS_FILE))),
    'delete from challenge.todos where source_file = {tasks_file};'.format(tasks_file=sql_text(str(TODO_FILE))),
]

if task_values:
    sql_parts.append("""
insert into challenge.todos (
  task_key, title, status, priority, area, due_date, tags, notes, source_file, created_at, updated_at, completed_at
)
values
{values};
""".format(values=',\n'.join(task_values)))

if event_values:
    sql_parts.append("""
insert into challenge.todo_events (
  event_key, task_key, event_type, event_at, details, source_file
)
values
{values};
""".format(values=',\n'.join(event_values)))

sql = '\n'.join(sql_parts)
subprocess.run(['psql', DB_URL, '-v', 'ON_ERROR_STOP=1', '-q'], input=sql, text=True, check=True)
print(f'Synced {len(tasks)} todo rows and {len(events)} todo events to Postgres.')
