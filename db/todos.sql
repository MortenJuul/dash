create schema if not exists challenge;

create table if not exists challenge.todos (
  task_key text primary key,
  title text not null,
  status text not null,
  priority text,
  area text,
  due_date date,
  tags text[] not null default '{}',
  notes text,
  source_file text not null,
  created_at timestamptz,
  updated_at timestamptz,
  completed_at timestamptz
);

create table if not exists challenge.todo_events (
  event_key text primary key,
  task_key text not null references challenge.todos(task_key) on delete cascade,
  event_type text not null,
  event_at timestamptz not null,
  details text,
  source_file text not null
);

create index if not exists todos_status_idx on challenge.todos (status, priority, due_date);
create index if not exists todos_area_idx on challenge.todos (area, status);
create index if not exists todos_tags_idx on challenge.todos using gin (tags);
create index if not exists todo_events_task_idx on challenge.todo_events (task_key, event_at desc);

create or replace view challenge.todos_status as
select
  task_key,
  title,
  status,
  priority,
  area,
  due_date,
  tags,
  notes,
  source_file,
  created_at,
  updated_at,
  completed_at,
  (status in ('todo', 'in_progress', 'blocked')) as is_open,
  (due_date is not null and due_date < current_date and status not in ('done', 'cancelled')) as is_overdue
from challenge.todos
order by
  case status
    when 'in_progress' then 1
    when 'blocked' then 2
    when 'todo' then 3
    when 'done' then 4
    when 'cancelled' then 5
    else 99
  end,
  due_date nulls last,
  priority nulls last,
  title;

create or replace view challenge.todo_events_status as
select
  e.event_key,
  e.task_key,
  t.title,
  e.event_type,
  e.event_at,
  e.details,
  e.source_file,
  t.status,
  t.priority,
  t.area
from challenge.todo_events e
join challenge.todos t on t.task_key = e.task_key
order by e.event_at desc, e.event_key desc;
