from fastapi import HTTPException, status

from app.db.supabase_client import get_supabase
from app.models.enums import OrderStatus
from app.models.user import CurrentUser, UserRole
from app.services.company_service import get_company_by_owner
from app.services.excel_service import build_orders_report

EXPORT_SELECT_COLUMNS = (
    "id, created_at, pickup_address, dropoff_address, cargo_type, weight_kg, "
    "vehicle_type_requested, status, total_price, driver_payout, platform_commission, "
    "delivered_at, "
    "companies(company_name), "
    "drivers(profiles(full_name)), "
    "vehicles(plate_number)"
)


def _flatten_row(row: dict) -> dict:
    row = dict(row)
    company = row.pop("companies", None) or {}
    driver = row.pop("drivers", None) or {}
    vehicle = row.pop("vehicles", None) or {}
    driver_profile = driver.get("profiles") or {}

    row["company_name"] = company.get("company_name") or "-"
    row["driver_name"] = driver_profile.get("full_name") or "-"
    row["plate_number"] = vehicle.get("plate_number") or "-"
    row["delivered_at"] = row.get("delivered_at") or "-"
    return row


def export_orders(
    *,
    current_user: CurrentUser,
    date_from: str | None,
    date_to: str | None,
    order_status: OrderStatus | None,
    company_id: str | None,
) -> tuple[bytes, str]:
    supabase = get_supabase()
    query = supabase.table("orders").select(EXPORT_SELECT_COLUMNS)

    if current_user.role == UserRole.company:
        own_company_id = get_company_by_owner(current_user.id).id
        query = query.eq("company_id", own_company_id)
    elif current_user.role == UserRole.admin:
        if company_id:
            query = query.eq("company_id", company_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya company dan admin yang bisa mengekspor rekap order.",
        )

    if order_status:
        query = query.eq("status", order_status.value)
    if date_from:
        query = query.gte("created_at", date_from)
    if date_to:
        query = query.lte("created_at", date_to)

    result = query.order("created_at", desc=True).execute()
    rows = [_flatten_row(row) for row in result.data]

    buffer = build_orders_report(rows)
    filename = f"rekap-order-{date_from or 'semua'}_{date_to or 'semua'}.xlsx"
    return buffer.getvalue(), filename
