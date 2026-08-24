from fastapi import APIRouter, Depends

from app.core.security import require_role
from app.models.enums import VehicleType
from app.models.user import CurrentUser, UserRole
from app.models.vehicle import AvailableVehicleResponse
from app.services import driver_service

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("/available", response_model=list[AvailableVehicleResponse])
def list_available_vehicles(
    vehicle_type: VehicleType | None = None,
    current_user: CurrentUser = Depends(require_role(UserRole.admin)),
) -> list[AvailableVehicleResponse]:
    return driver_service.list_available_vehicles(vehicle_type)
