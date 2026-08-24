# UI/UX Flow

## 0. Prinsip Desain & Palet Warna

| Token | Hex | Penggunaan |
|---|---|---|
| `--color-bg` (White Smoke) | `#F1F2EE` | Background utama aplikasi (body, halaman) |
| `--color-surface-muted` (Silver) | `#BFB7B6` | Background sekunder (card muted, state disabled, table stripe) |
| `--color-border` (Grey Olive) | `#848C8E` | Border, teks sekunder, placeholder |
| `--color-text` (Iron Grey) | `#435058` | Teks utama, header, elemen solid (navbar, table head) |
| `--color-accent` (Lime Cream) | `#DCF763` | Tombol utama (CTA), highlight, badge status positif, active state |

Konfigurasi Tailwind (`tailwind.config.ts`):
```ts
theme: {
  extend: {
    colors: {
      olive: "#848C8E",
      iron: "#435058",
      lime: "#DCF763",
      silver: "#BFB7B6",
      smoke: "#F1F2EE",
    },
  },
},
```

Aturan pemakaian:
- Tombol primer: `bg-lime text-iron font-semibold hover:brightness-95` (teks gelap di atas lime agar kontras cukup — **jangan** teks putih di atas lime).
- Tombol sekunder/outline: `border border-olive text-iron bg-transparent`.
- Card/panel: `bg-white border border-silver rounded-lg` di atas `bg-smoke` pada level body.
- Header tabel: `bg-iron text-white`.
- State disabled: `bg-silver text-olive cursor-not-allowed`.

## 1. Status Badge Mapping

| Status | Warna Badge | Kelas Tailwind |
|---|---|---|
| `pending` | Silver | `bg-silver text-iron` |
| `assigned` | Olive | `bg-olive/20 text-iron border border-olive` |
| `picked_up` | Lime muda | `bg-lime/40 text-iron` |
| `in_transit` | Lime | `bg-lime text-iron font-semibold` |
| `delivered` | Iron solid | `bg-iron text-white` |
| `cancelled` | Merah muted (satu-satunya luar palet, untuk sinyal bahaya) | `bg-red-100 text-red-700` |

## 2. Komponen Tabel Data (Wajib HTML Murni, Bukan Library Grid)

Contoh komponen React reusable — semantik `<table>` asli, styling Tailwind, tanpa dependency grid pihak ketiga:

```tsx
// components/DataTable.tsx
export function DataTable({ columns, rows }: { columns: string[]; rows: React.ReactNode[][] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-silver bg-white">
      <table className="min-w-full text-sm">
        <thead className="bg-iron text-white">
          <tr>
            {columns.map((col) => (
              <th key={col} className="px-4 py-3 text-left font-medium">{col}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-silver">
          {rows.map((row, i) => (
            <tr key={i} className="odd:bg-white even:bg-smoke hover:bg-lime/10">
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-3 text-iron">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

## 3. Layar Utama

### 3.1 Dashboard Company (Perusahaan)
- **Header**: logo + nama perusahaan, tombol CTA `bg-lime` "Buat Order Baru" di kanan atas.
- **Ringkasan** (4 stat card `bg-white border-silver`): Order Aktif, Menunggu Assign, Dalam Perjalanan, Selesai Bulan Ini.
- **Tabel Order** (`DataTable`): kolom — Order ID, Tanggal, Alamat Jemput → Antar, Jenis Barang, Status (badge), Driver, Aksi (Lihat Detail).
- Filter di atas tabel: dropdown status, date range picker, search alamat — semua elemen native (`<select>`, `<input type="date">`) dengan styling Tailwind, bukan library.
- Klik baris → modal/side-panel detail order: info lengkap + timeline status (vertical stepper sederhana pakai badge) + foto POD (jika `delivered`).
- Tombol "Export Excel" (`border-olive`) di atas tabel → download rekap sesuai filter aktif.

### 3.2 Dashboard Admin (Ops)
- **Sidebar** (`bg-iron text-white`): menu Orders, Drivers & Vehicles, Companies, Commission Rules, Reports.
- **Tab "Order Masuk" (status `pending`)**: tabel dengan tombol aksi per baris "Assign Driver" → membuka modal pilih driver (list driver `approved` & `is_available=true`, filter by `vehicle_type_requested`) + pilih kendaraan → submit.
- **Tab "Semua Order"**: tabel semua order lintas company & status, filter lengkap (company, driver, status, tanggal).
- **Halaman Drivers**: tabel mitra driver dengan status onboarding (`pending_review` disorot pakai badge Silver + tombol "Review" untuk approve/reject dengan alasan).
- **Halaman Commission Rules**: tabel sederhana per `vehicle_type` dengan input persentase komisi (inline edit, tombol simpan `bg-lime`).

### 3.3 Layar Driver (Mobile-first Web)
- Didesain mobile-first karena mayoritas akses dari HP di lapangan.
- **Beranda**: kartu besar "Tugas Aktif Saat Ini" (jika ada order `assigned/picked_up/in_transit`) dengan tombol besar full-width sesuai status berikutnya:
  - Status `assigned` → tombol `bg-lime` "Konfirmasi Jemput Barang" → status jadi `picked_up`.
  - Status `picked_up` → tombol "Mulai Perjalanan" → status jadi `in_transit`.
  - Status `in_transit` → tombol "Sampai Tujuan & Upload Bukti" → buka form upload foto POD → submit → status `delivered`.
- Jika tidak ada tugas aktif: tampilkan pesan netral + toggle "Status Ketersediaan" (available/unavailable) — `bg-lime` saat available, `bg-silver` saat tidak.
- **Riwayat**: `DataTable` sederhana kolom Tanggal, Rute, Status, Payout — untuk transparansi pendapatan driver.

## 4. Alur Navigasi Ringkas

```
/login  →  (redirect by role)
   ├─ company  → /company/dashboard → /company/orders/new → /company/orders/[id]
   ├─ admin    → /admin/dashboard   → /admin/orders → /admin/drivers → /admin/commission-rules
   └─ driver   → /driver/dashboard  → /driver/orders/[id] (aksi update status & POD)
```
