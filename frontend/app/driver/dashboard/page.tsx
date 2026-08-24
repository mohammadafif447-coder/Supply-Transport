"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { DataTable } from "@/components/DataTable";
import { DriverActiveTaskCard } from "@/components/DriverActiveTaskCard";
import { LogoutButton } from "@/components/LogoutButton";
import { StatusBadge } from "@/components/StatusBadge";
import { api, ApiError } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import { DRIVER_STATUS_LABELS, type DriverOrderListItem, type DriverProfile, type OrderStatus } from "@/lib/types";
import { useRealtimeRefetch } from "@/lib/useRealtimeRefetch";

const ACTIVE_STATUSES: OrderStatus[] = ["assigned", "picked_up", "in_transit"];

export default function DriverDashboardPage() {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [driver, setDriver] = useState<DriverProfile | null>(null);
  const [orders, setOrders] = useState<DriverOrderListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isTogglingAvailability, setIsTogglingAvailability] = useState(false);

  async function loadAll() {
    try {
      const [driverResult, ordersResult] = await Promise.all([
        api.get<DriverProfile>("/drivers/me"),
        api.get<DriverOrderListItem[]>("/orders/driver/me"),
      ]);
      setDriver(driverResult);
      setOrders(ordersResult);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        router.push("/driver/onboarding");
        return;
      }
      setError(err instanceof ApiError ? err.message : "Gagal memuat data driver.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    async function init() {
      const supabase = createClient();
      const { data } = await supabase.auth.getUser();
      setEmail(data.user?.email ?? null);
      await loadAll();
    }
    init();
  }, []);

  useRealtimeRefetch("driver-orders", ["orders"], loadAll);

  async function handleToggleAvailability() {
    if (!driver) return;
    setIsTogglingAvailability(true);
    setError(null);
    try {
      const updated = await api.patch<DriverProfile>("/drivers/me/availability", {
        is_available: !driver.is_available,
      });
      setDriver(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal mengubah status ketersediaan.");
    } finally {
      setIsTogglingAvailability(false);
    }
  }

  const activeOrder = orders.find((o) => ACTIVE_STATUSES.includes(o.status));

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-xl flex-col gap-6 p-6">
      <div className="flex items-center justify-between border-b border-silver pb-4">
        <div>
          <h1 className="text-xl font-semibold text-iron">Dashboard Driver</h1>
          <p className="text-sm text-olive">{email}</p>
        </div>
        <LogoutButton />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {!isLoading && !error && driver && driver.status !== "approved" && (
        <div className="rounded-lg border border-silver bg-white p-6 text-center">
          <p className="mb-1 text-sm font-semibold text-iron">
            Status Akun: {DRIVER_STATUS_LABELS[driver.status]}
          </p>
          {driver.status === "pending_review" && (
            <p className="text-sm text-olive">
              Profil Anda sedang direview oleh admin. Anda belum bisa menerima order.
            </p>
          )}
          {driver.status === "rejected" && (
            <p className="text-sm text-red-600">
              {driver.rejection_reason ?? "Profil Anda ditolak. Hubungi admin untuk info lebih lanjut."}
            </p>
          )}
          {driver.status === "suspended" && (
            <p className="text-sm text-red-600">Akun Anda ditangguhkan. Hubungi admin.</p>
          )}
        </div>
      )}

      {!isLoading && !error && driver?.status === "approved" && (
        <>
          {activeOrder ? (
            <DriverActiveTaskCard order={activeOrder} onUpdated={loadAll} />
          ) : (
            <div className="rounded-lg border border-silver bg-white p-6 text-center">
              <p className="mb-4 text-sm text-olive">
                Tidak ada tugas aktif saat ini. Ubah status ketersediaan Anda di bawah.
              </p>
              <button
                type="button"
                disabled={isTogglingAvailability}
                onClick={handleToggleAvailability}
                className={`w-full rounded-md px-4 py-3 font-semibold transition disabled:cursor-not-allowed ${
                  driver?.is_available
                    ? "bg-lime text-iron hover:brightness-95"
                    : "bg-silver text-olive hover:brightness-95"
                }`}
              >
                {driver?.is_available ? "Tersedia" : "Tidak Tersedia"}
              </button>
            </div>
          )}

          <div>
            <h2 className="mb-3 text-sm font-semibold text-iron">Riwayat</h2>
            <DataTable
              columns={["Tanggal", "Rute", "Status", "Payout"]}
              rows={orders.map((order) => [
                new Date(order.created_at).toLocaleDateString("id-ID"),
                `${order.pickup_address} → ${order.dropoff_address}`,
                <StatusBadge key={order.id} status={order.status} />,
                `Rp ${order.driver_payout.toLocaleString("id-ID")}`,
              ])}
            />
          </div>
        </>
      )}
    </main>
  );
}
