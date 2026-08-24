import Link from "next/link";
import { OrderForm } from "@/components/OrderForm";

export default function NewOrderPage() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-2xl flex-col gap-6 p-8">
      <div className="flex items-center justify-between border-b border-silver pb-4">
        <h1 className="text-xl font-semibold text-iron">Buat Order Baru</h1>
        <Link href="/company/dashboard" className="text-sm font-medium text-iron underline">
          Kembali
        </Link>
      </div>
      <OrderForm />
    </main>
  );
}
