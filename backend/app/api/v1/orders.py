from fastapi import APIRouter, Depends, File, UploadFile, status

from app.core.security import get_current_user, require_role
from app.models.enums import OrderStatus
from app.models.order import (
    DriverOrderListItem,
    OrderAssign,
    OrderCancel,
    OrderCreate,
    OrderListItem,
    OrderResponse,
    OrderStatusUpdate,
    TrackingEventResponse,
)
from app.models.user import CurrentUser, UserRole
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    current_user: CurrentUser = Depends(require_role(UserRole.company)),
) -> OrderResponse:
    return order_service.create_order(current_user=current_user, payload=payload)


@router.get("", response_model=list[OrderListItem])
def list_orders(
    status_filter: OrderStatus | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    driver_id: str | None = None,
    current_user: CurrentUser = Depends(require_role(UserRole.company, UserRole.admin)),
) -> list[OrderListItem]:
    return order_service.list_orders(
        current_user=current_user,
        order_status=status_filter,
        date_from=date_from,
        date_to=date_to,
        driver_id=driver_id,
    )


@router.get("/driver/me", response_model=list[DriverOrderListItem])
def list_my_orders_as_driver(
    current_user: CurrentUser = Depends(require_role(UserRole.driver)),
) -> list[DriverOrderListItem]:
    return order_service.list_orders_for_driver(driver_profile_id=current_user.id)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> OrderResponse:
    return order_service.get_order(order_id=order_id, current_user=current_user)


@router.get("/{order_id}/tracking", response_model=list[TrackingEventResponse])
def get_order_tracking(
    order_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> list[TrackingEventResponse]:
    return order_service.get_tracking(order_id=order_id, current_user=current_user)


@router.patch("/{order_id}/assign", response_model=OrderResponse)
def assign_order(
    order_id: str,
    payload: OrderAssign,
    current_user: CurrentUser = Depends(require_role(UserRole.admin)),
) -> OrderResponse:
    return order_service.assign_order(
        order_id=order_id, payload=payload, admin_profile_id=current_user.id
    )


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_status(
    order_id: str,
    payload: OrderStatusUpdate,
    current_user: CurrentUser = Depends(require_role(UserRole.driver)),
) -> OrderResponse:
    return order_service.update_status(
        order_id=order_id, payload=payload, driver_profile_id=current_user.id
    )


@router.post("/{order_id}/pod", response_model=OrderResponse)
async def upload_pod(
    order_id: str,
    photo: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_role(UserRole.driver)),
) -> OrderResponse:
    return await order_service.upload_pod(
        order_id=order_id, driver_profile_id=current_user.id, photo=photo
    )


@router.patch("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: str,
    payload: OrderCancel,
    current_user: CurrentUser = Depends(require_role(UserRole.company, UserRole.admin)),
) -> OrderResponse:
    return order_service.cancel_order(order_id=order_id, payload=payload, current_user=current_user)
