from pydantic import BaseModel, Field

from app.models.enums import DriverStatus
from app.models.vehicle import VehicleCreate, VehicleResponse


class DriverCreate(BaseModel):
    full_name: str = Field(min_length=3, max_length=100)
    phone_number: str = Field(pattern=r"^(\+62|62|0)8\d{8,11}$")
    ktp_number: str = Field(pattern=r"^\d{16}$")
    sim_number: str = Field(min_length=5, max_length=30)
    bank_name: str = Field(min_length=2, max_length=100)
    bank_account_number: str = Field(pattern=r"^\d{6,20}$")
    vehicle: VehicleCreate


class DriverResponse(BaseModel):
    id: str
    profile_id: str
    full_name: str
    phone_number: str | None
    ktp_number: str
    ktp_photo_url: str | None
    sim_number: str
    sim_photo_url: str | None
    bank_name: str
    bank_account_number: str
    status: DriverStatus
    is_available: bool
    rejection_reason: str | None
    created_at: str
    vehicles: list[VehicleResponse] = []


class DriverListItem(BaseModel):
    id: str
    full_name: str
    phone_number: str | None
    status: DriverStatus
    is_available: bool
    created_at: str


class DriverAvailabilityUpdate(BaseModel):
    is_available: bool


class DriverReviewUpdate(BaseModel):
    status: DriverStatus
    rejection_reason: str | None = Field(default=None, max_length=255)

    def validate_business_rules(self) -> None:
        if self.status == DriverStatus.rejected and not self.rejection_reason:
            raise ValueError("rejection_reason wajib diisi saat status 'rejected'.")
