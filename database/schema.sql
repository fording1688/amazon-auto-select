-- Amazon Seller Growth Copilot MVP schema
-- Supabase PostgreSQL compatible.

create table if not exists products (
  id bigserial primary key,
  sku text,
  asin text,
  title text not null default '',
  price numeric,
  status text default 'active',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create index if not exists idx_products_sku on products(sku);
create index if not exists idx_products_asin on products(asin);

create table if not exists sales_daily (
  id bigserial primary key,
  sku text,
  asin text,
  date date,
  sales numeric,
  orders numeric,
  units numeric,
  sessions numeric,
  conversion_rate numeric,
  raw_json jsonb,
  created_at timestamptz default now()
);

create table if not exists ads_daily (
  id bigserial primary key,
  sku text,
  asin text,
  campaign_name text,
  date date,
  impressions numeric,
  clicks numeric,
  spend numeric,
  sales numeric,
  orders numeric,
  acos numeric,
  cpc numeric,
  raw_json jsonb,
  created_at timestamptz default now()
);

create table if not exists search_terms (
  id bigserial primary key,
  sku text,
  asin text,
  campaign_name text,
  ad_group_name text,
  targeting text,
  match_type text,
  customer_search_term text,
  date date,
  impressions numeric,
  clicks numeric,
  spend numeric,
  sales numeric,
  orders numeric,
  acos numeric,
  cpc numeric,
  conversion_rate numeric,
  diagnosis text,
  raw_json jsonb,
  created_at timestamptz default now()
);

create table if not exists inventory_daily (
  id bigserial primary key,
  sku text,
  asin text,
  date date,
  available numeric,
  inbound numeric,
  reserved numeric,
  days_of_supply numeric,
  raw_json jsonb,
  created_at timestamptz default now()
);

create table if not exists competitor_products (
  id bigserial primary key,
  asin text,
  keyword text,
  title text,
  brand text,
  price numeric,
  rating numeric,
  review_count integer,
  product_url text,
  raw_json jsonb,
  created_at timestamptz default now()
);

create table if not exists recommendations (
  id bigserial primary key,
  sku text,
  asin text,
  recommendation_type text not null,
  priority text default 'P2',
  title text default '',
  content text,
  status text default 'pending',
  source_json jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
