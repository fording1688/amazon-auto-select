-- Amazon Seller Growth Copilot MVP schema
-- Supabase PostgreSQL compatible.

create table if not exists users (
  id bigserial primary key,
  email text not null unique,
  name text,
  password_hash text not null,
  status text default 'active',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create index if not exists idx_users_email on users(email);
create index if not exists idx_users_status on users(status);

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

create table if not exists stores (
  id bigserial primary key,
  user_id bigint references users(id),
  name text not null,
  marketplace text default 'US',
  status text default 'active',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create index if not exists idx_stores_user_id on stores(user_id);
create index if not exists idx_stores_name on stores(name);
create index if not exists idx_stores_marketplace on stores(marketplace);

create table if not exists import_batches (
  id bigserial primary key,
  user_id bigint references users(id),
  store_id bigint references stores(id),
  store_name text,
  business_date date,
  project_name text,
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
create index if not exists idx_import_batches_user_id on import_batches(user_id);
create index if not exists idx_import_batches_type on import_batches(report_type);
create index if not exists idx_import_batches_uploaded_at on import_batches(uploaded_at);
create index if not exists idx_import_batches_store_date on import_batches(store_id, business_date);

create table if not exists sales_daily (
  id bigserial primary key,
  user_id bigint references users(id),
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
create index if not exists idx_sales_daily_user_id on sales_daily(user_id);
create index if not exists idx_sales_daily_active_hash on sales_daily(is_active, data_hash);

create table if not exists ads_daily (
  id bigserial primary key,
  user_id bigint references users(id),
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
create index if not exists idx_ads_daily_user_id on ads_daily(user_id);
create index if not exists idx_ads_daily_active_hash on ads_daily(is_active, data_hash);

create table if not exists search_terms (
  id bigserial primary key,
  user_id bigint references users(id),
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
create index if not exists idx_search_terms_user_id on search_terms(user_id);
create index if not exists idx_search_terms_active_hash on search_terms(is_active, data_hash);

create table if not exists inventory_daily (
  id bigserial primary key,
  user_id bigint references users(id),
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
create index if not exists idx_inventory_daily_user_id on inventory_daily(user_id);
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
  user_id bigint references users(id),
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
create index if not exists idx_recommendations_user_id on recommendations(user_id);

create table if not exists listing_projects (
  id bigserial primary key,
  user_id bigint references users(id),
  project_name text not null,
  marketplace text default 'US',
  brand text,
  category text,
  product_name text,
  target_price numeric,
  fulfillment_method text,
  status text default 'draft',
  notes text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create index if not exists idx_listing_projects_user_id on listing_projects(user_id);
create index if not exists idx_listing_projects_status on listing_projects(status);

create table if not exists listing_project_inputs (
  id bigserial primary key,
  project_id bigint references listing_projects(id),
  size text,
  material text,
  color text,
  quantity text,
  compatibility text,
  package_includes text,
  not_included text,
  warning_limitation text,
  use_cases text,
  target_customer text,
  buyer_type text,
  advantages text,
  difference_from_competitors text,
  main_keywords text,
  secondary_keywords text,
  long_tail_keywords text,
  compatibility_keywords text,
  keywords_to_avoid text,
  forbidden_words text,
  compliance_notes text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists competitor_references (
  id bigserial primary key,
  project_id bigint references listing_projects(id),
  competitor_url text,
  competitor_title text,
  competitor_bullets text,
  competitor_description text,
  competitor_price numeric,
  competitor_rating numeric,
  competitor_review_count integer,
  competitor_image_notes text,
  competitor_aplus_notes text,
  what_to_reference text,
  what_to_avoid text,
  created_at timestamptz default now()
);

create table if not exists listing_versions (
  id bigserial primary key,
  project_id bigint references listing_projects(id),
  version_name text,
  title text,
  bullet_1 text,
  bullet_2 text,
  bullet_3 text,
  bullet_4 text,
  bullet_5 text,
  description text,
  backend_search_terms text,
  seo_score numeric,
  conversion_score numeric,
  compliance_risk_notes text,
  generation_notes text,
  created_at timestamptz default now()
);

create table if not exists image_prompt_versions (
  id bigserial primary key,
  project_id bigint references listing_projects(id),
  version_name text,
  image_type text,
  image_goal text,
  required_reference_images text,
  reference_usage_notes text,
  image_text text,
  prompt_en text,
  prompt_cn text,
  negative_prompt text,
  size_recommendation text,
  notes text,
  created_at timestamptz default now()
);

create table if not exists aplus_versions (
  id bigserial primary key,
  project_id bigint references listing_projects(id),
  version_name text,
  banner_copy text,
  brand_story_copy text,
  feature_modules text,
  specification_module text,
  application_module text,
  comparison_chart text,
  image_prompt_notes text,
  created_at timestamptz default now()
);
