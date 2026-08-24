from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field, field_validator

from app.models.enums import CargoType, OrderStatus, VehicleType


class OrderCreate(BaseModel):
    pickup_address: str = Field(min_length=10, max_length=255)
    pickup_lat: float | None = None
    pickup_lng: float | None = None
    dropoff_address: str = Field(min_length=10, max_length=255)
    dropoff_lat: float | None = None
    dropoff_lng: float | None = None
    cargo_type: CargoType
    weight_kg: float = Field(gt=0, le=30000)
    volume_m3: float | None = Field(default=None, ge=0)
    vehicle_type_requested: VehicleType
    scheduled_pickup_at: datetime
    notes: str | None = Field(default=None, max_length=500)
    pod_required: bool = True

    @field_validator("scheduled_pickup_at")
    @classmethod
    def must_be_at_least_one_hour_ahead(cls, value: datetime) -> datetime:
        reference = datetime.now(timezone.utc)
        compare_value = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if compare_value < reference + timedelta(hours=1):
            raise ValueError("scheduled_pickup_at harus minimal 1 jam dari sekarang.")
        return value


class OrderResponse(BaseModel):
    id: str
    company_id: str
    created_by_profile_id: str
    driver_id: str | None
    vehicle_id: str | None
    status: OrderStatus
    pickup_address: str
    pickup_lat: float | None
    pickup_lng: float | None
    dropoff_address: str
    dropoff_lat: float | None
    dropoff_lng: float | None
    cargo_type: CargoType
    weight_kg: float
    volume_m3: float | None
    vehicle_type_requested: VehicleType
    scheduled_pickup_at: str
    notes: str | None
    pod_required: bool
    pod_photo_url: str | None
    total_price: float
    driver_payout: float
    platform_commission: float
    commission_override_reason: str | None
    cancelled_reason: str | None
    delivered_at: str | None
    created_at: str
    updated_at: str


class OrderListItem(BaseModel):
    id: str
    status: OrderStatus
    pickup_address: str
    dropoff_address: str
    cargo_type: CargoType
    vehicle_type_requested: VehicleType
    scheduled_pickup_at: str
    total_price: float
    created_at: str


class DriverOrderListItem(OrderListItem):
    driver_payout: float


class OrderAssign(BaseModel):
    driver_id: str
    vehicle_id: str


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    note: str | None = Field(default=None, max_length=255)
    lat: float | None = None
    lng: float | None = None

    @field_validator("status")
    @classmethod
    def only_driver_advanceable_statuses(cls, value: OrderStatus) -> OrderStatus:
        allowed = {OrderStatus.picked_up, OrderStatus.in_transit, OrderStatus.delivered}
        if value not in allowed:
            raise ValueError(
                f"Status '{value.value}' tidak bisa diset lewat endpoint ini. "
                f"Gunakan salah satu dari: {', '.join(s.value for s in allowed)}."
            )
        return value


class OrderCancel(BaseModel):
    reason: str = Field(min_length=3, max_length=255)


class TrackingEventResponse(BaseModel):
    id: str
    order_id: str
    status: OrderStatus
    note: str | None
    lat: float | None
    lng: float | None
    created_by_profile_id: str
    created_at: str
