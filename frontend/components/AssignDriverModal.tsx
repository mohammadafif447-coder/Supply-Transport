"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { AvailableVehicle, OrderListItem } from "@/lib/types";

export function AssignDriverModal({
  order,
  onClose,
  onAssigned,
}: {
  order: OrderListItem;
  onClose: () => void;
  onAssigned: () => void;
}) {
  const [vehicles, setVehicles] = useState<AvailableVehicle[]>([]);
  const [selectedVehicleId, setSelectedVehicleId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const result = await api.get<AvailableVehicle[]>(
          `/vehicles/available?vehicle_type=${order.vehicle_type_requested}`
        );
        setVehicles(result);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Gagal memuat daftar kendaraan.");
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, [order.vehicle_type_requested]);

  async function handleAssign() {
    const vehicle = vehicles.find((v) => v.id === selectedVehicleId);
    if (!vehicle) return;

    setError(null);
    setIsSubmitting(true);
    try {
      await api.patch(`/orders/${order.id}/assign`, {
        driver_id: vehicle.driver_id,
        vehicle_id: vehicle.id,
      });
      onAssigned();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal menugaskan driver.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg rounded-lg bg-white p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-iron">Assign Driver</h2>
          <button type="button" onClick={onClose} className="text-sm text-olive">
            Tutup
          </button>
        </div>

        <p className="mb-4 text-sm text-olive">
          Order {order.id.slice(0, 8)} — {order.pickup_address} → {order.dropoff_address}
        </p>

        {isLoading && <p className="text-sm text-olive">Memuat daftar kendaraan...</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}

        {!isLoading && !error && vehicles.length === 0 && (
          <p className="text-sm text-olive">
            Tidak ada driver &amp; kendaraan tersedia untuk tipe ini.
          </p>
        )}

        {!isLoading && vehicles.length > 0 && (
          <div className="flex flex-col gap-2">
            {vehicles.map((vehicle) => (
              <label
                key={vehicle.id}
                className={`flex cursor-pointer items-center justify-between rounded-md border px-3 py-2 text-sm ${
                  selectedVehicleId === vehicle.id
                    ? "border-iron bg-lime/10"
                    : "border-silver bg-white"
                }`}
              >
                <span>
                  {vehicle.driver_full_name} — {vehicle.plate_number}
                </span>
                <input
                  type="radio"
                  name="vehicle"
                  checked={selectedVehicleId === vehicle.id}
                  onChange={() => setSelectedVehicleId(vehicle.id)}
                />
              </label>
            ))}
          </div>
        )}

        <button
          type="button"
          onClick={handleAssign}
          disabled={!selectedVehicleId || isSubmitting}
          className="mt-4 w-full rounded-md bg-lime px-4 py-2 font-semibold text-iron transition hover:brightness-95 disabled:cursor-not-allowed disabled:bg-silver disabled:text-olive"
        >
          {isSubmitting ? "Memproses..." : "Assign Driver"}
        </button>
      </div>
    </div>
  );
}
