"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { DriverListItem } from "@/lib/types";

export function ReviewDriverModal({
  driver,
  onClose,
  onReviewed,
}: {
  driver: DriverListItem;
  onClose: () => void;
  onReviewed: () => void;
}) {
  const [rejectionReason, setRejectionReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleReview(nextStatus: "approved" | "rejected") {
    if (nextStatus === "rejected" && rejectionReason.trim().length < 3) {
      setError("Alasan penolakan wajib diisi (minimal 3 karakter).");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await api.patch(`/drivers/${driver.id}/review`, {
        status: nextStatus,
        rejection_reason: nextStatus === "rejected" ? rejectionReason : null,
      });
      onReviewed();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal memproses review driver.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-lg bg-white p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-iron">Review Driver</h2>
          <button type="button" onClick={onClose} className="text-sm text-olive">
            Tutup
          </button>
        </div>

        <p className="mb-4 text-sm text-iron">{driver.full_name}</p>

        <label className="mb-1 block text-sm font-medium text-iron">
          Alasan Penolakan (wajib jika ditolak)
        </label>
        <textarea
          value={rejectionReason}
          onChange={(event) => setRejectionReason(event.target.value)}
          rows={3}
          className="mb-4 w-full rounded-md border border-silver bg-white px-3 py-2 text-sm text-iron focus:border-iron focus:outline-none"
        />

        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

        <div className="flex gap-2">
          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => handleReview("approved")}
            className="flex-1 rounded-md bg-lime px-4 py-2 text-sm font-semibold text-iron transition hover:brightness-95 disabled:cursor-not-allowed disabled:bg-silver"
          >
            Setujui
          </button>
          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => handleReview("rejected")}
            className="flex-1 rounded-md border border-red-600 px-4 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed"
          >
            Tolak
          </button>
        </div>
      </div>
    </div>
  );
}
