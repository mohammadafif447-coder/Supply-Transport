-- 0001_init.sql
-- Skema inti Platform Logistik B2B (MVP) — lihat docs/03-SDD.md §2 untuk penjelasan.

create extension if not exists "pgcrypto";

-- ============================================================
-- ENUM TYPES
-- ============================================================
create type user_role as enum ('company', 'admin', 'driver');
create type order_status as enum ('pending','assigned','picked_up','in_transit','delivered','cancelled');
create type driver_status as enum ('pending_review','approved','rejected','suspended');
create type cargo_type as enum ('general','fragile','frozen','hazardous','document');
create type vehicle_type as enum ('motor','pickup','box_small','box_medium','truck_cdd','truck_cdd_long','truck_fuso','truck_trailer');

-- ============================================================
-- 1. profiles — extends auth.users dengan role & data umum
-- ============================================================
create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  role user_role not null,
  full_name text not null,
  phone_number text unique,
  avatar_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Auto-create row profiles saat user baru daftar via Supabase Auth.
-- Role & full_name diambil dari raw_user_meta_data yang dikirim saat signUp().
create function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, role, full_name, phone_number)
  values (
    new.id,
    coalesce((new.raw_user_meta_data->>'role')::user_role, 'company'),
    coalesce(new.raw_user_meta_data->>'full_name', ''),
    new.raw_user_meta_data->>'phone_number'
  );
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- ============================================================
-- 2. companies — profil perusahaan klien (shipper)
-- ============================================================
create table companies (
  id uuid primary key default gen_random_uuid(),
  owner_profile_id uuid not null references profiles(id),
  company_name text not null,
  company_address text not null,
  tax_id text,
  billing_email text,
  created_at timestamptz not null default now()
);
create index idx_companies_owner on companies(owner_profile_id);

-- ============================================================
-- 3. drivers — profil mitra transporter
-- ============================================================
create table drivers (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null unique references profiles(id),
  ktp_number text not null unique,
  ktp_photo_url text not null,
  sim_number text not null,
  sim_photo_url text not null,
  bank_name text not null,
  bank_account_number text not null,
  status driver_status not null default 'pending_review',
  is_available boolean not null default true,
  rejection_reason text,
  created_at timestamptz not null default now()
);

-- ============================================================
-- 4. vehicles — kendaraan milik driver
-- ============================================================
create table vehicles (
  id uuid primary key default gen_random_uuid(),
  driver_id uuid not null references drivers(id) on delete cascade,
  plate_number text not null unique,
  vehicle_type vehicle_type not null,
  max_weight_kg numeric(10,2) not null check (max_weight_kg > 0),
  stnk_photo_url text not null,
  created_at timestamptz not null default now()
);
create index idx_vehicles_driver on vehicles(driver_id);

-- ============================================================
-- 5. commission_rules — konfigurasi persentase komisi per tipe kendaraan
-- ============================================================
create table commission_rules (
  id uuid primary key default gen_random_uuid(),
  vehicle_type vehicle_type not null unique,
  commission_percent numeric(5,2) not null check (commission_percent >= 0 and commission_percent <= 100),
  base_price numeric(12,2) not null default 0,
  price_per_km numeric(12,2) not null default 0,
  updated_at timestamptz not null default now()
);

-- ============================================================
-- 6. orders — order pengiriman
-- ============================================================
create table orders (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references companies(id),
  created_by_profile_id uuid not null references profiles(id),
  driver_id uuid references drivers(id),
  vehicle_id uuid references vehicles(id),
  status order_status not null default 'pending',
  pickup_address text not null,
  pickup_lat double precision,
  pickup_lng double precision,
  dropoff_address text not null,
  dropoff_lat double precision,
  dropoff_lng double precision,
  cargo_type cargo_type not null,
  weight_kg numeric(10,2) not null check (weight_kg > 0),
  volume_m3 numeric(10,2),
  vehicle_type_requested vehicle_type not null,
  scheduled_pickup_at timestamptz not null,
  notes text,
  pod_required boolean not null default true,
  pod_photo_url text,
  total_price numeric(12,2) not null default 0,
  driver_payout numeric(12,2) not null default 0,
  platform_commission numeric(12,2) not null default 0,
  commission_override_reason text,
  cancelled_reason text,
  delivered_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index idx_orders_company on orders(company_id);
create index idx_orders_driver on orders(driver_id);
create index idx_orders_status on orders(status);

create function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger trg_orders_updated_at
  before update on orders
  for each row execute procedure public.set_updated_at();

-- ============================================================
-- 7. order_tracking_events — histori/timeline status (append-only)
-- ============================================================
create table order_tracking_events (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references orders(id) on delete cascade,
  status order_status not null,
  note text,
  lat double precision,
  lng double precision,
  created_by_profile_id uuid not null references profiles(id),
  created_at timestamptz not null default now()
);
create index idx_tracking_order on order_tracking_events(order_id, created_at);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================
alter table profiles enable row level security;
alter table companies enable row level security;
alter table drivers enable row level security;
alter table vehicles enable row level security;
alter table commission_rules enable row level security;
alter table orders enable row level security;
alter table order_tracking_events enable row level security;

-- Helper: cek apakah user login adalah admin
create function public.is_admin()
returns boolean language sql stable as $$
  select exists (select 1 from profiles p where p.id = auth.uid() and p.role = 'admin');
$$;

-- profiles
create policy "user reads own profile" on profiles
  for select using (id = auth.uid());
create policy "admin reads all profiles" on profiles
  for select using (public.is_admin());
create policy "user updates own profile" on profiles
  for update using (id = auth.uid());

-- companies
create policy "company reads own record" on companies
  for select using (owner_profile_id = auth.uid());
create policy "company inserts own record" on companies
  for insert with check (owner_profile_id = auth.uid());
create policy "admin full access companies" on companies
  for all using (public.is_admin());

-- drivers
create policy "driver reads own record" on drivers
  for select using (profile_id = auth.uid());
create policy "driver inserts own record" on drivers
  for insert with check (profile_id = auth.uid());
create policy "admin full access drivers" on drivers
  for all using (public.is_admin());

-- vehicles
create policy "driver reads own vehicles" on vehicles
  for select using (
    exists (select 1 from drivers d where d.id = vehicles.driver_id and d.profile_id = auth.uid())
  );
create policy "driver inserts own vehicles" on vehicles
  for insert with check (
    exists (select 1 from drivers d where d.id = vehicles.driver_id and d.profile_id = auth.uid())
  );
create policy "admin full access vehicles" on vehicles
  for all using (public.is_admin());

-- commission_rules (read-only untuk semua user login, tulis hanya admin)
create policy "authenticated reads commission rules" on commission_rules
  for select using (auth.role() = 'authenticated');
create policy "admin writes commission rules" on commission_rules
  for all using (public.is_admin());

-- orders
create policy "company reads own orders" on orders
  for select using (
    exists (select 1 from companies c where c.id = orders.company_id and c.owner_profile_id = auth.uid())
  );
create policy "company inserts own orders" on orders
  for insert with check (
    exists (select 1 from companies c where c.id = orders.company_id and c.owner_profile_id = auth.uid())
  );
create policy "driver reads assigned orders" on orders
  for select using (
    exists (select 1 from drivers d where d.id = orders.driver_id and d.profile_id = auth.uid())
  );
create policy "admin full access orders" on orders
  for all using (public.is_admin());

-- order_tracking_events
create policy "company reads tracking of own orders" on order_tracking_events
  for select using (
    exists (
      select 1 from orders o
      join companies c on c.id = o.company_id
      where o.id = order_tracking_events.order_id and c.owner_profile_id = auth.uid()
    )
  );
create policy "driver reads tracking of assigned orders" on order_tracking_events
  for select using (
    exists (
      select 1 from orders o
      join drivers d on d.id = o.driver_id
      where o.id = order_tracking_events.order_id and d.profile_id = auth.uid()
    )
  );
create policy "admin full access tracking" on order_tracking_events
  for all using (public.is_admin());

-- ============================================================
-- REALTIME PUBLICATION
-- ============================================================
alter publication supabase_realtime add table orders;
alter publication supabase_realtime add table order_tracking_events;
