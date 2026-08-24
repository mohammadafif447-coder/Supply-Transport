from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError

from app.core.errors import validation_error_to_http
from app.core.security import require_role
from app.models.driver import (
    DriverAvailabilityUpdate,
    DriverCreate,
    DriverListItem,
    DriverResponse,
    DriverReviewUpdate,
)
from app.models.enums import DriverStatus, VehicleType
from app.models.user import CurrentUser, UserRole
from app.models.vehicle import VehicleCreate, VehicleResponse
from app.services import driver_service

router = APIRouter(prefix="/drivers", tags=["drivers"])


@router.post("", response_model=DriverResponse, status_code=status.HTTP_201_CREATED)
async def create_driver(
    full_name: str = Form(...),
    phone_number: str = Form(...),
    ktp_number: str = Form(...),
    sim_number: str = Form(...),
    bank_name: str = Form(...),
    bank_account_number: str = Form(...),
    vehicle_plate_number: str = Form(...),
    vehicle_type: VehicleType = Form(...),
    vehicle_max_weight_kg: float = Form(...),
    ktp_photo: UploadFile = File(...),
    sim_photo: UploadFile = File(...),
    stnk_photo: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_role(UserRole.driver)),
) -> DriverResponse:
    try:
        payload = DriverCreate(
            full_name=full_name,
            phone_number=phone_number,
            ktp_number=ktp_number,
            sim_number=sim_number,
            bank_name=bank_name,
            bank_account_number=bank_account_number,
            vehicle=VehicleCreate(
                plate_number=vehicle_plate_number,
                vehicle_type=vehicle_type,
                max_weight_kg=vehicle_max_weight_kg,
            ),
        )
    except ValidationError as exc:
        raise validation_error_to_http(exc) from exc

    return await driver_service.create_driver_with_vehicle(
        profile_id=current_user.id,
        payload=payload,
        ktp_photo=ktp_photo,
        sim_photo=sim_photo,
        stnk_photo=stnk_photo,
    )


@router.get("/me", response_model=DriverResponse)
def read_my_driver_profile(
    current_user: CurrentUser = Depends(require_role(UserRole.driver)),
) -> DriverResponse:
    return driver_service.get_driver_by_profile(current_user.id)


@router.patch("/me/availability", response_model=DriverResponse)
def update_my_availability(
    payload: DriverAvailabilityUpdate,
    current_user: CurrentUser = Depends(require_role(UserRole.driver)),
) -> DriverResponse:
    return driver_service.update_my_availability(
        profile_id=current_user.id, is_available=payload.is_available
    )


@router.get("", response_model=list[DriverListItem])
def list_drivers(
    status_filter: DriverStatus | None = None,
    is_available: bool | None = None,
    current_user: CurrentUser = Depends(require_role(UserRole.admin)),
) -> list[DriverListItem]:
    return driver_service.list_drivers(driver_status=status_filter, is_available=is_available)


@router.patch("/{driver_id}/review", response_model=DriverResponse)
def review_driver(
    driver_id: str,
    payload: DriverReviewUpdate,
    current_user: CurrentUser = Depends(require_role(UserRole.admin)),
) -> DriverResponse:
    try:
        return driver_service.review_driver(driver_id=driver_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.post(
    "/{driver_id}/vehicles", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED
)
async def add_vehicle(
    driver_id: str,
    plate_number: str = Form(...),
    vehicle_type: VehicleType = Form(...),
    max_weight_kg: float = Form(...),
    stnk_photo: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_role(UserRole.driver)),
) -> VehicleResponse:
    try:
        payload = VehicleCreate(
            plate_number=plate_number, vehicle_type=vehicle_type, max_weight_kg=max_weight_kg
        )
    except ValidationError as exc:
        raise validation_error_to_http(exc) from exc

    return await driver_service.add_vehicle(
        driver_id=driver_id,
        requesting_profile_id=current_user.id,
        payload=payload,
        stnk_photo=stnk_photo,
    )
