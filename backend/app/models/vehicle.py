from pydantic import BaseModel, Field

from app.models.enums import VehicleType


class VehicleCreate(BaseModel):
    plate_number: str = Field(min_length=4, max_length=15, pattern=r"^[A-Z0-9 -]+$")
    vehicle_type: VehicleType
    max_weight_kg: float = Field(gt=0, le=50000)


class VehicleResponse(BaseModel):
    id: str
    driver_id: str
    plate_number: str
    vehicle_type: VehicleType
    max_weight_kg: float
    stnk_photo_url: str | None
    created_at: str


class AvailableVehicleResponse(VehicleResponse):
    driver_full_name: str
    driver_phone_number: str | None
