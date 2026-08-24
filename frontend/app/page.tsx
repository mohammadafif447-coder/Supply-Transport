import Link from "next/link";

export default function HomePage() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 bg-smoke px-4 text-center">
      <h1 className="text-3xl font-semibold text-iron">Supply Transport</h1>
      <p className="max-w-md text-olive">
        Platform logistik B2B yang menghubungkan perusahaan dengan mitra driver &amp; truk.
      </p>
      <div className="flex gap-3">
        <Link
          href="/login"
          className="rounded-md bg-lime px-5 py-2 font-semibold text-iron transition hover:brightness-95"
        >
          Masuk
        </Link>
        <Link
          href="/register"
          className="rounded-md border border-iron px-5 py-2 font-semibold text-iron transition hover:bg-iron hover:text-white"
        >
          Daftar
        </Link>
      </div>
    </main>
  );
}
