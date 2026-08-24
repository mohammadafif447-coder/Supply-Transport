from fastapi import APIRouter, Depends, Response

from app.core.security import require_role
from app.models.enums import OrderStatus
from app.models.user import CurrentUser, UserRole
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/orders/export")
def export_orders(
    date_from: str | None = None,
    date_to: str | None = None,
    status_filter: OrderStatus | None = None,
    company_id: str | None = None,
    current_user: CurrentUser = Depends(require_role(UserRole.company, UserRole.admin)),
) -> Response:
    content, filename = report_service.export_orders(
        current_user=current_user,
        date_from=date_from,
        date_to=date_to,
        order_status=status_filter,
        company_id=company_id,
    )
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
