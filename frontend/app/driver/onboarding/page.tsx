"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { api, ApiError } from "@/lib/api";
import { VEHICLE_TYPE_LABELS, VEHICLE_TYPES, type VehicleType } from "@/lib/types";

type FileField = "ktp_photo" | "sim_photo" | "stnk_photo";

export default function DriverOnboardingPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [ktpNumber, setKtpNumber] = useState("");
  const [simNumber, setSimNumber] = useState("");
  const [bankName, setBankName] = useState("");
  const [bankAccountNumber, setBankAccountNumber] = useState("");
  const [vehiclePlateNumber, setVehiclePlateNumber] = useState("");
  const [vehicleType, setVehicleType] = useState<VehicleType>("motor");
  const [vehicleMaxWeightKg, setVehicleMaxWeightKg] = useState("");
  const [files, setFiles] = useState<Record<FileField, File | null>>({
    ktp_photo: null,
    sim_photo: null,
    stnk_photo: null,
  });
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function setFile(field: FileField, file: File | null) {
    setFiles((prev) => ({ ...prev, [field]: file }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!files.ktp_photo || !files.sim_photo || !files.stnk_photo) {
      setError("Foto KTP, SIM, dan STNK wajib diunggah.");
      return;
    }

    const formData = new FormData();
    formData.append("full_name", fullName);
    formData.append("phone_number", phoneNumber);
    formData.append("ktp_number", ktpNumber);
    formData.append("sim_number", simNumber);
    formData.append("bank_name", bankName);
    formData.append("bank_account_number", bankAccountNumber);
    formData.append("vehicle_plate_number", vehiclePlateNumber);
    formData.append("vehicle_type", vehicleType);
    formData.append("vehicle_max_weight_kg", vehicleMaxWeightKg);
    formData.append("ktp_photo", files.ktp_photo);
    formData.append("sim_photo", files.sim_photo);
    formData.append("stnk_photo", files.stnk_photo);

    setIsSubmitting(true);
    try {
      await api.postFormData("/drivers", formData);
      router.push("/driver/dashboard");
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal menyimpan profil driver.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-2xl flex-col gap-6 p-8">
      <div className="border-b border-silver pb-4">
        <h1 className="text-xl font-semibold text-iron">Lengkapi Profil Mitra Driver</h1>
        <p className="mt-1 text-sm text-olive">
          Data ini wajib diisi dan akan direview oleh admin sebelum Anda bisa menerima order.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-iron">Nama Lengkap</label>
          <input
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            required
            minLength={3}
            maxLength={100}
            className="w-full rounded-md border border-silver bg-white px-3 py-2 text-iron focus:border-iron focus:outline-none"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-iron">No. HP</label>
          <input
            value={phoneNumber}
            onChange={(event) => setPhoneNumber(event.target.value)}
            required
            placeholder="081234567890"
            className="w-full rounded-md border border-silver bg-white px-3 py-2 text-iron focus:border-iron focus:outline-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-iron">Nomor KTP</label>
            <input
              value={ktpNumber}
              onChange={(event) => setKtpNumber(event.target.value)}
              required
              maxLength={16}
              placeholder="16 digit"
              className="w-full rounded-md border border-silver bg-white px-3 py-2 text-iron focus:border-iron focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-iron">Nomor SIM</label>
            <input
              value={simNumber}
              onChange={(event) => setSimNumber(event.target.value)}
              required
              minLength={5}
              maxLength={30}
              className="w-full rounded-md border border-silver bg-white px-3 py-2 text-iron focus:border-iron focus:outline-none"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-iron">Nama Bank</label>
            <input
              value={bankName}
              onChange={(event) => setBankName(event.target.value)}
              required
              minLength={2}
              maxLength={100}
              className="w-full rounded-md border border-silver bg-white px-3 py-2 text-iron focus:border-iron focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-iron">No. Rekening</label>
            <input
              value={bankAccountNumber}
              onChange={(event) => setBankAccountNumber(event.target.value)}
              required
              maxLength={20}
              className="w-full rounded-md border border-silver bg-white px-3 py-2 text-iron focus:border-iron focus:outline-none"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-iron">Plat Kendaraan</label>
            <input
              value={vehiclePlateNumber}
              onChange={(event) => setVehiclePlateNumber(event.target.value.toUpperCase())}
              required
              minLength={4}
              maxLength={15}
              placeholder="B 1234 XYZ"
              className="w-full rounded-md border border-silver bg-white px-3 py-2 text-iron focus:border-iron focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-iron">Jenis Kendaraan</label>
            <select
              value={vehicleType}
              onChange={(event) => setVehicleType(event.target.value as VehicleType)}
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

        <div>
          <label className="mb-1 block text-sm font-medium text-iron">
            Kapasitas Maksimal (kg)
          </label>
          <input
            type="number"
            value={vehicleMaxWeightKg}
            onChange={(event) => setVehicleMaxWeightKg(event.target.value)}
            required
            min={1}
            max={50000}
            className="w-full rounded-md border border-silver bg-white px-3 py-2 text-iron focus:border-iron focus:outline-none"
          />
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-iron">Foto KTP</label>
            <input
              type="file"
              accept="image/jpeg,image/png,application/pdf"
              required
              onChange={(event) => setFile("ktp_photo", event.target.files?.[0] ?? null)}
              className="w-full text-sm text-iron"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-iron">Foto SIM</label>
            <input
              type="file"
              accept="image/jpeg,image/png,application/pdf"
              required
              onChange={(event) => setFile("sim_photo", event.target.files?.[0] ?? null)}
              className="w-full text-sm text-iron"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-iron">Foto STNK</label>
            <input
              type="file"
              accept="image/jpeg,image/png,application/pdf"
              required
              onChange={(event) => setFile("stnk_photo", event.target.files?.[0] ?? null)}
              className="w-full text-sm text-iron"
            />
          </div>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={isSubmitting}
          className="mt-2 w-full rounded-md bg-lime px-4 py-2 font-semibold text-iron transition hover:brightness-95 disabled:cursor-not-allowed disabled:bg-silver disabled:text-olive"
        >
          {isSubmitting ? "Menyimpan..." : "Simpan & Kirim untuk Review"}
        </button>
      </form>
    </main>
  );
}
