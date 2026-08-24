from fastapi import HTTPException, UploadFile, status
from postgrest.exceptions import APIError

from app.core.errors import db_error_to_http
from app.db.supabase_client import get_supabase
from app.models.driver import DriverCreate, DriverListItem, DriverResponse, DriverReviewUpdate
from app.models.enums import DriverStatus, VehicleType
from app.models.vehicle import AvailableVehicleResponse, VehicleCreate, VehicleResponse
from app.services.storage_service import (
    DRIVER_DOCUMENTS_BUCKET,
    get_signed_url,
    upload_document,
)


def _hydrate_driver(row: dict, vehicles: list[dict] | None = None) -> DriverResponse:
    row = dict(row)
    row["ktp_photo_url"] = get_signed_url(DRIVER_DOCUMENTS_BUCKET, row.get("ktp_photo_url"))
    row["sim_photo_url"] = get_signed_url(DRIVER_DOCUMENTS_BUCKET, row.get("sim_photo_url"))
    vehicle_models = []
    for v in vehicles or []:
        v = dict(v)
        v["stnk_photo_url"] = get_signed_url(DRIVER_DOCUMENTS_BUCKET, v.get("stnk_photo_url"))
        vehicle_models.append(VehicleResponse(**v))
    return DriverResponse(**row, vehicles=vehicle_models)


async def create_driver_with_vehicle(
    *,
    profile_id: str,
    payload: DriverCreate,
    ktp_photo: UploadFile,
    sim_photo: UploadFile,
    stnk_photo: UploadFile,
) -> DriverResponse:
    supabase = get_supabase()

    existing = supabase.table("drivers").select("id").eq("profile_id", profile_id).execute()
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profil driver sudah terdaftar untuk akun ini.",
        )

    ktp_path = await upload_document(
        bucket=DRIVER_DOCUMENTS_BUCKET, folder=profile_id, filename_prefix="ktp", file=ktp_photo
    )
    sim_path = await upload_document(
        bucket=DRIVER_DOCUMENTS_BUCKET, folder=profile_id, filename_prefix="sim", file=sim_photo
    )
    stnk_path = await upload_document(
        bucket=DRIVER_DOCUMENTS_BUCKET, folder=profile_id, filename_prefix="stnk", file=stnk_photo
    )

    try:
        driver_result = (
            supabase.table("drivers")
            .insert(
                {
                    "profile_id": profile_id,
                    "ktp_number": payload.ktp_number,
                    "ktp_photo_url": ktp_path,
                    "sim_number": payload.sim_number,
                    "sim_photo_url": sim_path,
                    "bank_name": payload.bank_name,
                    "bank_account_number": payload.bank_account_number,
                }
            )
            .execute()
        )
    except APIError as exc:
        raise db_error_to_http(exc) from exc

    driver_row = driver_result.data[0]

    try:
        supabase.table("profiles").update(
            {"full_name": payload.full_name, "phone_number": payload.phone_number}
        ).eq("id", profile_id).execute()
    except APIError as exc:
        supabase.table("drivers").delete().eq("id", driver_row["id"]).execute()
        raise db_error_to_http(exc) from exc

    try:
        vehicle_result = (
            supabase.table("vehicles")
            .insert(
                {
                    "driver_id": driver_row["id"],
                    "plate_number": payload.vehicle.plate_number,
                    "vehicle_type": payload.vehicle.vehicle_type.value,
                    "max_weight_kg": payload.vehicle.max_weight_kg,
                    "stnk_photo_url": stnk_path,
                }
            )
            .execute()
        )
    except APIError as exc:
        # Rollback manual: driver tanpa kendaraan tidak valid — hapus driver yang baru dibuat.
        supabase.table("drivers").delete().eq("id", driver_row["id"]).execute()
        raise db_error_to_http(exc) from exc

    driver_row["full_name"] = payload.full_name
    driver_row["phone_number"] = payload.phone_number
    return _hydrate_driver(driver_row, vehicle_result.data)


def get_driver_by_profile(profile_id: str) -> DriverResponse:
    supabase = get_supabase()
    driver_result = (
        supabase.table("drivers")
        .select("*, profiles!inner(full_name, phone_number)")
        .eq("profile_id", profile_id)
        .maybe_single()
        .execute()
    )
    if not driver_result or not driver_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil driver belum dibuat. Lengkapi onboarding lewat POST /drivers.",
        )

    row = driver_result.data
    profile = row.pop("profiles")
    row["full_name"] = profile["full_name"]
    row["phone_number"] = profile["phone_number"]

    vehicles = (
        supabase.table("vehicles").select("*").eq("driver_id", row["id"]).execute()
    )
    return _hydrate_driver(row, vehicles.data)


def update_my_availability(*, profile_id: str, is_available: bool) -> DriverResponse:
    supabase = get_supabase()
    driver = (
        supabase.table("drivers")
        .select("id, status")
        .eq("profile_id", profile_id)
        .maybe_single()
        .execute()
    )
    if not driver or not driver.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil driver belum dibuat. Lengkapi onboarding lewat POST /drivers.",
        )
    if driver.data["status"] != DriverStatus.approved.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hanya driver berstatus 'approved' yang bisa mengubah ketersediaan.",
        )

    if is_available:
        active_order = (
            supabase.table("orders")
            .select("id")
            .eq("driver_id", driver.data["id"])
            .in_("status", ["assigned", "picked_up", "in_transit"])
            .maybe_single()
            .execute()
        )
        if active_order and active_order.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tidak bisa mengubah ke tersedia saat masih ada tugas aktif.",
            )

    supabase.table("drivers").update({"is_available": is_available}).eq(
        "id", driver.data["id"]
    ).execute()
    return get_driver_by_profile(profile_id)


def list_drivers(
    *, driver_status: DriverStatus | None, is_available: bool | None
) -> list[DriverListItem]:
    supabase = get_supabase()
    query = supabase.table("drivers").select("*, profiles!inner(full_name, phone_number)")
    if driver_status:
        query = query.eq("status", driver_status.value)
    if is_available is not None:
        query = query.eq("is_available", is_available)

    result = query.order("created_at", desc=True).execute()

    items = []
    for row in result.data:
        profile = row["profiles"]
        items.append(
            DriverListItem(
                id=row["id"],
                full_name=profile["full_name"],
                phone_number=profile["phone_number"],
                status=row["status"],
                is_available=row["is_available"],
                created_at=row["created_at"],
            )
        )
    return items


def review_driver(*, driver_id: str, payload: DriverReviewUpdate) -> DriverResponse:
    payload.validate_business_rules()
    supabase = get_supabase()

    existing = supabase.table("drivers").select("id").eq("id", driver_id).maybe_single().execute()
    if not existing or not existing.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver tidak ditemukan.")

    update_payload = {
        "status": payload.status.value,
        "rejection_reason": payload.rejection_reason if payload.status == DriverStatus.rejected else None,
    }
    supabase.table("drivers").update(update_payload).eq("id", driver_id).execute()

    driver_result = (
        supabase.table("drivers")
        .select("*, profiles!inner(full_name, phone_number)")
        .eq("id", driver_id)
        .single()
        .execute()
    )
    row = driver_result.data
    profile = row.pop("profiles")
    row["full_name"] = profile["full_name"]
    row["phone_number"] = profile["phone_number"]

    vehicles = supabase.table("vehicles").select("*").eq("driver_id", driver_id).execute()
    return _hydrate_driver(row, vehicles.data)


async def add_vehicle(
    *, driver_id: str, requesting_profile_id: str, payload: VehicleCreate, stnk_photo: UploadFile
) -> VehicleResponse:
    supabase = get_supabase()

    driver = (
        supabase.table("drivers")
        .select("id, profile_id")
        .eq("id", driver_id)
        .maybe_single()
        .execute()
    )
    if not driver or not driver.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver tidak ditemukan.")
    if driver.data["profile_id"] != requesting_profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tidak bisa menambah kendaraan untuk driver lain.",
        )

    stnk_path = await upload_document(
        bucket=DRIVER_DOCUMENTS_BUCKET,
        folder=requesting_profile_id,
        filename_prefix="stnk",
        file=stnk_photo,
    )

    try:
        result = (
            supabase.table("vehicles")
            .insert(
                {
                    "driver_id": driver_id,
                    "plate_number": payload.plate_number,
                    "vehicle_type": payload.vehicle_type.value,
                    "max_weight_kg": payload.max_weight_kg,
                    "stnk_photo_url": stnk_path,
                }
            )
            .execute()
        )
    except APIError as exc:
        raise db_error_to_http(exc) from exc

    row = result.data[0]
    row["stnk_photo_url"] = get_signed_url(DRIVER_DOCUMENTS_BUCKET, row.get("stnk_photo_url"))
    return VehicleResponse(**row)


def list_available_vehicles(vehicle_type: VehicleType | None) -> list[AvailableVehicleResponse]:
    supabase = get_supabase()
    query = (
        supabase.table("vehicles")
        .select(
            "*, drivers!inner(status, is_available, profiles!inner(full_name, phone_number))"
        )
        .eq("drivers.status", DriverStatus.approved.value)
        .eq("drivers.is_available", True)
    )
    if vehicle_type:
        query = query.eq("vehicle_type", vehicle_type.value)

    result = query.execute()

    vehicles = []
    for row in result.data:
        driver = row.pop("drivers")
        profile = driver["profiles"]
        row["stnk_photo_url"] = get_signed_url(DRIVER_DOCUMENTS_BUCKET, row.get("stnk_photo_url"))
        vehicles.append(
            AvailableVehicleResponse(
                **row,
                driver_full_name=profile["full_name"],
                driver_phone_number=profile.get("phone_number"),
            )
        )
    return vehicles
