from fastapi import HTTPException, status

from app.db.supabase_client import get_supabase
from app.models.enums import VehicleType
from app.utils.geo import haversine_km


def calculate_order_pricing(
    *,
    vehicle_type: VehicleType,
    pickup_lat: float | None,
    pickup_lng: float | None,
    dropoff_lat: float | None,
    dropoff_lng: float | None,
) -> dict:
    supabase = get_supabase()
    rule = (
        supabase.table("commission_rules")
        .select("commission_percent, base_price, price_per_km")
        .eq("vehicle_type", vehicle_type.value)
        .maybe_single()
        .execute()
    )
    if not rule or not rule.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Aturan tarif untuk tipe kendaraan '{vehicle_type.value}' belum dikonfigurasi.",
        )

    distance_km = 0.0
    coords = (pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)
    if all(c is not None for c in coords):
        distance_km = haversine_km(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)

    base_price = float(rule.data["base_price"])
    price_per_km = float(rule.data["price_per_km"])
    commission_percent = float(rule.data["commission_percent"])

    total_price = round(base_price + price_per_km * distance_km, 2)
    platform_commission = round(total_price * commission_percent / 100, 2)
    driver_payout = round(total_price - platform_commission, 2)

    return {
        "total_price": total_price,
        "driver_payout": driver_payout,
        "platform_commission": platform_commission,
    }
