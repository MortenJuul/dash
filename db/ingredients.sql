create schema if not exists challenge;

create table if not exists challenge.ingredients (
  ingredient_key text primary key,
  product_name text not null,
  brand text,
  label_serving_text text,
  label_serving_g numeric(7,2),
  regular_portion_g numeric(7,2),
  calories_per_100g numeric(8,2),
  protein_g_per_100g numeric(8,2),
  fat_g_per_100g numeric(8,2),
  carbs_g_per_100g numeric(8,2),
  fiber_g_per_100g numeric(8,2),
  sugar_g_per_100g numeric(8,2),
  sodium_mg_per_100g numeric(8,2),
  nicknames text[] not null default '{}',
  source_kind text,
  source_detail text,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table challenge.ingredients add column if not exists label_serving_text text;
alter table challenge.ingredients add column if not exists label_serving_g numeric(7,2);
alter table challenge.ingredients add column if not exists regular_portion_g numeric(7,2);
alter table challenge.ingredients add column if not exists calories_per_100g numeric(8,2);
alter table challenge.ingredients add column if not exists protein_g_per_100g numeric(8,2);
alter table challenge.ingredients add column if not exists fat_g_per_100g numeric(8,2);
alter table challenge.ingredients add column if not exists carbs_g_per_100g numeric(8,2);
alter table challenge.ingredients add column if not exists fiber_g_per_100g numeric(8,2);
alter table challenge.ingredients add column if not exists sugar_g_per_100g numeric(8,2);
alter table challenge.ingredients add column if not exists sodium_mg_per_100g numeric(8,2);

create index if not exists ingredients_product_name_idx on challenge.ingredients (product_name);
create index if not exists ingredients_brand_idx on challenge.ingredients (brand, product_name);
create index if not exists ingredients_nicknames_idx on challenge.ingredients using gin (nicknames);

create or replace function challenge.touch_ingredients_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists ingredients_touch_updated_at on challenge.ingredients;
create trigger ingredients_touch_updated_at
before update on challenge.ingredients
for each row execute function challenge.touch_ingredients_updated_at();

drop view if exists challenge.ingredients_status;
create view challenge.ingredients_status as
select
  ingredient_key,
  product_name,
  brand,
  label_serving_text,
  label_serving_g,
  regular_portion_g,
  calories_per_100g,
  protein_g_per_100g,
  fat_g_per_100g,
  carbs_g_per_100g,
  fiber_g_per_100g,
  sugar_g_per_100g,
  sodium_mg_per_100g,
  nicknames,
  source_kind,
  source_detail,
  notes,
  updated_at
from challenge.ingredients
order by coalesce(brand, ''), product_name;
