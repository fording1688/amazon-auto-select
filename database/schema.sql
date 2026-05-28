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

create table if not exists import_batches (
  id bigserial primary key,
  report_type text not null,
  file_name text not null,
  marketplace text default 'US',
  uploaded_by text,
  uploaded_at timestamptz default now(),
  period_start date,
  period_end date,
  duplicate_strategy text,
  duplicate_count integer default 0,
  row_count integer default 0,
  status text default 'success',
  error_message text,
  created_at timestamptz default now()
);
create index if not exists idx_import_batches_type on import_batches(report_type);
create index if not exists idx_import_batches_uploaded_at on import_batches(uploaded_at);

create table if not exists sales_daily (
  id bigserial primary key,
  import_batch_id bigint references import_batches(id),
  marketplace text default 'US',
  sku text,
  asin text,
  date date,
  report_date date,
  period_start date,
  period_end date,
  is_active boolean default true,
  data_hash text,
  sales numeric,
  orders numeric,
  units numeric,
  sessions numeric,
  conversion_rate numeric,
  raw_json jsonb,
  created_at timestamptz default now()
);
create index if not exists idx_sales_daily_active_hash on sales_daily(is_active, data_hash);

create table if not exists ads_daily (
  id bigserial primary key,
  import_batch_id bigint references import_batches(id),
  marketplace text default 'US',
  sku text,
  asin text,
  campaign_name text,
  date date,
  report_date date,
  period_start date,
  period_end date,
  is_active boolean default true,
  data_hash text,
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
create index if not exists idx_ads_daily_active_hash on ads_daily(is_active, data_hash);

create table if not exists search_terms (
  id bigserial primary key,
  import_batch_id bigint references import_batches(id),
  marketplace text default 'US',
  sku text,
  asin text,
  campaign_name text,
  ad_group_name text,
  targeting text,
  match_type text,
  customer_search_term text,
  date date,
  report_date date,
  period_start date,
  period_end date,
  is_active boolean default true,
  data_hash text,
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
create index if not exists idx_search_terms_active_hash on search_terms(is_active, data_hash);

create table if not exists inventory_daily (
  id bigserial primary key,
  import_batch_id bigint references import_batches(id),
  marketplace text default 'US',
  sku text,
  asin text,
  date date,
  report_date date,
  period_start date,
  period_end date,
  is_active boolean default true,
  data_hash text,
  available numeric,
  inbound numeric,
  reserved numeric,
  days_of_supply numeric,
  raw_json jsonb,
  created_at timestamptz default now()
);
create index if not exists idx_inventory_daily_active_hash on inventory_daily(is_active, data_hash);

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
