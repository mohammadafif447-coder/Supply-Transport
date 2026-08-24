from fastapi import HTTPException, UploadFile, status
from postgrest.exceptions import APIError

from app.core.errors import db_error_to_http
from app.db.supabase_client import get_supabase
from app.models.enums import DriverStatus, OrderStatus
from app.models.order import (
    DriverOrderListItem,
    OrderAssign,
    OrderCancel,
    OrderCreate,
    OrderListItem,
    OrderResponse,
    OrderStatusUpdate,
    TrackingEventResponse,
)
from app.models.user import CurrentUser, UserRole
from app.services.pricing_service import calculate_order_pricing
from app.services.storage_service import POD_PHOTOS_BUCKET, get_signed_url, upload_document

ORDER_SELECT_COLUMNS = (
    "id, company_id, created_by_profile_id, driver_id, vehicle_id, status, "
    "pickup_address, pickup_lat, pickup_lng, dropoff_address, dropoff_lat, dropoff_lng, "
    "cargo_type, weight_kg, volume_m3, vehicle_type_requested, scheduled_pickup_at, notes, "
    "pod_required, pod_photo_url, total_price, driver_payout, platform_commission, "
    "commission_override_reason, cancelled_reason, delivered_at, created_at, updated_at"
)


def _hydrate_order(row: dict) -> OrderResponse:
    row = dict(row)
    row["pod_photo_url"] = get_signed_url(POD_PHOTOS_BUCKET, row.get("pod_photo_url"))
    return OrderResponse(**row)


def _get_company_id_for_owner(owner_profile_id: str) -> str:
    supabase = get_supabase()
    company = (
        supabase.table("companies")
        .select("id")
        .eq("owner_profile_id", owner_profile_id)
        .maybe_single()
        .execute()
    )
    if not company or not company.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil perusahaan belum dibuat. Lengkapi onboarding lewat POST /companies.",
        )
    return company.data["id"]


def _get_driver_id_for_profile(profile_id: str) -> str:
    supabase = get_supabase()
    driver = (
        supabase.table("drivers")
        .select("id")
        .eq("profile_id", profile_id)
        .maybe_single()
        .execute()
    )
    if not driver or not driver.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil driver belum dibuat. Lengkapi onboarding lewat POST /drivers.",
        )
    return driver.data["id"]


def _fetch_order_or_404(order_id: str) -> dict:
    supabase = get_supabase()
    result = (
        supabase.table("orders")
        .select(ORDER_SELECT_COLUMNS)
        .eq("id", order_id)
        .maybe_single()
        .execute()
    )
    if not result or not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order tidak ditemukan.")
    return result.data


def _assert_can_view_order(order: dict, current_user: CurrentUser) -> None:
    if current_user.role == UserRole.admin:
        return
    if current_user.role == UserRole.company:
        company_id = _get_company_id_for_owner(current_user.id)
        if order["company_id"] == company_id:
            return
    if current_user.role == UserRole.driver:
        driver_id = _get_driver_id_for_profile(current_user.id)
        if order["driver_id"] == driver_id:
            return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Anda tidak berhak mengakses order ini.")


def create_order(*, current_user: CurrentUser, payload: OrderCreate) -> OrderResponse:
    company_id = _get_company_id_for_owner(current_user.id)
    pricing = calculate_order_pricing(
        vehicle_type=payload.vehicle_type_requested,
        pickup_lat=payload.pickup_lat,
        pickup_lng=payload.pickup_lng,
        dropoff_lat=payload.dropoff_lat,
        dropoff_lng=payload.dropoff_lng,
    )

    supabase = get_supabase()
    try:
        result = (
            supabase.table("orders")
            .insert(
                {
                    "company_id": company_id,
                    "created_by_profile_id": current_user.id,
                    "status": OrderStatus.pending.value,
                    "pickup_address": payload.pickup_address,
                    "pickup_lat": payload.pickup_lat,
                    "pickup_lng": payload.pickup_lng,
                    "dropoff_address": payload.dropoff_address,
                    "dropoff_lat": payload.dropoff_lat,
                    "dropoff_lng": payload.dropoff_lng,
                    "cargo_type": payload.cargo_type.value,
                    "weight_kg": payload.weight_kg,
                    "volume_m3": payload.volume_m3,
                    "vehicle_type_requested": payload.vehicle_type_requested.value,
                    "scheduled_pickup_at": payload.scheduled_pickup_at.isoformat(),
                    "notes": payload.notes,
                    "pod_required": payload.pod_required,
                    **pricing,
                }
            )
            .execute()
        )
    except APIError as exc:
        raise db_error_to_http(exc) from exc

    return _hydrate_order(result.data[0])


def list_orders(
    *,
    current_user: CurrentUser,
    order_status: OrderStatus | None,
    date_from: str | None,
    date_to: str | None,
    driver_id: str | None,
) -> list[OrderListItem]:
    supabase = get_supabase()
    query = supabase.table("orders").select(
        "id, status, pickup_address, dropoff_address, cargo_type, "
        "vehicle_type_requested, scheduled_pickup_at, total_price, created_at, company_id, driver_id"
    )

    if current_user.role == UserRole.company:
        company_id = _get_company_id_for_owner(current_user.id)
        query = query.eq("company_id", company_id)
    elif current_user.role == UserRole.admin:
        if driver_id:
            query = query.eq("driver_id", driver_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Gunakan GET /orders/driver/me untuk melihat order Anda.",
        )

    if order_status:
        query = query.eq("status", order_status.value)
    if date_from:
        query = query.gte("created_at", date_from)
    if date_to:
        query = query.lte("created_at", date_to)

    result = query.order("created_at", desc=True).execute()
    return [OrderListItem(**row) for row in result.data]


def list_orders_for_driver(*, driver_profile_id: str) -> list[DriverOrderListItem]:
    driver_id = _get_driver_id_for_profile(driver_profile_id)
    supabase = get_supabase()
    result = (
        supabase.table("orders")
        .select(
            "id, status, pickup_address, dropoff_address, cargo_type, "
            "vehicle_type_requested, scheduled_pickup_at, total_price, driver_payout, created_at"
        )
        .eq("driver_id", driver_id)
        .order("created_at", desc=True)
        .execute()
    )
    return [DriverOrderListItem(**row) for row in result.data]


def get_order(*, order_id: str, current_user: CurrentUser) -> OrderResponse:
    order = _fetch_order_or_404(order_id)
    _assert_can_view_order(order, current_user)
    return _hydrate_order(order)


def get_tracking(*, order_id: str, current_user: CurrentUser) -> list[TrackingEventResponse]:
    order = _fetch_order_or_404(order_id)
    _assert_can_view_order(order, current_user)

    supabase = get_supabase()
    result = (
        supabase.table("order_tracking_events")
        .select("*")
        .eq("order_id", order_id)
        .order("created_at")
        .execute()
    )
    return [TrackingEventResponse(**row) for row in result.data]


def assign_order(*, order_id: str, payload: OrderAssign, admin_profile_id: str) -> OrderResponse:
    supabase = get_supabase()

    try:
        driver = (
            supabase.table("drivers")
            .select("id, status, is_available")
            .eq("id", payload.driver_id)
            .maybe_single()
            .execute()
        )
    except APIError:
        driver = None
    if not driver or not driver.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver tidak ditemukan.")
    if driver.data["status"] != DriverStatus.approved.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Driver belum berstatus 'approved'."
        )
    if not driver.data["is_available"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Driver sedang tidak tersedia (masih ada tugas aktif lain).",
        )

    try:
        vehicle = (
            supabase.table("vehicles")
            .select("id, driver_id")
            .eq("id", payload.vehicle_id)
            .maybe_single()
            .execute()
        )
    except APIError:
        vehicle = None
    if not vehicle or not vehicle.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kendaraan tidak ditemukan.")
    if vehicle.data["driver_id"] != payload.driver_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kendaraan tersebut bukan milik driver yang dipilih.",
        )

    try:
        result = supabase.rpc(
            "transition_order_status",
            {
                "p_order_id": order_id,
                "p_new_status": OrderStatus.assigned.value,
                "p_actor_profile_id": admin_profile_id,
                "p_driver_id": payload.driver_id,
                "p_vehicle_id": payload.vehicle_id,
            },
        ).execute()
    except APIError as exc:
        raise db_error_to_http(exc) from exc

    return _hydrate_order(result.data)


def update_status(*, order_id: str, payload: OrderStatusUpdate, driver_profile_id: str) -> OrderResponse:
    driver_id = _get_driver_id_for_profile(driver_profile_id)
    order = _fetch_order_or_404(order_id)
    if order["driver_id"] != driver_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Order ini bukan tugas Anda."
        )

    supabase = get_supabase()
    try:
        result = supabase.rpc(
            "transition_order_status",
            {
                "p_order_id": order_id,
                "p_new_status": payload.status.value,
                "p_actor_profile_id": driver_profile_id,
                "p_note": payload.note,
                "p_lat": payload.lat,
                "p_lng": payload.lng,
            },
        ).execute()
    except APIError as exc:
        raise db_error_to_http(exc) from exc

    return _hydrate_order(result.data)


async def upload_pod(*, order_id: str, driver_profile_id: str, photo: UploadFile) -> OrderResponse:
    driver_id = _get_driver_id_for_profile(driver_profile_id)
    order = _fetch_order_or_404(order_id)
    if order["driver_id"] != driver_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Order ini bukan tugas Anda."
        )
    if order["status"] != OrderStatus.in_transit.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bukti serah terima hanya bisa diunggah saat order berstatus 'in_transit'.",
        )

    pod_path = await upload_document(
        bucket=POD_PHOTOS_BUCKET, folder=order_id, filename_prefix="pod", file=photo
    )

    supabase = get_supabase()
    try:
        result = (
            supabase.table("orders")
            .update({"pod_photo_url": pod_path})
            .eq("id", order_id)
            .execute()
        )
    except APIError as exc:
        raise db_error_to_http(exc) from exc

    return _hydrate_order(result.data[0])


def cancel_order(*, order_id: str, payload: OrderCancel, current_user: CurrentUser) -> OrderResponse:
    order = _fetch_order_or_404(order_id)

    if current_user.role == UserRole.company:
        company_id = _get_company_id_for_owner(current_user.id)
        if order["company_id"] != company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Order ini bukan milik perusahaan Anda."
            )
    elif current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tidak diizinkan.")

    supabase = get_supabase()
    try:
        result = supabase.rpc(
            "transition_order_status",
            {
                "p_order_id": order_id,
                "p_new_status": OrderStatus.cancelled.value,
                "p_actor_profile_id": current_user.id,
                "p_cancelled_reason": payload.reason,
            },
        ).execute()
    except APIError as exc:
        raise db_error_to_http(exc) from exc

    return _hydrate_order(result.data)
