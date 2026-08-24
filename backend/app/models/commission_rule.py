from pydantic import BaseModel, Field

from app.models.enums import VehicleType


class CommissionRuleResponse(BaseModel):
    id: str
    vehicle_type: VehicleType
    commission_percent: float
    base_price: float
    price_per_km: float
    updated_at: str


class CommissionRuleUpdate(BaseModel):
    commission_percent: float = Field(ge=0, le=100)
    base_price: float = Field(ge=0)
    price_per_km: float = Field(ge=0)
