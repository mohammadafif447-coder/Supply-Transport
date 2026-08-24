"use client";

import { useEffect, useMemo, useState } from "react";
import { AdminNav } from "@/components/AdminNav";
import { AssignDriverModal } from "@/components/AssignDriverModal";
import { DataTable } from "@/components/DataTable";
import { LogoutButton } from "@/components/LogoutButton";
import { StatusBadge } from "@/components/StatusBadge";
import { api, ApiError } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import type { OrderListItem } from "@/lib/types";
import { useRealtimeRefetch } from "@/lib/useRealtimeRefetch";

type Tab = "masuk" | "semua";

export default function AdminDashboardPage() {
  const [email, setEmail] = useState<string | null>(null);
  const [orders, setOrders] = useState<OrderListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("masuk");
  const [assigningOrder, setAssigningOrder] = useState<OrderListItem | null>(null);

  async function loadOrders() {
    try {
      const result = await api.get<OrderListItem[]>("/orders");
      setOrders(result);
    } catch (err) {
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

  useRealtimeRefetch("admin-orders", ["orders"], loadOrders);

  const visibleOrders = useMemo(
    () => (tab === "masuk" ? orders.filter((o) => o.status === "pending") : orders),
    [orders, tab]
  );

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-6 p-8">
      <div className="flex items-center justify-between border-b border-silver pb-4">
        <div>
          <h1 className="text-xl font-semibold text-iron">Dashboard Admin</h1>
          <p className="text-sm text-olive">{email}</p>
        </div>
        <LogoutButton />
      </div>

      <AdminNav />

      {error && <p className="text-sm text-red-600">{error}</p>}

      {!isLoading && !error && (
        <>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setTab("masuk")}
              className={`rounded-md px-4 py-2 text-sm font-medium ${
                tab === "masuk" ? "bg-lime text-iron" : "border border-olive text-iron"
              }`}
            >
              Order Masuk
            </button>
            <button
              type="button"
              onClick={() => setTab("semua")}
              className={`rounded-md px-4 py-2 text-sm font-medium ${
                tab === "semua" ? "bg-lime text-iron" : "border border-olive text-iron"
              }`}
            >
              Semua Order
            </button>
          </div>

          <DataTable
            columns={[
              "Order ID",
              "Tanggal",
              "Alamat Jemput",
              "Alamat Antar",
              "Jenis Barang",
              "Status",
              "Aksi",
            ]}
            rows={visibleOrders.map((order) => [
              order.id.slice(0, 8),
              new Date(order.created_at).toLocaleDateString("id-ID"),
              order.pickup_address,
              order.dropoff_address,
              order.cargo_type,
              <StatusBadge key={order.id} status={order.status} />,
              order.status === "pending" ? (
                <button
                  key={order.id}
                  type="button"
                  onClick={() => setAssigningOrder(order)}
                  className="rounded-md border border-olive px-3 py-1 text-sm font-medium text-iron transition hover:bg-iron hover:text-white"
                >
                  Assign Driver
                </button>
              ) : (
                <span key={order.id} className="text-sm text-olive">
                  -
                </span>
              ),
            ])}
          />
        </>
      )}

      {assigningOrder && (
        <AssignDriverModal
          order={assigningOrder}
          onClose={() => setAssigningOrder(null)}
          onAssigned={async () => {
            setAssigningOrder(null);
            await loadOrders();
          }}
        />
      )}
    </main>
  );
}
