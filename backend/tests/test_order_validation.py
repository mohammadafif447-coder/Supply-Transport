from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.models.order import OrderCancel, OrderCreate, OrderStatusUpdate


def _valid_order_kwargs(**overrides) -> dict:
    kwargs = {
        "pickup_address": "Jl. Gudang Utama No. 10, Jakarta",
        "dropoff_address": "Jl. Tujuan Akhir No. 20, Jakarta",
        "cargo_type": "general",
        "weight_kg": 500,
        "vehicle_type_requested": "pickup",
        "scheduled_pickup_at": datetime.now(timezone.utc) + timedelta(hours=2),
    }
    kwargs.update(overrides)
    return kwargs


def test_order_create_accepts_valid_payload():
    order = OrderCreate(**_valid_order_kwargs())
    assert order.pod_required is True
    assert order.volume_m3 is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"pickup_address": "short"},
        {"pickup_address": "x" * 256},
        {"dropoff_address": "short"},
        {"weight_kg": 0},
        {"weight_kg": -1},
        {"weight_kg": 30001},
        {"volume_m3": -1},
        {"notes": "x" * 501},
        {"cargo_type": "not_a_cargo_type"},
        {"vehicle_type_requested": "not_a_vehicle_type"},
    ],
)
def test_order_create_rejects_invalid_fields(overrides):
    with pytest.raises(ValidationError):
        OrderCreate(**_valid_order_kwargs(**overrides))


def test_order_create_rejects_scheduled_pickup_less_than_one_hour_ahead():
    with pytest.raises(ValidationError):
        OrderCreate(
            **_valid_order_kwargs(
                scheduled_pickup_at=datetime.now(timezone.utc) + timedelta(minutes=30)
            )
        )


def test_order_create_rejects_scheduled_pickup_in_the_past():
    with pytest.raises(ValidationError):
        OrderCreate(
            **_valid_order_kwargs(
                scheduled_pickup_at=datetime.now(timezone.utc) - timedelta(hours=1)
            )
        )


def test_order_create_accepts_scheduled_pickup_exactly_at_boundary():
    # a couple of seconds of margin above the 1-hour minimum to avoid flakiness
    order = OrderCreate(
        **_valid_order_kwargs(
            scheduled_pickup_at=datetime.now(timezone.utc) + timedelta(hours=1, seconds=5)
        )
    )
    assert order.scheduled_pickup_at is not None


@pytest.mark.parametrize("status", ["picked_up", "in_transit", "delivered"])
def test_order_status_update_accepts_driver_advanceable_statuses(status):
    update = OrderStatusUpdate(status=status)
    assert update.status.value == status


@pytest.mark.parametrize("status", ["pending", "assigned", "cancelled"])
def test_order_status_update_rejects_non_driver_advanceable_statuses(status):
    with pytest.raises(ValidationError):
        OrderStatusUpdate(status=status)


def test_order_cancel_requires_reason_with_minimum_length():
    with pytest.raises(ValidationError):
        OrderCancel(reason="ab")

    cancel = OrderCancel(reason="abc")
    assert cancel.reason == "abc"


def test_order_cancel_rejects_reason_over_max_length():
    with pytest.raises(ValidationError):
        OrderCancel(reason="x" * 256)
