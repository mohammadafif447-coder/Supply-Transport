import type { OrderStatus } from "@/lib/types";

const STATUS_STYLES: Record<OrderStatus, string> = {
  pending: "bg-silver text-iron",
  assigned: "bg-olive/20 text-iron border border-olive",
  picked_up: "bg-lime/40 text-iron",
  in_transit: "bg-lime text-iron font-semibold",
  delivered: "bg-iron text-white",
  cancelled: "bg-red-100 text-red-700",
};

export const STATUS_LABELS: Record<OrderStatus, string> = {
  pending: "Menunggu",
  assigned: "Ditugaskan",
  picked_up: "Dijemput",
  in_transit: "Dalam Perjalanan",
  delivered: "Selesai",
  cancelled: "Dibatalkan",
};

export function StatusBadge({ status }: { status: OrderStatus }) {
  return (
    <span
      className={`inline-block rounded-full px-3 py-1 text-xs font-medium ${STATUS_STYLES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
