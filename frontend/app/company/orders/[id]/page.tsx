"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import { api, ApiError } from "@/lib/api";
import { CARGO_TYPE_LABELS, VEHICLE_TYPE_LABELS } from "@/lib/types";
import type { OrderResponse, TrackingEventResponse } from "@/lib/types";

const CANCELLABLE_STATUSES = new Set(["pending", "assigned"]);

export default function OrderDetailPage() {
  const params = useParams<{ id: string }>();
  const [order, setOrder] = useState<OrderResponse | null>(null);
  const [tracking, setTracking] = useState<TrackingEventResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showCancelForm, setShowCancelForm] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelError, setCancelError] = useState<string | null>(null);
  const [isCancelling, setIsCancelling] = useState(false);

  async function load() {
    try {
      const [orderResult, trackingResult] = await Promise.all([
        api.get<OrderResponse>(`/orders/${params.id}`),
        api.get<TrackingEventResponse[]>(`/orders/${params.id}/tracking`),
      ]);
      setOrder(orderResult);
      setTracking(trackingResult);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal memuat detail order.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial fetch-on-mount; load() is reused after cancel too
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.id]);

  async function handleCancel() {
    if (cancelReason.trim().length < 3) {
      setCancelError("Alasan pembatalan wajib diisi (minimal 3 karakter).");
      return;
    }
    setCancelError(null);
    setIsCancelling(true);
    try {
      await api.patch(`/orders/${params.id}/cancel`, { reason: cancelReason });
      setShowCancelForm(false);
      setCancelReason("");
      await load();
    } catch (err) {
      setCancelError(err instanceof ApiError ? err.message : "Gagal membatalkan order.");
    } finally {
      setIsCancelling(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col gap-6 p-8">
      <div className="flex items-center justify-between border-b border-silver pb-4">
        <h1 className="text-xl font-semibold text-iron">Detail Order</h1>
        <Link href="/company/dashboard" className="text-sm font-medium text-iron underline">
          Kembali
        </Link>
      </div>

      {isLoading && <p className="text-olive">Memuat...</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {order && (
        <>
          <div className="rounded-lg border border-silver bg-white p-6">
            <div className="mb-4 flex items-center justify-between">
              <span className="font-mono text-sm text-olive">{order.id}</span>
              <StatusBadge status={order.status} />
            </div>
            <dl className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <dt className="text-olive">Alamat Jemput</dt>
                <dd className="text-iron">{order.pickup_address}</dd>
              </div>
              <div>
                <dt className="text-olive">Alamat Antar</dt>
                <dd className="text-iron">{order.dropoff_address}</dd>
              </div>
              <div>
                <dt className="text-olive">Jenis Barang</dt>
                <dd className="text-iron">{CARGO_TYPE_LABELS[order.cargo_type]}</dd>
              </div>
              <div>
                <dt className="text-olive">Tipe Kendaraan</dt>
                <dd className="text-iron">{VEHICLE_TYPE_LABELS[order.vehicle_type_requested]}</dd>
              </div>
              <div>
                <dt className="text-olive">Berat</dt>
                <dd className="text-iron">{order.weight_kg} kg</dd>
              </div>
              <div>
                <dt className="text-olive">Total Harga</dt>
                <dd className="text-iron">Rp {order.total_price.toLocaleString("id-ID")}</dd>
              </div>
              {order.notes && (
                <div className="col-span-2">
                  <dt className="text-olive">Catatan</dt>
                  <dd className="text-iron">{order.notes}</dd>
                </div>
              )}
              {order.status === "cancelled" && order.cancelled_reason && (
                <div className="col-span-2">
                  <dt className="text-olive">Alasan Dibatalkan</dt>
                  <dd className="text-red-700">{order.cancelled_reason}</dd>
                </div>
              )}
            </dl>

            {order.status === "delivered" && order.pod_photo_url && (
              <div className="mt-4">
                <p className="mb-2 text-sm text-olive">Bukti Pengiriman (POD)</p>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={order.pod_photo_url}
                  alt="Bukti pengiriman"
                  className="max-w-xs rounded-md border border-silver"
                />
              </div>
            )}

            {CANCELLABLE_STATUSES.has(order.status) && (
              <div className="mt-4 border-t border-silver pt-4">
                {!showCancelForm ? (
                  <button
                    type="button"
                    onClick={() => setShowCancelForm(true)}
                    className="rounded-md border border-red-600 px-4 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-50"
                  >
                    Batalkan Order
                  </button>
                ) : (
                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-medium text-iron">Alasan Pembatalan</label>
                    <textarea
                      value={cancelReason}
                      onChange={(event) => setCancelReason(event.target.value)}
                      rows={2}
                      className="w-full rounded-md border border-silver bg-white px-3 py-2 text-sm text-iron focus:border-iron focus:outline-none"
                    />
                    {cancelError && <p className="text-sm text-red-600">{cancelError}</p>}
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={isCancelling}
                        onClick={handleCancel}
                        className="rounded-md bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:brightness-95 disabled:cursor-not-allowed disabled:bg-silver"
                      >
                        {isCancelling ? "Memproses..." : "Konfirmasi Batalkan"}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setShowCancelForm(false);
                          setCancelError(null);
                        }}
                        className="rounded-md border border-silver px-4 py-2 text-sm font-medium text-iron"
                      >
                        Tutup
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-silver bg-white p-6">
            <h2 className="mb-4 text-sm font-semibold text-iron">Riwayat Status</h2>
            <ol className="flex flex-col gap-3">
              {tracking.map((event) => (
                <li key={event.id} className="flex items-center gap-3">
                  <StatusBadge status={event.status} />
                  <span className="text-sm text-olive">
                    {new Date(event.created_at).toLocaleString("id-ID")}
                  </span>
                  {event.note && <span className="text-sm text-iron">— {event.note}</span>}
                </li>
              ))}
              {tracking.length === 0 && (
                <li className="text-sm text-olive">Belum ada riwayat status.</li>
              )}
            </ol>
          </div>
        </>
      )}
    </main>
  );
}
