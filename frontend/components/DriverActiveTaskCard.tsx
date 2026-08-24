"use client";

import { useRef, useState } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import { api, ApiError } from "@/lib/api";
import type { DriverOrderListItem, OrderStatus } from "@/lib/types";

const NEXT_ACTION: Partial<Record<OrderStatus, { label: string; nextStatus: OrderStatus }>> = {
  assigned: { label: "Konfirmasi Jemput Barang", nextStatus: "picked_up" },
  picked_up: { label: "Mulai Perjalanan", nextStatus: "in_transit" },
};

export function DriverActiveTaskCard({
  order,
  onUpdated,
}: {
  order: DriverOrderListItem;
  onUpdated: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function advanceStatus(nextStatus: OrderStatus) {
    setError(null);
    setIsSubmitting(true);
    try {
      await api.patch(`/orders/${order.id}/status`, { status: nextStatus });
      onUpdated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal memperbarui status.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handlePodUpload(file: File) {
    setError(null);
    setIsSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("photo", file);
      await api.postFormData(`/orders/${order.id}/pod`, formData);
      await advanceStatus("delivered");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal mengunggah bukti pengiriman.");
      setIsSubmitting(false);
    }
  }

  const nextAction = NEXT_ACTION[order.status];

  return (
    <div className="rounded-lg border border-silver bg-white p-6">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-iron">Tugas Aktif Saat Ini</h2>
        <StatusBadge status={order.status} />
      </div>
      <p className="mb-1 text-sm text-olive">Jemput</p>
      <p className="mb-3 text-sm text-iron">{order.pickup_address}</p>
      <p className="mb-1 text-sm text-olive">Antar</p>
      <p className="mb-4 text-sm text-iron">{order.dropoff_address}</p>

      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

      {nextAction && (
        <button
          type="button"
          disabled={isSubmitting}
          onClick={() => advanceStatus(nextAction.nextStatus)}
          className="w-full rounded-md bg-lime px-4 py-3 font-semibold text-iron transition hover:brightness-95 disabled:cursor-not-allowed disabled:bg-silver disabled:text-olive"
        >
          {isSubmitting ? "Memproses..." : nextAction.label}
        </button>
      )}

      {order.status === "in_transit" && (
        <>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,application/pdf"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) handlePodUpload(file);
            }}
          />
          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => fileInputRef.current?.click()}
            className="w-full rounded-md bg-lime px-4 py-3 font-semibold text-iron transition hover:brightness-95 disabled:cursor-not-allowed disabled:bg-silver disabled:text-olive"
          >
            {isSubmitting ? "Memproses..." : "Sampai Tujuan & Upload Bukti"}
          </button>
        </>
      )}
    </div>
  );
}
