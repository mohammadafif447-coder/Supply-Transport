"use client";

import { useEffect, useState } from "react";
import { AdminNav } from "@/components/AdminNav";
import { DataTable } from "@/components/DataTable";
import { LogoutButton } from "@/components/LogoutButton";
import { api, ApiError } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import { VEHICLE_TYPE_LABELS, type CommissionRule } from "@/lib/types";

type EditableRule = {
  commission_percent: string;
  base_price: string;
  price_per_km: string;
};

export default function CommissionRulesPage() {
  const [email, setEmail] = useState<string | null>(null);
  const [rules, setRules] = useState<CommissionRule[]>([]);
  const [edits, setEdits] = useState<Record<string, EditableRule>>({});
  const [error, setError] = useState<string | null>(null);
  const [savingType, setSavingType] = useState<string | null>(null);
  const [savedType, setSavedType] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const supabase = createClient();
      const { data } = await supabase.auth.getUser();
      setEmail(data.user?.email ?? null);

      try {
        const result = await api.get<CommissionRule[]>("/commission-rules");
        setRules(result);
        const nextEdits: Record<string, EditableRule> = {};
        for (const rule of result) {
          nextEdits[rule.vehicle_type] = {
            commission_percent: String(rule.commission_percent),
            base_price: String(rule.base_price),
            price_per_km: String(rule.price_per_km),
          };
        }
        setEdits(nextEdits);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Gagal memuat aturan komisi.");
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, []);

  function updateField(vehicleType: string, field: keyof EditableRule, value: string) {
    setEdits((prev) => ({ ...prev, [vehicleType]: { ...prev[vehicleType], [field]: value } }));
  }

  async function handleSave(vehicleType: string) {
    const edit = edits[vehicleType];
    setSavingType(vehicleType);
    setSavedType(null);
    setError(null);
    try {
      const updated = await api.put<CommissionRule>(`/commission-rules/${vehicleType}`, {
        commission_percent: Number(edit.commission_percent),
        base_price: Number(edit.base_price),
        price_per_km: Number(edit.price_per_km),
      });
      setRules((prev) => prev.map((r) => (r.vehicle_type === vehicleType ? updated : r)));
      setSavedType(vehicleType);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal menyimpan aturan komisi.");
    } finally {
      setSavingType(null);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-4xl flex-col gap-6 p-8">
      <div className="flex items-center justify-between border-b border-silver pb-4">
        <div>
          <h1 className="text-xl font-semibold text-iron">Aturan Komisi</h1>
          <p className="text-sm text-olive">{email}</p>
        </div>
        <LogoutButton />
      </div>

      <AdminNav />

      {error && <p className="text-sm text-red-600">{error}</p>}

      {!isLoading && !error && (
        <DataTable
          columns={["Tipe Kendaraan", "Komisi (%)", "Tarif Dasar", "Tarif per Km", ""]}
          rows={rules.map((rule) => {
            const edit = edits[rule.vehicle_type];
            return [
              VEHICLE_TYPE_LABELS[rule.vehicle_type],
              <input
                key={`${rule.vehicle_type}-percent`}
                type="number"
                value={edit?.commission_percent ?? ""}
                onChange={(event) =>
                  updateField(rule.vehicle_type, "commission_percent", event.target.value)
                }
                className="w-20 rounded-md border border-silver bg-white px-2 py-1 text-sm text-iron focus:border-iron focus:outline-none"
              />,
              <input
                key={`${rule.vehicle_type}-base`}
                type="number"
                value={edit?.base_price ?? ""}
                onChange={(event) =>
                  updateField(rule.vehicle_type, "base_price", event.target.value)
                }
                className="w-28 rounded-md border border-silver bg-white px-2 py-1 text-sm text-iron focus:border-iron focus:outline-none"
              />,
              <input
                key={`${rule.vehicle_type}-perkm`}
                type="number"
                value={edit?.price_per_km ?? ""}
                onChange={(event) =>
                  updateField(rule.vehicle_type, "price_per_km", event.target.value)
                }
                className="w-24 rounded-md border border-silver bg-white px-2 py-1 text-sm text-iron focus:border-iron focus:outline-none"
              />,
              <div key={`${rule.vehicle_type}-save`} className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleSave(rule.vehicle_type)}
                  disabled={savingType === rule.vehicle_type}
                  className="rounded-md bg-lime px-3 py-1 text-sm font-semibold text-iron transition hover:brightness-95 disabled:cursor-not-allowed disabled:bg-silver"
                >
                  {savingType === rule.vehicle_type ? "..." : "Simpan"}
                </button>
                {savedType === rule.vehicle_type && (
                  <span className="text-xs text-olive">Tersimpan</span>
                )}
              </div>,
            ];
          })}
        />
      )}
    </main>
  );
}
