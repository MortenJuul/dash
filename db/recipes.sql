create schema if not exists challenge;

create table if not exists challenge.recipes (
  recipe_key text primary key,
  recipe_name text not null,
  category text,
  notes text,
  tags text[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists challenge.recipe_ingredients (
  recipe_key text not null references challenge.recipes(recipe_key) on delete cascade,
  ingredient_key text not null references challenge.ingredients(ingredient_key) on delete restrict,
  amount_g numeric(8,2) not null,
  sort_order integer not null default 1,
  notes text,
  primary key (recipe_key, ingredient_key, sort_order)
);

create index if not exists recipe_ingredients_recipe_idx on challenge.recipe_ingredients (recipe_key, sort_order);
create index if not exists recipe_ingredients_ingredient_idx on challenge.recipe_ingredients (ingredient_key);

create or replace function challenge.touch_recipes_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists recipes_touch_updated_at on challenge.recipes;
create trigger recipes_touch_updated_at
before update on challenge.recipes
for each row execute function challenge.touch_recipes_updated_at();

create or replace view challenge.recipe_ingredients_status as
select
  ri.recipe_key,
  r.recipe_name,
  r.category,
  ri.sort_order,
  ri.ingredient_key,
  i.product_name,
  i.brand,
  ri.amount_g,
  round((i.calories_per_100g * ri.amount_g / 100.0)::numeric, 2) as calories,
  round((i.protein_g_per_100g * ri.amount_g / 100.0)::numeric, 2) as protein_g,
  round((i.fat_g_per_100g * ri.amount_g / 100.0)::numeric, 2) as fat_g,
  round((i.carbs_g_per_100g * ri.amount_g / 100.0)::numeric, 2) as carbs_g,
  round((i.fiber_g_per_100g * ri.amount_g / 100.0)::numeric, 2) as fiber_g,
  ri.notes,
  r.tags,
  r.updated_at
from challenge.recipe_ingredients ri
join challenge.recipes r on r.recipe_key = ri.recipe_key
join challenge.ingredients i on i.ingredient_key = ri.ingredient_key
order by r.recipe_name, ri.sort_order, i.product_name;

drop view if exists challenge.recipe_summaries_status;
create view challenge.recipe_summaries_status as
select
  r.recipe_key,
  r.recipe_name,
  r.category,
  coalesce(sum(ri.amount_g), 0)::numeric(10,2) as total_amount_g,
  round(coalesce(sum(ris.calories), 0)::numeric, 2) as calories,
  round(coalesce(sum(ris.protein_g), 0)::numeric, 2) as protein_g,
  round(coalesce(sum(ris.fat_g), 0)::numeric, 2) as fat_g,
  round(coalesce(sum(ris.carbs_g), 0)::numeric, 2) as carbs_g,
  round(coalesce(sum(ris.fiber_g), 0)::numeric, 2) as fiber_g,
  r.notes,
  r.tags,
  r.updated_at
from challenge.recipes r
left join challenge.recipe_ingredients ri on ri.recipe_key = r.recipe_key
left join challenge.recipe_ingredients_status ris on ris.recipe_key = ri.recipe_key and ris.ingredient_key = ri.ingredient_key and ris.sort_order = ri.sort_order
group by r.recipe_key, r.recipe_name, r.category, r.notes, r.tags, r.updated_at
order by r.recipe_name;
