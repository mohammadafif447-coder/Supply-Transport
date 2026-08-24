# SDD — System Design Document

## 1. Arsitektur

```
┌─────────────────────┐        ┌──────────────────────┐        ┌───────────────────────┐
│   Next.js 14 (App    │  HTTPS │   FastAPI (Python)   │        │      Supabase          │
│   Router, TS)         │──────▶│   Business Logic /    │──────▶│  - Postgres (data)     │
│  - Server Components  │◀──────│   Validation Layer    │◀──────│  - Auth (JWT)          │
│  - Server Actions      │       │  - Pydantic models    │        │  - Storage (files)     │
│  - Client Components   │       │  - openpyxl reports   │        │  - Realtime (WS)       │
│    (subscribe realtime)│       │                       │        │                        │
└───────────┬───────────┘       └──────────┬────────────┘        └───────────┬────────────┘
            │                              │                                  │
            │  1. Auth langsung ke Supabase Auth (login/register, dapat JWT)  │
            └──────────────────────────────────────────────────────────────▶│
            │                                                                 │
            │  2. Semua operasi bisnis (create order, assign, update status,  │
            │     export Excel) lewat FastAPI — FastAPI verifikasi JWT lalu   │
            │     pakai service-role key untuk baca/tulis Postgres.           │
            │                                                                 │
            │  3. Frontend subscribe LANGSUNG ke Supabase Realtime (WS) untuk │
            │     update status order — TIDAK lewat FastAPI (latensi rendah). │
            └────────────────────────────────────────────────────────────────┘
```

**Prinsip pembagian tanggung jawab:**
- **Next.js**: rendering UI, Server Actions untuk mutasi sederhana yang men-*proxy* ke FastAPI, subscribe Supabase Realtime langsung dari client untuk update live, membaca session/JWT dari Supabase Auth (`@supabase/ssr`).
- **FastAPI**: satu-satunya pintu untuk **mutasi data berbisnis-aturan** (create order, assign driver, ubah status, hitung komisi, generate Excel). Tidak ada logic bisnis yang hanya hidup di frontend.
- **Supabase**: identity provider (Auth), database of record (Postgres + RLS sebagai lapis kedua), file storage (dokumen driver, foto POD), dan real-time transport layer.

Autentikasi antara Next.js ↔ FastAPI: Next.js mengirim Supabase JWT (access token) di header `Authorization: Bearer <token>`; FastAPI memverifikasi signature JWT lewat **JWKS** (project ini pakai signing key asimetris ES256 — `GET {SUPABASE_URL}/auth/v1/.well-known/jwks.json`, endpoint publik, tanpa perlu menyimpan secret apa pun untuk verifikasi), lalu mengekstrak `user_id` dari klaim `sub` dan mencocokkan `role` dari tabel `profiles`.

## 2. Database Schema (PostgreSQL / Supabase)

```sql
-- ENUM types
create type user_role as enum ('company', 'admin', 'driver');
create type order_status as enum ('pending','assigned','picked_up','in_transit','delivered','cancelled');
create type driver_status as enum ('pending_review','approved','rejected','suspended');
create type cargo_type as enum ('general','fragile','frozen','hazardous','document');
create type vehicle_type as enum ('motor','pickup','box_small','box_medium','truck_cdd','truck_cdd_long','truck_fuso','truck_trailer');

-- 1. profiles: extends auth.users (Supabase Auth) dengan role & data umum
create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  role user_role not null,
  full_name text not null,
  phone_number text unique,
  avatar_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 2. companies: profil perusahaan klien (shipper)
create table companies (
  id uuid primary key default gen_random_uuid(),
  owner_profile_id uuid not null references profiles(id),
  company_name text not null,
  company_address text not null,
  tax_id text,          -- NPWP
  billing_email text,
  created_at timestamptz not null default now()
);

-- 3. drivers: profil mitra transporter
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

-- 4. vehicles: kendaraan milik driver
create table vehicles (
  id uuid primary key default gen_random_uuid(),
  driver_id uuid not null references drivers(id) on delete cascade,
  plate_number text not null unique,
  vehicle_type vehicle_type not null,
  max_weight_kg numeric(10,2) not null,
  stnk_photo_url text not null,
  created_at timestamptz not null default now()
);

-- 5. commission_rules: konfigurasi persentase komisi per tipe kendaraan
create table commission_rules (
  id uuid primary key default gen_random_uuid(),
  vehicle_type vehicle_type not null unique,
  commission_percent numeric(5,2) not null check (commission_percent >= 0 and commission_percent <= 100),
  updated_at timestamptz not null default now()
);

-- 6. orders: order pengiriman
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
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index idx_orders_company on orders(company_id);
create index idx_orders_driver on orders(driver_id);
create index idx_orders_status on orders(status);

-- 7. order_tracking_events: histori/timeline perubahan status (append-only)
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
```

**Row-Level Security (RLS)** — diaktifkan di semua tabel; contoh untuk `orders`:
```sql
alter table orders enable row level security;

create policy "company reads own orders" on orders
  for select using (
    exists (select 1 from companies c where c.id = orders.company_id and c.owner_profile_id = auth.uid())
  );

create policy "driver reads assigned orders" on orders
  for select using (
    exists (select 1 from drivers d where d.id = orders.driver_id and d.profile_id = auth.uid())
  );

create policy "admin full access" on orders
  for all using (
    exists (select 1 from profiles p where p.id = auth.uid() and p.role = 'admin')
  );
```
FastAPI menggunakan **service role key** (bypass RLS) untuk operasi backend yang sudah divalidasi di application layer; RLS tetap aktif sebagai lapis pertahanan kedua untuk mencegah akses langsung tak sah lewat Supabase client di frontend (mis. saat subscribe Realtime).

## 3. API Endpoints (FastAPI)

Base path: `/api/v1`. Semua endpoint (kecuali `/auth/*` yang di-handle Supabase langsung dari frontend) mensyaratkan header `Authorization: Bearer <supabase_jwt>`.

| Method | Path | Role | Deskripsi |
|---|---|---|---|
| POST | `/companies` | company | Buat/lengkapi profil perusahaan (onboarding) |
| GET | `/companies/me` | company | Ambil profil perusahaan sendiri |
| POST | `/drivers` | driver | Submit onboarding driver + kendaraan pertama |
| GET | `/drivers/me` | driver | Ambil profil driver sendiri |
| GET | `/drivers` | admin | List semua driver (filter `status`, `is_available`, `vehicle_type`) |
| PATCH | `/drivers/{driver_id}/review` | admin | Approve/reject driver (`status`, `rejection_reason`) |
| POST | `/drivers/{driver_id}/vehicles` | driver | Tambah kendaraan baru |
| GET | `/vehicles/available` | admin | List kendaraan tersedia untuk assignment (filter `vehicle_type`) |
| POST | `/orders` | company | Buat order baru (status awal `pending`, hitung estimasi harga & komisi) |
| GET | `/orders` | company/admin | List order (company: hanya miliknya; admin: semua, dgn filter `status`,`date_range`,`driver_id`) |
| GET | `/orders/{order_id}` | company/admin/driver | Detail order (RLS membatasi kepemilikan) |
| GET | `/orders/driver/me` | driver | List order yang di-assign ke driver login |
| PATCH | `/orders/{order_id}/assign` | admin | Assign `driver_id` + `vehicle_id` → status `assigned` |
| PATCH | `/orders/{order_id}/status` | driver | Update status (`picked_up`/`in_transit`/`delivered`) sesuai state machine §SRS 2.1 |
| POST | `/orders/{order_id}/pod` | driver | Upload foto POD (multipart) → simpan `pod_photo_url` |
| PATCH | `/orders/{order_id}/cancel` | company/admin | Batalkan order (hanya jika status `pending`/`assigned`) |
| GET | `/orders/{order_id}/tracking` | company/admin/driver | Timeline lengkap `order_tracking_events` |
| GET | `/reports/orders/export` | admin/company | Generate & download rekap Excel (query params: `date_from`, `date_to`, `status`, `company_id`) |
| GET | `/commission-rules` | admin | List aturan komisi |
| PUT | `/commission-rules/{vehicle_type}` | admin | Update persentase komisi per tipe kendaraan |

## 4. Backend Logic — Export/Import Excel dengan `openpyxl`

Alur `GET /reports/orders/export`:

1. FastAPI menerima query params (`date_from`, `date_to`, `status`, `company_id` opsional) dan **role user** (dari JWT) untuk membatasi scope data (company hanya bisa export order miliknya sendiri; admin bebas).
2. Query Postgres via Supabase client (service role) → dapatkan list order + join `companies.company_name`, `drivers.full_name`(lewat `profiles`), `vehicles.plate_number`.
3. Bangun workbook dengan `openpyxl`:

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from io import BytesIO

def build_orders_report(orders: list[dict]) -> BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "Rekap Order"

    headers = [
        "Order ID", "Tanggal Order", "Perusahaan", "Alamat Jemput", "Alamat Antar",
        "Jenis Barang", "Berat (kg)", "Tipe Kendaraan", "Driver", "Plat Nomor",
        "Status", "Total Harga", "Payout Driver", "Komisi Platform", "Tgl Selesai",
    ]
    ws.append(headers)
    header_fill = PatternFill(start_color="435058", end_color="435058", fill_type="solid")
    for col_idx, _ in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill

    for o in orders:
        ws.append([
            o["id"], o["created_at"], o["company_name"], o["pickup_address"], o["dropoff_address"],
            o["cargo_type"], float(o["weight_kg"]), o["vehicle_type_requested"], o.get("driver_name", "-"),
            o.get("plate_number", "-"), o["status"], float(o["total_price"]), float(o["driver_payout"]),
            float(o["platform_commission"]), o.get("delivered_at", "-"),
        ])

    for col_idx in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = 18

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
```

4. Endpoint mengembalikan file via `StreamingResponse` dengan `media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"` dan header `Content-Disposition: attachment; filename=rekap-order-{date_from}_{date_to}.xlsx` — **tidak** disimpan permanen di server (dibangun on-the-fly per request; jika perlu link yang bisa dibagikan, baru diunggah ke Supabase Storage dengan signed URL 24 jam sesuai SRS §3.2).
5. **Import** (opsional MVP-lanjutan, bukan blocker MVP inti): endpoint `POST /reports/orders/import` menerima file `.xlsx` (bulk create order dari template), dibaca dengan `openpyxl.load_workbook(..., data_only=True)`, setiap baris divalidasi lewat Pydantic model yang sama dengan `POST /orders` sebelum insert — baris gagal dikumpulkan dan dikembalikan sebagai laporan error (bukan gagal seluruh batch).

## 5. Struktur Direktori (Monorepo)

```
Supply Transport/
├── frontend/                # Next.js 14 App Router
│   ├── app/
│   │   ├── (auth)/login/ register/
│   │   ├── (company)/dashboard/ orders/
│   │   ├── (admin)/dashboard/ drivers/ orders/
│   │   ├── (driver)/dashboard/ orders/
│   │   └── layout.tsx
│   ├── lib/supabase/ (client.ts, server.ts)
│   ├── components/ (Table, StatusBadge, OrderForm, ...)
│   └── Dockerfile
├── backend/                 # FastAPI
│   ├── app/
│   │   ├── main.py
│   │   ├── api/v1/ (orders.py, drivers.py, companies.py, reports.py)
│   │   ├── models/ (pydantic schemas)
│   │   ├── services/ (order_service.py, excel_service.py, commission_service.py)
│   │   ├── core/ (config.py, security.py — verifikasi JWT Supabase)
│   │   └── db/ (supabase_client.py)
│   ├── requirements.txt
│   └── Dockerfile
├── docs/                    # PRD, SRS, SDD, UI/UX, Task Breakdown (dokumen ini)
├── supabase/                # migrations SQL (schema di atas)
└── docker-compose.yml
```
