"use client";

import { useEffect, useState } from "react";
import { AdminNav } from "@/components/AdminNav";
import { DataTable } from "@/components/DataTable";
import { LogoutButton } from "@/components/LogoutButton";
import { ReviewDriverModal } from "@/components/ReviewDriverModal";
import { api, ApiError } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import { DRIVER_STATUS_LABELS, DRIVER_STATUS_STYLES, type DriverListItem } from "@/lib/types";

function DriverStatusBadge({ status }: { status: DriverListItem["status"] }) {
  return (
    <span
      className={`inline-block rounded-full px-3 py-1 text-xs font-medium ${DRIVER_STATUS_STYLES[status]}`}
    >
      {DRIVER_STATUS_LABELS[status]}
    </span>
  );
}

export default function AdminDriversPage() {
  const [email, setEmail] = useState<string | null>(null);
  const [drivers, setDrivers] = useState<DriverListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [reviewingDriver, setReviewingDriver] = useState<DriverListItem | null>(null);

  async function loadDrivers() {
    try {
      const result = await api.get<DriverListItem[]>("/drivers");
      setDrivers(result);
    } catch (err) {
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
      await loadDrivers();
    }
    init();
  }, []);

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-6 p-8">
      <div className="flex items-center justify-between border-b border-silver pb-4">
        <div>
          <h1 className="text-xl font-semibold text-iron">Mitra Driver</h1>
          <p className="text-sm text-olive">{email}</p>
        </div>
        <LogoutButton />
      </div>

      <AdminNav />

      {error && <p className="text-sm text-red-600">{error}</p>}

      {!isLoading && !error && (
        <DataTable
          columns={["Nama", "No. HP", "Status", "Tersedia", "Terdaftar", "Aksi"]}
          rows={drivers.map((driver) => [
            driver.full_name,
            driver.phone_number ?? "-",
            <DriverStatusBadge key={driver.id} status={driver.status} />,
            driver.is_available ? "Ya" : "Tidak",
            new Date(driver.created_at).toLocaleDateString("id-ID"),
            driver.status === "pending_review" ? (
              <button
                key={driver.id}
                type="button"
                onClick={() => setReviewingDriver(driver)}
                className="rounded-md border border-olive px-3 py-1 text-sm font-medium text-iron transition hover:bg-iron hover:text-white"
              >
                Review
              </button>
            ) : (
              <span key={driver.id} className="text-sm text-olive">
                -
              </span>
            ),
          ])}
        />
      )}

      {reviewingDriver && (
        <ReviewDriverModal
          driver={reviewingDriver}
          onClose={() => setReviewingDriver(null)}
          onReviewed={async () => {
            setReviewingDriver(null);
            await loadDrivers();
          }}
        />
      )}
    </main>
  );
}
