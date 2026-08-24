"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { DataTable } from "@/components/DataTable";
import { LogoutButton } from "@/components/LogoutButton";
import { StatusBadge, STATUS_LABELS } from "@/components/StatusBadge";
import { api, ApiError } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import { ORDER_STATUSES, type OrderListItem, type OrderStatus } from "@/lib/types";
import { useRealtimeRefetch } from "@/lib/useRealtimeRefetch";

function isThisMonth(isoDate: string): boolean {
  const date = new Date(isoDate);
  const now = new Date();
  return date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth();
}

export default function CompanyDashboardPage() {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [orders, setOrders] = useState<OrderListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [exportError, setExportError] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState<OrderStatus | "">("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [search, setSearch] = useState("");

  async function loadOrders() {
    try {
      const result = await api.get<OrderListItem[]>("/orders");
      setOrders(result);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        router.push("/company/onboarding");
        return;
      }
      setError(err instanceof ApiError ? err.message : "Gagal memuat data order.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    async function init() {
      const supabase = createClient();
      const { data } = await supabase.auth.getUser();
      setEmail(data.user?.email ?? null);
      await loadOrders();
    }
    init();
  }, []);

  useRealtimeRefetch("company-orders", ["orders"], loadOrders);

  const stats = useMemo(() => {
    const aktif = orders.filter((o) => o.status !== "delivered" && o.status !== "cancelled").length;
    const menungguAssign = orders.filter((o) => o.status === "pending").length;
    const dalamPerjalanan = orders.filter(
      (o) => o.status === "picked_up" || o.status === "in_transit"
    ).length;
    const selesaiBulanIni = orders.filter(
      (o) => o.status === "delivered" && isThisMonth(o.created_at)
    ).length;
    return { aktif, menungguAssign, dalamPerjalanan, selesaiBulanIni };
  }, [orders]);

  const visibleOrders = useMemo(() => {
    return orders.filter((order) => {
      if (statusFilter && order.status !== statusFilter) return false;
      if (dateFrom && order.created_at < dateFrom) return false;
      if (dateTo && order.created_at > `${dateTo}T23:59:59`) return false;
      if (search) {
        const q = search.toLowerCase();
        if (
          !order.pickup_address.toLowerCase().includes(q) &&
          !order.dropoff_address.toLowerCase().includes(q)
        ) {
          return false;
        }
      }
      return true;
    });
  }, [orders, statusFilter, dateFrom, dateTo, search]);

  async function handleExport() {
    setExportError(null);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.set("status_filter", statusFilter);
      if (dateFrom) params.set("date_from", dateFrom);
      if (dateTo) params.set("date_to", dateTo);

      const { blob, filename } = await api.downloadFile(
        `/reports/orders/export?${params.toString()}`
      );
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setExportError(err instanceof ApiError ? err.message : "Gagal mengekspor data.");
    }
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-6 p-8">
      <div className="flex items-center justify-between border-b border-silver pb-4">
        <div>
          <h1 className="text-xl font-semibold text-iron">Dashboard Perusahaan</h1>
          <p className="text-sm text-olive">{email}</p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/company/orders/new"
            className="rounded-md bg-lime px-4 py-2 text-sm font-semibold text-iron transition hover:brightness-95"
          >
            Buat Order Baru
          </Link>
          <LogoutButton />
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {!isLoading && !error && (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="rounded-lg border border-silver bg-white p-4">
              <p className="text-xs text-olive">Order Aktif</p>
              <p className="text-2xl font-semibold text-iron">{stats.aktif}</p>
            </div>
            <div className="rounded-lg border border-silver bg-white p-4">
              <p className="text-xs text-olive">Menunggu Assign</p>
              <p className="text-2xl font-semibold text-iron">{stats.menungguAssign}</p>
            </div>
            <div className="rounded-lg border border-silver bg-white p-4">
              <p className="text-xs text-olive">Dalam Perjalanan</p>
              <p className="text-2xl font-semibold text-iron">{stats.dalamPerjalanan}</p>
            </div>
            <div className="rounded-lg border border-silver bg-white p-4">
              <p className="text-xs text-olive">Selesai Bulan Ini</p>
              <p className="text-2xl font-semibold text-iron">{stats.selesaiBulanIni}</p>
            </div>
          </div>

          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-iron">Status</label>
              <select
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value as OrderStatus | "")}
                className="rounded-md border border-silver bg-white px-3 py-2 text-sm text-iron focus:border-iron focus:outline-none"
              >
                <option value="">Semua Status</option>
                {ORDER_STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {STATUS_LABELS[status]}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-iron">Dari Tanggal</label>
              <input
                type="date"
                value={dateFrom}
                onChange={(event) => setDateFrom(event.target.value)}
                className="rounded-md border border-silver bg-white px-3 py-2 text-sm text-iron focus:border-iron focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-iron">Sampai Tanggal</label>
              <input
                type="date"
                value={dateTo}
                onChange={(event) => setDateTo(event.target.value)}
                className="rounded-md border border-silver bg-white px-3 py-2 text-sm text-iron focus:border-iron focus:outline-none"
              />
            </div>
            <div className="flex-1">
              <label className="mb-1 block text-xs font-medium text-iron">Cari Alamat</label>
              <input
                type="text"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Alamat jemput atau antar..."
                className="w-full rounded-md border border-silver bg-white px-3 py-2 text-sm text-iron focus:border-iron focus:outline-none"
              />
            </div>
            <button
              type="button"
              onClick={handleExport}
              className="rounded-md border border-olive px-4 py-2 text-sm font-medium text-iron transition hover:bg-iron hover:text-white"
            >
              Export Excel
            </button>
          </div>

          {exportError && <p className="text-sm text-red-600">{exportError}</p>}

          <DataTable
            columns={["Order ID", "Tanggal", "Alamat Jemput", "Alamat Antar", "Jenis Barang", "Status", "Aksi"]}
            rows={visibleOrders.map((order) => [
              order.id.slice(0, 8),
              new Date(order.created_at).toLocaleDateString("id-ID"),
              order.pickup_address,
              order.dropoff_address,
              order.cargo_type,
              <StatusBadge key={order.id} status={order.status} />,
              <Link
                key={order.id}
                href={`/company/orders/${order.id}`}
                className="font-medium text-iron underline"
              >
                Lihat Detail
              </Link>,
            ])}
          />
        </>
      )}
    </main>
  );
}
