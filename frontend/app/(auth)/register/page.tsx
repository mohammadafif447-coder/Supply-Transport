"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { createClient } from "@/lib/supabase/client";
import type { UserRole } from "@/lib/types";

type RegisterRole = Extract<UserRole, "company" | "driver">;

export default function RegisterPage() {
  const router = useRouter();
  const [role, setRole] = useState<RegisterRole>("company");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [confirmationPending, setConfirmationPending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    const supabase = createClient();
    const { data, error: signUpError } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: { role, full_name: fullName },
      },
    });

    if (signUpError) {
      setError(signUpError.message);
      setIsSubmitting(false);
      return;
    }

    if (!data.session) {
      setConfirmationPending(true);
      setIsSubmitting(false);
      return;
    }

    router.push(role === "company" ? "/company/onboarding" : "/driver/onboarding");
    router.refresh();
  }

  if (confirmationPending) {
    return (
      <p className="text-center text-sm text-iron">
        Akun berhasil dibuat. Silakan cek email <span className="font-medium">{email}</span> untuk
        konfirmasi sebelum masuk.
      </p>
    );
  }

  return (
    <div>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div>
          <span className="mb-1 block text-sm font-medium text-iron">Daftar sebagai</span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setRole("company")}
              className={`flex-1 rounded-md border px-3 py-2 text-sm font-medium ${
                role === "company"
                  ? "border-iron bg-iron text-white"
                  : "border-silver bg-white text-iron"
              }`}
            >
              Perusahaan
            </button>
            <button
              type="button"
              onClick={() => setRole("driver")}
              className={`flex-1 rounded-md border px-3 py-2 text-sm font-medium ${
                role === "driver"
                  ? "border-iron bg-iron text-white"
                  : "border-silver bg-white text-iron"
              }`}
            >
              Mitra Driver
            </button>
          </div>
        </div>

        <div>
          <label htmlFor="fullName" className="mb-1 block text-sm font-medium text-iron">
            Nama Lengkap
          </label>
          <input
            id="fullName"
            type="text"
            required
            minLength={3}
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            className="w-full rounded-md border border-silver bg-white px-3 py-2 text-iron focus:border-iron focus:outline-none"
          />
        </div>

        <div>
          <label htmlFor="email" className="mb-1 block text-sm font-medium text-iron">
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="w-full rounded-md border border-silver bg-white px-3 py-2 text-iron focus:border-iron focus:outline-none"
          />
        </div>

        <div>
          <label htmlFor="password" className="mb-1 block text-sm font-medium text-iron">
            Kata Sandi
          </label>
          <input
            id="password"
            type="password"
            required
            minLength={6}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="w-full rounded-md border border-silver bg-white px-3 py-2 text-iron focus:border-iron focus:outline-none"
          />
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={isSubmitting}
          className="mt-2 w-full rounded-md bg-lime px-4 py-2 font-semibold text-iron transition hover:brightness-95 disabled:cursor-not-allowed disabled:bg-silver disabled:text-olive"
        >
          {isSubmitting ? "Memproses..." : "Daftar"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-olive">
        Sudah punya akun?{" "}
        <Link href="/login" className="font-medium text-iron underline">
          Masuk
        </Link>
      </p>
    </div>
  );
}
