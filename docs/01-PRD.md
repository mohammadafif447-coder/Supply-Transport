# PRD — Platform Logistik B2B Asset-Light (MVP)

## 1. Tujuan Produk

Membangun web platform yang menghubungkan **Perusahaan (Shipper)** yang butuh jasa angkut barang dengan **Mitra Transporter** (driver/pemilik truk pihak ketiga), di mana perusahaan kita bertindak sebagai **broker/orchestrator**: menerima order, mencocokkan/menugaskan transporter, melacak status pengiriman secara real-time, dan mengelola pembayaran & komisi — **tanpa memiliki armada sendiri**.

Visi MVP (iterasi pertama): membuktikan alur inti "**Order → Assign → Track → Selesai**" berjalan end-to-end, cukup stabil untuk dipakai beberapa perusahaan klien pilot dengan admin internal yang menugaskan driver secara manual (belum ada auto-matching/algoritma).

## 2. User Personas

### a. Klien Perusahaan (Shipper / Company Admin)
- Staff logistik/purchasing di perusahaan klien (mis. pabrik, distributor, retail).
- Butuh: membuat permintaan pengiriman antar-kota/dalam-kota, tahu status barang real-time, punya riwayat & bukti pengiriman (POD) untuk rekonsiliasi internal, bisa export laporan bulanan.
- Teknis: awam, akses via browser desktop, kadang mobile.

### b. Admin Internal (Ops/Broker)
- Tim internal kita yang menjalankan operasional harian.
- Butuh: melihat semua order masuk, menugaskan/mengganti transporter, memantau seluruh pengiriman aktif dalam satu dashboard, mengelola data mitra driver & kendaraan, generate laporan Excel, menangani eksepsi (pembatalan, keterlambatan).
- Teknis: power user, banyak bekerja dengan tabel data & filter.

### c. Mitra Driver / Transporter
- Driver lepas atau pemilik 1-beberapa truk yang menjadi mitra.
- Butuh: melihat tugas (order) yang di-assign ke dirinya, update status pengiriman (dijemput → dalam perjalanan → terkirim), upload bukti serah terima (foto/POD), lihat riwayat & estimasi pendapatan.
- Teknis: awam, dominan akses via HP (mobile browser), koneksi internet kadang tidak stabil.

## 3. Fitur Utama (MVP Scope)

| Modul | Fitur | Persona |
|---|---|---|
| Auth | Register/Login (email+password via Supabase Auth), role-based access (company, admin, driver) | Semua |
| Onboarding | Form profil perusahaan (klien), form onboarding driver (data diri, kendaraan, dokumen) | Company, Driver |
| Order Management | Buat order pengiriman (alamat jemput/antar, jenis barang, berat/dimensi, jadwal), lihat daftar order, detail order | Company |
| Assignment | Admin melihat order baru (status `pending`), pilih & assign driver/kendaraan tersedia | Admin |
| Tracking | Update status pengiriman oleh driver, notifikasi status berubah real-time ke company & admin | Driver, Company, Admin |
| Proof of Delivery | Upload foto bukti serah terima saat status `delivered` | Driver |
| Dashboard | Dashboard company (order milik sendiri), dashboard admin (semua order, semua mitra), tabel data dengan filter status/tanggal | Semua |
| Reporting | Export rekap order ke Excel (periode tertentu), berdasarkan filter | Admin, Company |
| Driver & Vehicle Management | CRUD data mitra driver & kendaraan (admin approve driver baru) | Admin |
| Notifikasi dasar | Perubahan status order ter-refresh otomatis di UI (Supabase Realtime), tanpa perlu reload | Semua |

**Eksplisit di luar scope MVP** (iterasi berikutnya): pembayaran online/payment gateway, auto-matching driver by algoritma/geolokasi live map, rating & review, chat in-app, multi-currency, mobile native app.

## 4. User Flow Utama (Order Lifecycle)

```
[Company] Login → Buat Order Baru
   → isi detail (asal, tujuan, jenis barang, jadwal jemput)
   → submit → status order = "pending"
        │
        ▼
[Admin] Lihat order "pending" di dashboard
   → pilih driver & kendaraan yang available
   → assign → status order = "assigned"
        │
        ▼
[Driver] Terima notifikasi tugas baru di dashboard-nya
   → menuju lokasi jemput → update status = "picked_up"
   → dalam perjalanan → update status = "in_transit"
   → sampai tujuan → upload foto POD → update status = "delivered"
        │
        ▼
[Company & Admin] Melihat status berubah real-time di tabel order (tanpa reload)
   → Company bisa lihat POD di detail order
        │
        ▼
[Admin] Order selesai → masuk rekap
   → (opsional) Admin/Company export laporan Excel periode tertentu
```

Status order (state machine): `pending → assigned → picked_up → in_transit → delivered` dengan cabang `cancelled` yang bisa terjadi dari `pending` atau `assigned` (lihat SRS §2 untuk aturan transisi).
