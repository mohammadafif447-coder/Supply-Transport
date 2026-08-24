"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { api, ApiError } from "@/lib/api";

export default function CompanyOnboardingPage() {
  const router = useRouter();
  const [companyName, setCompanyName] = useState("");
  const [companyAddress, setCompanyAddress] = useState("");
  const [taxId, setTaxId] = useState("");
  const [billingEmail, setBillingEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await api.post("/companies", {
        company_name: companyName,
        company_address: companyAddress,
        tax_id: taxId || undefined,
        billing_email: billingEmail || undefined,
      });
      router.push("/company/dashboard");
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal menyimpan profil perusahaan.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-2xl flex-col gap-6 p-8">
      <div className="border-b border-silver pb-4">
        <h1 className="text-xl font-semibold text-iron">Lengkapi Profil Perusahaan</h1>
        <p className="mt-1 text-sm text-olive">
          Data ini wajib diisi sebelum Anda dapat membuat order.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-iron">Nama Perusahaan</label>
          <input
            value={companyName}
            onChange={(event) => setCompanyName(event.target.value)}
            required
            minLength={2}
            maxLength={150}
            className="w-full rounded-md border border-silver bg-white px-3 py-2 text-iron focus:border-iron focus:outline-none"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-iron">Alamat Perusahaan</label>
          <input
            value={companyAddress}
            onChange={(event) => setCompanyAddress(event.target.value)}
            required
            minLength={10}
            maxLength={255}
            className="w-full rounded-md border border-silver bg-white px-3 py-2 text-iron focus:border-iron focus:outline-none"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-iron">NPWP (opsional)</label>
          <input
            value={taxId}
            onChange={(event) => setTaxId(event.target.value)}
            maxLength={30}
            className="w-full rounded-md border border-silver bg-white px-3 py-2 text-iron focus:border-iron focus:outline-none"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-iron">
            Email Penagihan (opsional)
          </label>
          <input
            type="email"
            value={billingEmail}
            onChange={(event) => setBillingEmail(event.target.value)}
            className="w-full rounded-md border border-silver bg-white px-3 py-2 text-iron focus:border-iron focus:outline-none"
          />
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={isSubmitting}
          className="mt-2 w-full rounded-md bg-lime px-4 py-2 font-semibold text-iron transition hover:brightness-95 disabled:cursor-not-allowed disabled:bg-silver disabled:text-olive"
        >
          {isSubmitting ? "Menyimpan..." : "Simpan & Lanjutkan"}
        </button>
      </form>
    </main>
  );
}
