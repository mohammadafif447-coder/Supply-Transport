export type UserRole = "company" | "admin" | "driver";

export const ORDER_STATUSES = [
  "pending",
  "assigned",
  "picked_up",
  "in_transit",
  "delivered",
  "cancelled",
] as const;
export type OrderStatus = (typeof ORDER_STATUSES)[number];

export const CARGO_TYPES = ["general", "fragile", "frozen", "hazardous", "document"] as const;
export type CargoType = (typeof CARGO_TYPES)[number];

export const VEHICLE_TYPES = [
  "motor",
  "pickup",
  "box_small",
  "box_medium",
  "truck_cdd",
  "truck_cdd_long",
  "truck_fuso",
  "truck_trailer",
] as const;
export type VehicleType = (typeof VEHICLE_TYPES)[number];

export const CARGO_TYPE_LABELS: Record<CargoType, string> = {
  general: "Umum",
  fragile: "Mudah Pecah",
  frozen: "Beku",
  hazardous: "Berbahaya",
  document: "Dokumen",
};

export const VEHICLE_TYPE_LABELS: Record<VehicleType, string> = {
  motor: "Motor",
  pickup: "Pickup",
  box_small: "Box Kecil",
  box_medium: "Box Sedang",
  truck_cdd: "Truk CDD",
  truck_cdd_long: "Truk CDD Panjang",
  truck_fuso: "Truk Fuso",
  truck_trailer: "Truk Trailer",
};

export interface OrderListItem {
  id: string;
  status: OrderStatus;
  pickup_address: string;
  dropoff_address: string;
  cargo_type: CargoType;
  vehicle_type_requested: VehicleType;
  scheduled_pickup_at: string;
  total_price: number;
  created_at: string;
}

export interface OrderResponse {
  id: string;
  company_id: string;
  created_by_profile_id: string;
  driver_id: string | null;
  vehicle_id: string | null;
  status: OrderStatus;
  pickup_address: string;
  pickup_lat: number | null;
  pickup_lng: number | null;
  dropoff_address: string;
  dropoff_lat: number | null;
  dropoff_lng: number | null;
  cargo_type: CargoType;
  weight_kg: number;
  volume_m3: number | null;
  vehicle_type_requested: VehicleType;
  scheduled_pickup_at: string;
  notes: string | null;
  pod_required: boolean;
  pod_photo_url: string | null;
  total_price: number;
  driver_payout: number;
  platform_commission: number;
  commission_override_reason: string | null;
  cancelled_reason: string | null;
  delivered_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TrackingEventResponse {
  id: string;
  order_id: string;
  status: OrderStatus;
  note: string | null;
  lat: number | null;
  lng: number | null;
  created_by_profile_id: string;
  created_at: string;
}

export const DRIVER_STATUSES = ["pending_review", "approved", "rejected", "suspended"] as const;
export type DriverStatus = (typeof DRIVER_STATUSES)[number];

export const DRIVER_STATUS_LABELS: Record<DriverStatus, string> = {
  pending_review: "Menunggu Review",
  approved: "Disetujui",
  rejected: "Ditolak",
  suspended: "Ditangguhkan",
};

export const DRIVER_STATUS_STYLES: Record<DriverStatus, string> = {
  pending_review: "bg-silver text-iron",
  approved: "bg-lime text-iron font-semibold",
  rejected: "bg-red-100 text-red-700",
  suspended: "bg-olive/20 text-iron border border-olive",
};

export interface DriverListItem {
  id: string;
  full_name: string;
  phone_number: string | null;
  status: DriverStatus;
  is_available: boolean;
  created_at: string;
}

export interface AvailableVehicle {
  id: string;
  driver_id: string;
  plate_number: string;
  vehicle_type: VehicleType;
  max_weight_kg: number;
  stnk_photo_url: string | null;
  created_at: string;
  driver_full_name: string;
  driver_phone_number: string | null;
}

export interface DriverProfile {
  id: string;
  profile_id: string;
  full_name: string;
  phone_number: string | null;
  status: DriverStatus;
  is_available: boolean;
  rejection_reason: string | null;
  created_at: string;
}

export interface DriverOrderListItem extends OrderListItem {
  driver_payout: number;
}

export interface CommissionRule {
  id: string;
  vehicle_type: VehicleType;
  commission_percent: number;
  base_price: number;
  price_per_km: number;
  updated_at: string;
}

export function dashboardPathForRole(role: UserRole | null | undefined): string {
  switch (role) {
    case "admin":
      return "/admin/dashboard";
    case "driver":
      return "/driver/dashboard";
    default:
      return "/company/dashboard";
  }
}
