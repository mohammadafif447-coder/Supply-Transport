from datetime import datetime, timezone

from fastapi import HTTPException, status
from postgrest.exceptions import APIError

from app.core.errors import db_error_to_http
from app.db.supabase_client import get_supabase
from app.models.commission_rule import CommissionRuleResponse, CommissionRuleUpdate
from app.models.enums import VehicleType


def list_commission_rules() -> list[CommissionRuleResponse]:
    supabase = get_supabase()
    result = supabase.table("commission_rules").select("*").order("vehicle_type").execute()
    return [CommissionRuleResponse(**row) for row in result.data]


def update_commission_rule(
    *, vehicle_type: VehicleType, payload: CommissionRuleUpdate
) -> CommissionRuleResponse:
    supabase = get_supabase()
    try:
        result = (
            supabase.table("commission_rules")
            .update(
                {
                    "commission_percent": payload.commission_percent,
                    "base_price": payload.base_price,
                    "price_per_km": payload.price_per_km,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("vehicle_type", vehicle_type.value)
            .execute()
        )
    except APIError as exc:
        raise db_error_to_http(exc) from exc

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aturan tarif untuk tipe kendaraan '{vehicle_type.value}' tidak ditemukan.",
        )
    return CommissionRuleResponse(**result.data[0])
