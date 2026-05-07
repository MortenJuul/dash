create schema if not exists challenge;

create table if not exists challenge.forge_daily (
  entry_date date primary key,
  week_no integer not null,
  block_no integer not null,
  day_name text not null,
  planned_session text,
  workout_done boolean,
  steps_count integer,
  steps_goal_hit boolean,
  protein_g numeric(6,2),
  protein_goal_hit boolean,
  no_snacks_or_grazing boolean,
  food_logged boolean,
  water_liters numeric(5,2),
  hydration_goal_hit boolean,
  creatine_taken boolean,
  progress_photo boolean,
  scale_available boolean,
  weigh_in boolean,
  weight numeric(7,2),
  weight_unit text,
  bmi numeric(5,2),
  body_fat_pct numeric(5,2),
  subcutaneous_fat_pct numeric(5,2),
  visceral_fat numeric(5,2),
  skeletal_muscle_pct numeric(5,2),
  muscle_mass_kg numeric(7,2),
  fat_free_body_weight_kg numeric(7,2),
  body_water_pct numeric(5,2),
  bone_mass_kg numeric(6,2),
  protein_pct numeric(5,2),
  bmr_kcal integer,
  metabolic_age integer,
  strikes_today integer,
  cumulative_strikes integer,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists forge_daily_week_idx on challenge.forge_daily (week_no, entry_date);
create index if not exists forge_daily_block_idx on challenge.forge_daily (block_no, entry_date);

alter table challenge.forge_daily add column if not exists bmi numeric(5,2);
alter table challenge.forge_daily add column if not exists body_fat_pct numeric(5,2);
alter table challenge.forge_daily add column if not exists subcutaneous_fat_pct numeric(5,2);
alter table challenge.forge_daily add column if not exists visceral_fat numeric(5,2);
alter table challenge.forge_daily add column if not exists skeletal_muscle_pct numeric(5,2);
alter table challenge.forge_daily add column if not exists muscle_mass_kg numeric(7,2);
alter table challenge.forge_daily add column if not exists fat_free_body_weight_kg numeric(7,2);
alter table challenge.forge_daily add column if not exists body_water_pct numeric(5,2);
alter table challenge.forge_daily add column if not exists bone_mass_kg numeric(6,2);
alter table challenge.forge_daily add column if not exists protein_pct numeric(5,2);
alter table challenge.forge_daily add column if not exists bmr_kcal integer;
alter table challenge.forge_daily add column if not exists metabolic_age integer;

create or replace function challenge.touch_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists forge_daily_touch_updated_at on challenge.forge_daily;
create trigger forge_daily_touch_updated_at
before update on challenge.forge_daily
for each row execute function challenge.touch_updated_at();

drop view if exists challenge.forge_daily_status;
create view challenge.forge_daily_status as
select
  entry_date,
  week_no,
  block_no,
  day_name,
  planned_session,
  workout_done,
  steps_count,
  steps_goal_hit,
  protein_g,
  protein_goal_hit,
  no_snacks_or_grazing,
  food_logged,
  water_liters,
  hydration_goal_hit,
  creatine_taken,
  progress_photo,
  scale_available,
  weigh_in,
  weight,
  weight_unit,
  bmi,
  body_fat_pct,
  subcutaneous_fat_pct,
  visceral_fat,
  skeletal_muscle_pct,
  muscle_mass_kg,
  fat_free_body_weight_kg,
  body_water_pct,
  bone_mass_kg,
  protein_pct,
  bmr_kcal,
  metabolic_age,
  strikes_today,
  cumulative_strikes,
  (
    coalesce((workout_done is true)::int, 0)
    + coalesce((steps_goal_hit is true)::int, 0)
    + coalesce((protein_goal_hit is true)::int, 0)
    + coalesce((no_snacks_or_grazing is true)::int, 0)
    + coalesce((food_logged is true)::int, 0)
    + coalesce((hydration_goal_hit is true)::int, 0)
    + coalesce((creatine_taken is true)::int, 0)
    + coalesce((progress_photo is true)::int, 0)
    + coalesce((case when scale_available is true then (weigh_in is true)::int else 0 end), 0)
  ) as completed_checks,
  notes,
  updated_at
from challenge.forge_daily
order by entry_date;
