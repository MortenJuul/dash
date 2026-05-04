create schema if not exists challenge;

create table if not exists challenge.food_daily (
  entry_date date primary key,
  calories_target integer,
  protein_target_g numeric(6,2),
  fat_target_g numeric(6,2),
  carbs_target_g numeric(6,2),
  fiber_target_g_low numeric(6,2),
  fiber_target_g_high numeric(6,2),
  water_target_liters numeric(5,2),
  calories integer,
  protein_g numeric(6,2),
  fat_g numeric(6,2),
  carbs_g numeric(6,2),
  fiber_g numeric(6,2),
  water_liters numeric(5,2),
  calories_remaining integer,
  protein_remaining_g numeric(6,2),
  fat_remaining_g numeric(6,2),
  carbs_remaining_g numeric(6,2),
  fiber_remaining_g_low numeric(6,2),
  fiber_remaining_g_high numeric(6,2),
  water_remaining_liters numeric(5,2),
  entries_markdown text,
  source_file text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists food_daily_date_idx on challenge.food_daily (entry_date);

create or replace function challenge.touch_food_daily_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists food_daily_touch_updated_at on challenge.food_daily;
create trigger food_daily_touch_updated_at
before update on challenge.food_daily
for each row execute function challenge.touch_food_daily_updated_at();

create or replace view challenge.food_daily_status as
select
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
  case when calories_target > 0 and calories is not null then round((calories::numeric / calories_target) * 100, 1) end as calories_pct,
  case when protein_target_g > 0 and protein_g is not null then round((protein_g / protein_target_g) * 100, 1) end as protein_pct,
  case when fat_target_g > 0 and fat_g is not null then round((fat_g / fat_target_g) * 100, 1) end as fat_pct,
  case when carbs_target_g > 0 and carbs_g is not null then round((carbs_g / carbs_target_g) * 100, 1) end as carbs_pct,
  case when water_target_liters > 0 and water_liters is not null then round((water_liters / water_target_liters) * 100, 1) end as water_pct,
  entries_markdown,
  source_file,
  updated_at
from challenge.food_daily
order by entry_date;
