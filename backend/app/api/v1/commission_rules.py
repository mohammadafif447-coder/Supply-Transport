from fastapi import APIRouter, Depends

from app.core.security import require_role
from app.models.commission_rule import CommissionRuleResponse, CommissionRuleUpdate
from app.models.enums import VehicleType
from app.models.user import CurrentUser, UserRole
from app.services import commission_rule_service

router = APIRouter(prefix="/commission-rules", tags=["commission-rules"])


@router.get("", response_model=list[CommissionRuleResponse])
def list_commission_rules(
    current_user: CurrentUser = Depends(require_role(UserRole.admin)),
) -> list[CommissionRuleResponse]:
    return commission_rule_service.list_commission_rules()


@router.put("/{vehicle_type}", response_model=CommissionRuleResponse)
def update_commission_rule(
    vehicle_type: VehicleType,
    payload: CommissionRuleUpdate,
    current_user: CurrentUser = Depends(require_role(UserRole.admin)),
) -> CommissionRuleResponse:
    return commission_rule_service.update_commission_rule(
        vehicle_type=vehicle_type, payload=payload
    )
