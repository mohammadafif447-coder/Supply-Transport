from fastapi import APIRouter, Depends, status

from app.core.security import require_role
from app.models.company import CompanyCreate, CompanyResponse
from app.models.user import CurrentUser, UserRole
from app.services import company_service

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(
    payload: CompanyCreate,
    current_user: CurrentUser = Depends(require_role(UserRole.company)),
) -> CompanyResponse:
    return company_service.create_company(owner_profile_id=current_user.id, payload=payload)


@router.get("/me", response_model=CompanyResponse)
def read_my_company(
    current_user: CurrentUser = Depends(require_role(UserRole.company)),
) -> CompanyResponse:
    return company_service.get_company_by_owner(current_user.id)
