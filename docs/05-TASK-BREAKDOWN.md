# Task Breakdown — Langkah Eksekusi Step-by-Step

> Kerjakan berurutan. Setiap fase punya "Definition of Done" — jangan lanjut ke fase berikutnya sebelum DoD tercapai, supaya error tidak menumpuk.

## Fase 0 — Setup Fondasi

0.1. Buat akun & project baru di [supabase.com](https://supabase.com) → catat `Project URL`, `anon key`, `service_role key`.
0.2. Di root `D:\Supply Transport`, jalankan `npx supabase init` untuk folder `supabase/` (migrations lokal).
0.3. Tulis file migration SQL berdasarkan skema di `docs/03-SDD.md` §2 ke `supabase/migrations/0001_init.sql`.
0.4. Jalankan migration ke project Supabase (`npx supabase db push` atau paste manual ke SQL Editor Supabase Dashboard).
0.5. Aktifkan RLS policy sesuai `docs/03-SDD.md` §2 untuk tabel `orders`, `drivers`, `companies`, `vehicles`, `order_tracking_events`.
0.6. Buat bucket Storage di Supabase: `driver-documents` (privat) dan `pod-photos` (privat), masing-masing dengan policy akses sesuai role.

**DoD Fase 0**: Bisa login ke Supabase Dashboard, lihat semua tabel di Table Editor sesuai skema, RLS aktif (bukan disabled), 2 bucket storage tersedia.

## Fase 1 — Inisialisasi Backend (FastAPI)

1.1. `mkdir backend && cd backend`, buat virtualenv, `pip install fastapi uvicorn[standard] pydantic-settings supabase openpyxl python-multipart python-jose[cryptography]`.
1.2. Freeze dependency: `pip freeze > requirements.txt`.
1.3. Buat `app/core/config.py` (baca `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` dari environment variable — **jangan hardcode**).
1.4. Buat `app/core/security.py`: fungsi `get_current_user()` sebagai FastAPI dependency yang memverifikasi JWT Supabase dari header `Authorization` lewat JWKS project (`{SUPABASE_URL}/auth/v1/.well-known/jwks.json`) — tidak ada JWT secret statis yang perlu disimpan.
1.5. Buat `app/main.py` dengan health-check endpoint `GET /health`.
1.6. Jalankan `uvicorn app.main:app --reload` → test `GET /health` return 200.

**DoD Fase 1**: Server FastAPI lokal jalan, endpoint health check bisa diakses, struktur folder sesuai `docs/03-SDD.md` §5.

## Fase 2 — API Inti: Companies, Drivers, Vehicles

2.1. Buat Pydantic schema untuk `Company`, `Driver`, `Vehicle` sesuai validasi di `docs/02-SRS.md` §1.
2.2. Implementasi endpoint `POST /companies`, `GET /companies/me`.
2.3. Implementasi endpoint `POST /drivers` (termasuk handle upload file KTP/SIM ke Supabase Storage sebelum insert record — cek batas 5MB di `docs/02-SRS.md` §1.2).
2.4. Implementasi endpoint `GET /drivers`, `PATCH /drivers/{id}/review` (khusus role admin).
2.5. Implementasi endpoint `POST /drivers/{id}/vehicles`, `GET /vehicles/available`.
2.6. Test semua endpoint di atas pakai Postman/Thunder Client dengan token JWT dummy dari Supabase Auth (buat 3 user test: 1 company, 1 admin, 1 driver, set `role` di tabel `profiles` manual dulu).

**DoD Fase 2**: Semua endpoint di atas berhasil di-test manual, termasuk kasus gagal validasi (400) dan gagal auth (401/403).

## Fase 3 — API Inti: Orders & Status Transition

3.1. Buat Pydantic schema `OrderCreate`, `OrderStatusUpdate` sesuai `docs/02-SRS.md` §1.1 & §2.1.
3.2. Implementasi `POST /orders` — termasuk hitung `total_price` (tarif dasar sederhana per `vehicle_type` + jarak dummy/manual di MVP) dan `platform_commission` dari tabel `commission_rules`.
3.3. Implementasi `GET /orders`, `GET /orders/{id}` dengan scoping akses per role.
3.4. Implementasi `PATCH /orders/{id}/assign` — validasi driver `approved` & `is_available`.
3.5. Implementasi `PATCH /orders/{id}/status` — **tegakkan state machine** persis sesuai `docs/02-SRS.md` §2.1 (tolak transisi ilegal dengan 400 + pesan jelas).
3.6. Implementasi `POST /orders/{id}/pod` (upload foto ke bucket `pod-photos`).
3.7. Implementasi `PATCH /orders/{id}/cancel`.
3.8. Implementasi `GET /orders/{id}/tracking` (baca `order_tracking_events`).
3.9. Setiap perubahan status, pastikan insert row ke `order_tracking_events` dalam transaksi yang sama dengan update `orders.status`.

**DoD Fase 3**: End-to-end lifecycle order (`pending → assigned → picked_up → in_transit → delivered`) bisa dijalankan penuh lewat Postman, transisi ilegal ditolak, `order_tracking_events` terisi tiap langkah.

## Fase 4 — Setup Frontend (Next.js)

4.1. `npx create-next-app@latest frontend --typescript --tailwind --app --src-dir=false`.
4.2. Install `@supabase/ssr @supabase/supabase-js`.
4.3. Setup `lib/supabase/client.ts` (browser client) dan `lib/supabase/server.ts` (server client, untuk Server Components/Actions), pakai env var `NEXT_PUBLIC_SUPABASE_URL` & `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
4.4. Terapkan palet warna di `tailwind.config.ts` sesuai `docs/04-UIUX.md` §0.
4.5. Buat halaman `/login`, `/register` dengan Supabase Auth (`signInWithPassword`, `signUp`).
4.6. Buat middleware Next.js untuk proteksi route berbasis role (baca `role` dari tabel `profiles` setelah login, redirect sesuai `docs/04-UIUX.md` §4).

**DoD Fase 4**: Bisa register & login 3 jenis akun berbeda, masing-masing di-redirect ke dashboard yang sesuai role, route diproteksi (akses silang antar-role ditolak).

## Fase 5 — Komponen Bersama (Table, Badge, Form)

5.1. Buat `components/DataTable.tsx` sesuai `docs/04-UIUX.md` §2 (HTML table murni).
5.2. Buat `components/StatusBadge.tsx` sesuai mapping warna `docs/04-UIUX.md` §1.
5.3. Buat `components/OrderForm.tsx` (form buat order) dengan validasi Zod yang **mirror** Pydantic schema Fase 3.1 — pastikan field & aturan identik agar tidak ada gap validasi client vs server.
5.4. Buat helper `lib/api.ts` (wrapper fetch ke FastAPI, otomatis sisipkan `Authorization: Bearer <token>` dari session Supabase).

**DoD Fase 5**: Komponen bisa dipakai ulang di minimal 2 halaman berbeda tanpa modifikasi, form submit berhasil membuat order lewat FastAPI.

## Fase 6 — Dashboard Company

6.1. Halaman `/company/dashboard`: stat card + `DataTable` order milik company (fetch `GET /orders`).
6.2. Halaman `/company/orders/new`: pakai `OrderForm`.
6.3. Halaman `/company/orders/[id]`: detail order + timeline status (fetch `GET /orders/{id}/tracking`).
6.4. Tombol export Excel (panggil `GET /reports/orders/export`, trigger browser download).

**DoD Fase 6**: Company bisa membuat order baru dan melihatnya muncul di dashboard tanpa refresh manual (lanjut ke Fase 8 untuk real-time).

## Fase 7 — Dashboard Admin

7.1. Halaman `/admin/dashboard` (tab Order Masuk vs Semua Order).
7.2. Modal "Assign Driver" (pilih dari `GET /vehicles/available`).
7.3. Halaman `/admin/drivers` (list + tombol approve/reject).
7.4. Halaman `/admin/commission-rules` (inline edit persentase).

**DoD Fase 7**: Admin bisa menyelesaikan satu siklus penuh: lihat order baru → assign driver → order pindah status → approve driver baru dari halaman terpisah.

## Fase 8 — Layar Driver & Realtime

8.1. Halaman `/driver/dashboard` (kartu tugas aktif sesuai `docs/04-UIUX.md` §3.3).
8.2. Implementasi tombol aksi status berurutan → panggil `PATCH /orders/{id}/status`.
8.3. Form upload POD → panggil `POST /orders/{id}/pod`.
8.4. **Integrasi Supabase Realtime**: subscribe channel `postgres_changes` pada tabel `orders` (filter sesuai role) di ketiga dashboard (company/admin/driver) — update UI otomatis tanpa reload sesuai `docs/02-SRS.md` §2.2.
8.5. Handle reconnect: refetch REST saat channel `SUBSCRIBED` kembali setelah putus koneksi.

**DoD Fase 8**: Buka 2 browser berbeda (company & driver) side-by-side — driver update status, company melihat perubahan tabel real-time tanpa refresh.

## Fase 9 — Testing & Hardening

9.1. Tulis test backend (pytest) untuk state machine transisi status (kasus valid & invalid).
9.2. Tulis test validasi Pydantic (kasus field invalid).
9.3. Review semua RLS policy: coba akses silang antar-role langsung via Supabase client (harus ditolak).
9.4. Cek seluruh upload file: tolak file > 5MB dan tipe tidak sesuai.
9.5. Review error handling: semua endpoint mengembalikan pesan error konsisten (format JSON error terstandar), tidak expose stack trace ke client.

**DoD Fase 9**: Test suite backend hijau, tidak ada akses silang role yang berhasil, upload file besar/tipe salah ditolak dengan pesan jelas.

## Fase 10 — Dockerize & Deploy Lokal

10.1. Tulis `frontend/Dockerfile`, `backend/Dockerfile`, `docker-compose.yml` (sudah disiapkan — lihat root proyek).
10.2. Buat file `.env.example` di `frontend/` dan `backend/` (daftar semua env var wajib, tanpa nilai asli).
10.3. Jalankan `docker compose up --build` di root, verifikasi frontend (port 3000) bisa memanggil backend (port 8000) dan keduanya terhubung ke Supabase cloud.
10.4. Lakukan full smoke test alur order end-to-end di environment Docker (bukan lagi `npm run dev` / `uvicorn --reload`).

**DoD Fase 10**: `docker compose up` dari kondisi bersih (`docker compose down -v` lalu up lagi) menghasilkan aplikasi yang berjalan penuh, siap untuk langkah deployment ke server/VPS/cloud provider pilihan pada iterasi berikutnya.
