# SRS — Software Requirements Specification

## 1. Validasi Form

### 1.1 Form Order Pemesanan (Company)

| Field | Tipe | Aturan Validasi |
|---|---|---|
| `pickup_address` | string | wajib, min 10 karakter, max 255 |
| `pickup_lat`, `pickup_lng` | float | opsional di MVP (bisa null jika input alamat manual saja) |
| `dropoff_address` | string | wajib, min 10 karakter, max 255 |
| `cargo_type` | enum | wajib — salah satu dari: `general`, `fragile`, `frozen`, `hazardous`, `document` |
| `weight_kg` | decimal | wajib, > 0, ≤ 30000 |
| `volume_m3` | decimal | opsional, ≥ 0 |
| `vehicle_type_requested` | enum | wajib — `motor`, `pickup`, `box_small`, `box_medium`, `truck_cdd`, `truck_cdd_long`, `truck_fuso`, `truck_trailer` |
| `scheduled_pickup_at` | datetime | wajib, harus ≥ now + 1 jam |
| `notes` | string | opsional, max 500 karakter |
| `pod_required` | boolean | default `true` |

Validasi dilakukan **dua lapis**: Zod schema di Next.js (client + server action) dan Pydantic model di FastAPI (server-side, sumber kebenaran akhir — jangan pernah percaya validasi client saja).

### 1.2 Onboarding Driver (Mitra Transporter)

| Field | Tipe | Aturan Validasi |
|---|---|---|
| `full_name` | string | wajib, min 3 karakter |
| `phone_number` | string | wajib, format Indonesia `08xxxxxxxxxx` atau `+62xxxxxxxxxx`, unik |
| `ktp_number` | string | wajib, 16 digit numerik, unik |
| `ktp_photo_url` | file→url | wajib, tipe file `image/jpeg|png`, max 5 MB |
| `sim_number` | string | wajib (SIM sesuai kelas kendaraan) |
| `sim_photo_url` | file→url | wajib, max 5 MB |
| `bank_account_number` | string | wajib, numerik |
| `bank_name` | string | wajib |
| Kendaraan: `plate_number` | string | wajib, unik, format plat Indonesia |
| Kendaraan: `vehicle_type` | enum | wajib, sama dengan enum `vehicle_type_requested` di atas |
| Kendaraan: `stnk_photo_url` | file→url | wajib, max 5 MB |
| Kendaraan: `max_weight_kg` | decimal | wajib, > 0 |

Status onboarding driver: `pending_review → approved / rejected` — driver **tidak bisa** menerima assignment sebelum status `approved` oleh Admin.

**Batasan ukuran file (global, berlaku semua upload — KTP, SIM, STNK, foto POD):** max **5 MB per file**, format `image/jpeg`, `image/png`, atau `application/pdf` (khusus dokumen). Validasi dilakukan di FastAPI sebelum upload ke Supabase Storage, dan dibatasi juga di sisi client sebelum upload untuk hemat bandwidth.

## 2. Behavior — Real-time via Supabase

### 2.1 State Machine Status Order

```
pending ──assign──> assigned ──pickup──> picked_up ──depart──> in_transit ──arrive──> delivered
   │                    │
   └──cancel────────────┴──> cancelled
```

Aturan transisi (ditegakkan di backend FastAPI, bukan hanya di frontend):
- `pending → assigned`: hanya oleh role `admin`, mensyaratkan `driver_id` & `vehicle_id` terisi dan driver berstatus `approved` & `available`.
- `assigned → picked_up` dan `picked_up → in_transit` dan `in_transit → delivered`: hanya oleh role `driver` yang merupakan **pemilik assignment** order tersebut (dicek via `order.driver_id == current_user.id`).
- `delivered` mensyaratkan `pod_photo_url` sudah terisi — tidak bisa transisi ke `delivered` tanpa POD jika `pod_required = true`.
- `→ cancelled`: bisa dilakukan oleh `admin` atau `company` (pemilik order) **hanya** selama status masih `pending` atau `assigned` (belum `picked_up`). Setelah barang dijemput, pembatalan harus lewat proses eksepsi manual admin (di luar scope otomatis MVP).
- Transisi mundur (mis. `in_transit → assigned`) **tidak diizinkan**; kesalahan input status ditangani via endpoint koreksi khusus admin dengan log alasan.

### 2.2 Mekanisme Real-time

- Setiap perubahan pada tabel `orders` dan `order_tracking_events` di-broadcast otomatis oleh **Supabase Realtime** (Postgres logical replication → WebSocket).
- Frontend Next.js subscribe ke channel per-role:
  - Company: filter `orders` where `company_id = current_company_id`.
  - Admin: subscribe semua `orders` (atau di-paginate per halaman aktif) + tabel `drivers` untuk status ketersediaan.
  - Driver: filter `orders` where `driver_id = current_driver_id`.
- Setiap kali FastAPI melakukan mutasi status (`PATCH /orders/{id}/status`), FastAPI menulis row baru ke `order_tracking_events` **dan** meng-update kolom `status` di `orders` dalam satu transaksi DB — supaya konsumen Realtime cukup listen ke satu event source (`orders` update) untuk status terkini, dan `order_tracking_events` untuk histori lengkap (timeline).
- Reconnect handling: jika koneksi WebSocket driver terputus (umum di lapangan), Next.js melakukan **refetch REST** saat channel reconnect (`on('SUBSCRIBED')`) untuk menjamin state tidak stale.

## 3. Aturan Aplikasi (Business Rules)

### 3.1 Komisi

- Setiap order memiliki `total_price` (tarif yang dibayar Company) dan `driver_payout` (yang diterima transporter).
- `platform_commission = total_price - driver_payout`.
- MVP: **komisi flat percentage per tipe kendaraan**, disimpan di tabel konfigurasi `commission_rules` (bukan hardcode), contoh default: 15% dari `total_price`. Admin bisa override komisi per-order secara manual jika perlu (dicatat di `orders.commission_override_reason`).
- Perhitungan komisi terjadi **saat order dibuat** (estimasi) dan **dikunci final saat status `delivered`** (final settlement) — mencegah nilai berubah setelah pengiriman selesai.

### 3.2 Batasan Umum

- Maksimal file upload: **5 MB** per file (lihat §1.2).
- Maksimal order aktif per company tanpa approval khusus: tidak dibatasi di MVP (semua order langsung masuk antrian admin).
- Satu driver hanya bisa memiliki **satu order aktif** (`assigned`/`picked_up`/`in_transit`) dalam satu waktu di MVP (disederhanakan — belum mendukung multi-drop dalam satu perjalanan).
- Export Excel dibatasi rentang maksimal **1 tahun** per request (mencegah query berat) dan hasil generate disimpan sementara (signed URL Supabase Storage, kedaluwarsa 24 jam).
- Semua endpoint API wajib melalui autentikasi JWT Supabase; row-level security (RLS) di Postgres menjadi lapis pertahanan kedua di luar validasi FastAPI (defense in depth).
