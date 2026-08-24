"""Integration tests for the order status state machine (Fase 9.1).

The real enforcement lives in the Postgres function
`transition_order_status` (supabase/migrations/0002_...sql), so these run
against the live Supabase project end-to-end through the actual FastAPI
endpoints — the same thing manually verified during Fase 3/6/7/8, now
codified as a regression suite. Skipped unless RUN_INTEGRATION_TESTS=1.
"""

import io

import pytest

pytestmark = pytest.mark.integration


def _assign(live_stack, order_id, driver):
    return live_stack["client"].patch(
        f"/api/v1/orders/{order_id}/assign",
        headers={"Authorization": f"Bearer {live_stack['admin_token']}"},
        json={"driver_id": driver["driver_id"], "vehicle_id": driver["vehicle_id"]},
    )


def _set_status(live_stack, order_id, driver, status):
    return live_stack["client"].patch(
        f"/api/v1/orders/{order_id}/status",
        headers={"Authorization": f"Bearer {driver['driver_token']}"},
        json={"status": status},
    )


def _upload_pod(live_stack, order_id, driver):
    return live_stack["client"].post(
        f"/api/v1/orders/{order_id}/pod",
        headers={"Authorization": f"Bearer {driver['driver_token']}"},
        files={"photo": ("pod.jpg", io.BytesIO(b"\xff\xd8\xff\xe0fakejpeg"), "image/jpeg")},
    )


def test_full_valid_lifecycle_pending_to_delivered(live_stack, make_order, fresh_approved_driver):
    order = make_order()

    resp = _assign(live_stack, order["id"], fresh_approved_driver)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "assigned"

    resp = _set_status(live_stack, order["id"], fresh_approved_driver, "picked_up")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "picked_up"

    resp = _set_status(live_stack, order["id"], fresh_approved_driver, "in_transit")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "in_transit"

    resp = _upload_pod(live_stack, order["id"], fresh_approved_driver)
    assert resp.status_code == 200, resp.text
    assert resp.json()["pod_photo_url"]

    resp = _set_status(live_stack, order["id"], fresh_approved_driver, "delivered")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "delivered"
    assert body["delivered_at"] is not None


def test_rejects_skipping_picked_up_straight_to_in_transit(
    live_stack, make_order, fresh_approved_driver
):
    order = make_order()
    assert _assign(live_stack, order["id"], fresh_approved_driver).status_code == 200

    resp = _set_status(live_stack, order["id"], fresh_approved_driver, "in_transit")

    assert resp.status_code == 400
    assert "Transisi status tidak diizinkan" in resp.json()["error"]["message"]


def test_rejects_skipping_straight_to_delivered_from_assigned(
    live_stack, make_order, fresh_approved_driver
):
    order = make_order()
    assert _assign(live_stack, order["id"], fresh_approved_driver).status_code == 200

    resp = _set_status(live_stack, order["id"], fresh_approved_driver, "delivered")

    assert resp.status_code == 400
    assert "Transisi status tidak diizinkan" in resp.json()["error"]["message"]


def test_rejects_backward_transition(live_stack, make_order, fresh_approved_driver):
    order = make_order()
    assert _assign(live_stack, order["id"], fresh_approved_driver).status_code == 200
    assert _set_status(live_stack, order["id"], fresh_approved_driver, "picked_up").status_code == 200
    assert (
        _set_status(live_stack, order["id"], fresh_approved_driver, "in_transit").status_code == 200
    )

    # in_transit -> picked_up is not a valid status for this endpoint at all
    # (only picked_up/in_transit/delivered are accepted), so this is rejected
    # by Pydantic before ever reaching the DB state machine.
    resp = live_stack["client"].patch(
        f"/api/v1/orders/{order['id']}/status",
        headers={"Authorization": f"Bearer {fresh_approved_driver['driver_token']}"},
        json={"status": "assigned"},
    )
    assert resp.status_code == 422


def test_rejects_delivered_without_pod_when_pod_required(
    live_stack, make_order, fresh_approved_driver
):
    order = make_order(pod_required=True)
    assert _assign(live_stack, order["id"], fresh_approved_driver).status_code == 200
    assert _set_status(live_stack, order["id"], fresh_approved_driver, "picked_up").status_code == 200
    assert (
        _set_status(live_stack, order["id"], fresh_approved_driver, "in_transit").status_code == 200
    )

    resp = _set_status(live_stack, order["id"], fresh_approved_driver, "delivered")

    assert resp.status_code == 400
    assert "bukti serah terima" in resp.json()["error"]["message"]


def test_allows_delivered_without_pod_when_not_required(
    live_stack, make_order, fresh_approved_driver
):
    order = make_order(pod_required=False)
    assert _assign(live_stack, order["id"], fresh_approved_driver).status_code == 200
    assert _set_status(live_stack, order["id"], fresh_approved_driver, "picked_up").status_code == 200
    assert (
        _set_status(live_stack, order["id"], fresh_approved_driver, "in_transit").status_code == 200
    )

    resp = _set_status(live_stack, order["id"], fresh_approved_driver, "delivered")

    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "delivered"


def test_cancel_allowed_while_pending(live_stack, make_order):
    order = make_order()

    resp = live_stack["client"].patch(
        f"/api/v1/orders/{order['id']}/cancel",
        headers={"Authorization": f"Bearer {live_stack['company_a_token']}"},
        json={"reason": "Perubahan rencana pengiriman"},
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "cancelled"


def test_cancel_allowed_while_assigned(live_stack, make_order, fresh_approved_driver):
    order = make_order()
    assert _assign(live_stack, order["id"], fresh_approved_driver).status_code == 200

    resp = live_stack["client"].patch(
        f"/api/v1/orders/{order['id']}/cancel",
        headers={"Authorization": f"Bearer {live_stack['company_a_token']}"},
        json={"reason": "Driver berhalangan"},
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "cancelled"


def test_cancel_rejected_after_picked_up(live_stack, make_order, fresh_approved_driver):
    order = make_order()
    assert _assign(live_stack, order["id"], fresh_approved_driver).status_code == 200
    assert _set_status(live_stack, order["id"], fresh_approved_driver, "picked_up").status_code == 200

    resp = live_stack["client"].patch(
        f"/api/v1/orders/{order['id']}/cancel",
        headers={"Authorization": f"Bearer {live_stack['company_a_token']}"},
        json={"reason": "Coba batalkan setelah dijemput"},
    )

    assert resp.status_code == 400
    assert "Transisi status tidak diizinkan" in resp.json()["error"]["message"]

    # clean up: drive it to a terminal state so the driver becomes available
    # again (not strictly needed since fresh_approved_driver is per-test, but
    # keeps the seeded order's final state consistent for inspection).
    _set_status(live_stack, order["id"], fresh_approved_driver, "in_transit")
    _upload_pod(live_stack, order["id"], fresh_approved_driver)
    _set_status(live_stack, order["id"], fresh_approved_driver, "delivered")


def test_no_further_transition_allowed_once_delivered(
    live_stack, make_order, fresh_approved_driver
):
    order = make_order(pod_required=False)
    assert _assign(live_stack, order["id"], fresh_approved_driver).status_code == 200
    assert _set_status(live_stack, order["id"], fresh_approved_driver, "picked_up").status_code == 200
    assert (
        _set_status(live_stack, order["id"], fresh_approved_driver, "in_transit").status_code == 200
    )
    assert _set_status(live_stack, order["id"], fresh_approved_driver, "delivered").status_code == 200

    resp = live_stack["client"].patch(
        f"/api/v1/orders/{order['id']}/cancel",
        headers={"Authorization": f"Bearer {live_stack['company_a_token']}"},
        json={"reason": "Coba batalkan order yang sudah selesai"},
    )

    assert resp.status_code == 400
    assert "Transisi status tidak diizinkan" in resp.json()["error"]["message"]


def test_assign_rejects_unavailable_driver(live_stack, make_order, fresh_approved_driver):
    first_order = make_order()
    assert _assign(live_stack, first_order["id"], fresh_approved_driver).status_code == 200

    second_order = make_order()
    resp = _assign(live_stack, second_order["id"], fresh_approved_driver)

    assert resp.status_code == 400
    assert "tidak tersedia" in resp.json()["error"]["message"]
