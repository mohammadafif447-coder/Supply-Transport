"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { z } from "zod";
import { api, ApiError } from "@/lib/api";
import {
  CARGO_TYPE_LABELS,
  CARGO_TYPES,
  VEHICLE_TYPE_LABELS,
  VEHICLE_TYPES,
  type CargoType,
  type VehicleType,
} from "@/lib/types";

// Mirrors backend/app/models/order.py::OrderCreate — keep field names & rules identical.
const orderCreateSchema = z.object({
  pickup_address: z.string().min(10, "Alamat jemput minimal 10 karakter.").max(255),
  dropoff_address: z.string().min(10, "Alamat antar minimal 10 karakter.").max(255),
  cargo_type: z.enum(CARGO_TYPES),
  weight_kg: z.coerce
    .number({ message: "Berat wajib diisi." })
    .gt(0, "Berat harus lebih dari 0.")
    .max(30000, "Berat maksimal 30.000 kg."),
  volume_m3: z.coerce.number().min(0, "Volume tidak boleh negatif.").optional(),
  vehicle_type_requested: z.enum(VEHICLE_TYPES),
  scheduled_pickup_at: z
    .string()
    .min(1, "Waktu jemput wajib diisi.")
    .refine(
      (value) => new Date(value).getTime() >= Date.now() + 60 * 60 * 1000,
      "Waktu jemput harus minimal 1 jam dari sekarang."
    ),
  notes: z.string().max(500).optional(),
  pod_required: z.boolean(),
});

type FormValues = {
  pickup_address: string;
  dropoff_address: string;
  cargo_type: CargoType;
  weight_kg: string;
  volume_m3: string;
  vehicle_type_requested: VehicleType;
  scheduled_pickup_at: string;
  notes: string;
  pod_required: boolean;
};

const initialValues: FormValues = {
  pickup_address: "",
  dropoff_address: "",
  cargo_type: "general",
  weight_kg: "",
  volume_m3: "",
  vehicle_type_requested: "motor",
  scheduled_pickup_at: "",
  notes: "",
  pod_required: true,
};

export function OrderForm() {
  const router = useRouter();
  const [values, setValues] = useState<FormValues>(initialValues);
  const [errors, setErrors] = useState<Partial<Record<keyof FormValues, string>>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function update<K extends keyof FormValues>(key: K, value: FormValues[K]) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);

    const parsed = orderCreateSchema.safeParse({
      ...values,
      volume_m3: values.volume_m3 === "" ? undefined : values.volume_m3,
      notes: values.notes === "" ? undefined : values.notes,
    });

    if (!parsed.success) {
      const fieldErrors: Partial<Record<keyof FormValues, string>> = {};
      for (const issue of parsed.error.issues) {
        const key = issue.path[0] as keyof FormValues;
        fieldErrors[key] = issue.message;
      }
      setErrors(fieldErrors);
      return;
    }

    setErrors({});
    setIsSubmitting(true);
    try {
      await api.post("/orders", {
        ...parsed.data,
        scheduled_pickup_at: new Date(parsed.data.scheduled_pickup_at).toISOString(),
      });
      router.push("/company/dashboard");
      router.refresh();
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        router.push("/company/onboarding");
        return;
      }
      setSubmitError(err instanceof ApiError ? err.message : "Gagal membuat order.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-iron">Alamat Jemput</label>
        <input
          value={values.pickup_address}
          onChange={(event) => update("pickup_address", event.target.value)}
          className="w-full rounded-md border border-silver bg-white px-3 py-2 text-iron focus:border-iron focus:outline-none"
        />
        {errors.pickup_address && (
          <p className="mt-1 text-sm text-red-600">{errors.pickup_address}</p>
        )}
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-iron">Alamat Antar</label>
        <input
          value={values.dropoff_address}
          onChange={(event) => update("dropoff_address", event.target.value)}
          className="w-full rounded-md border border-silver bg-white px-3 py-2 text-iron focus:border-iron focus:outline-none"
        />
        {errors.dropoff_address && (
          <p className="mt-1 text-sm text-red-600">{errors.dropoff_address}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-iron">Jenis Barang</label>
          <select
            value={values.cargo_type}
            onChange={(event) => update("cargo_type", event.target.value as CargoType)}
            className="w-full rounded-md border border-silver bg-white px-3 py-2 text-iron focus:border-iron focus:outline-none"
          >
            {CARGO_TYPES.map((type) => (
              <option key={type} value={type}>
                {CARGO_TYPE_LABELS[type]}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-iron">Jenis Kendaraan</label>
          <select
            value={values.vehicle_type_requested}
            onChange={(event) =>
              update("vehicle_type_requested", event.target.value as VehicleType)
            }
            className="w-full rounded-md border border-silver bg-white px-3 py-2 text-iron focus:border-iron focus:outline-none"
          >
            {VEHICLE_TYPES.map((type) => (
              <option key={type} value={type}>
                {VEHICLE_TYPE_LABELS[type]}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-iron">Berat (kg)</label>
          <input
            type="number"
            value={values.weight_kg}
            onChange={(event) => update("weight_kg", event.target.value)}
            className="w-full rounded-md border border-silver bg-white px-3 py-2 text-iron focus:border-iron focus:outline-none"
          />
          {errors.weight_kg && <p className="mt-1 text-sm text-red-600">{errors.weight_kg}</p>}
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-iron">
            Volume (m&sup3;, opsional)
          </label>
          <input
            type="number"
            value={values.volume_m3}
            onChange={(event) => update("volume_m3", event.target.value)}
            className="w-full rounded-md border border-silver bg-white px-3 py-2 text-iron focus:border-iron focus:outline-none"
          />
          {errors.volume_m3 && <p className="mt-1 text-sm text-red-600">{errors.volume_m3}</p>}
        </div>
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-iron">Waktu Jemput</label>
        <input
          type="datetime-local"
          value={values.scheduled_pickup_at}
          onChange={(event) => update("scheduled_pickup_at", event.target.value)}
          className="w-full rounded-md border border-silver bg-white px-3 py-2 text-iron focus:border-iron focus:outline-none"
        />
        {errors.scheduled_pickup_at && (
          <p className="mt-1 text-sm text-red-600">{errors.scheduled_pickup_at}</p>
        )}
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-iron">Catatan (opsional)</label>
        <textarea
          value={values.notes}
          onChange={(event) => update("notes", event.target.value)}
          maxLength={500}
          rows={3}
          className="w-full rounded-md border border-silver bg-white px-3 py-2 text-iron focus:border-iron focus:outline-none"
        />
        {errors.notes && <p className="mt-1 text-sm text-red-600">{errors.notes}</p>}
      </div>

      <label className="flex items-center gap-2 text-sm text-iron">
        <input
          type="checkbox"
          checked={values.pod_required}
          onChange={(event) => update("pod_required", event.target.checked)}
        />
        Wajib bukti pengiriman (POD) sebelum status selesai
      </label>

      {submitError && <p className="text-sm text-red-600">{submitError}</p>}

      <button
        type="submit"
        disabled={isSubmitting}
        className="mt-2 w-full rounded-md bg-lime px-4 py-2 font-semibold text-iron transition hover:brightness-95 disabled:cursor-not-allowed disabled:bg-silver disabled:text-olive"
      >
        {isSubmitting ? "Memproses..." : "Buat Order"}
      </button>
    </form>
  );
}
