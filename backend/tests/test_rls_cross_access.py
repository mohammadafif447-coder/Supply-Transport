"""Integration tests for Fase 9.3 — probe RLS directly via a Supabase REST
client (not through our FastAPI backend), to prove the database itself
rejects cross-role/cross-company access as a defense-in-depth layer
independent of the backend's own scoping logic. Skipped unless
RUN_INTEGRATION_TESTS=1.
"""

import httpx
import pytest

from app.core.config import get_settings

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def rest_url():
    return f"{get_settings().supabase_url.rstrip('/')}/rest/v1"


def _get(rest_url, path, token, auth, params=None):
    return httpx.get(f"{rest_url}/{path}", headers=auth.rest_headers(token), params=params, timeout=30)


def _patch(rest_url, path, token, auth, json, params=None):
    return httpx.patch(
        f"{rest_url}/{path}",
        headers={**auth.rest_headers(token), "Content-Type": "application/json"},
        params=params,
        json=json,
        timeout=30,
    )


def test_company_can_read_its_own_order_via_direct_rest(live_stack, make_order, rest_url):
    order = make_order()
    auth = live_stack["auth"]

    resp = _get(
        rest_url,
        "orders",
        live_stack["company_a_token"],
        auth,
        params={"id": f"eq.{order['id']}", "select": "id,status"},
    )

    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["id"] == order["id"]


def test_company_cannot_read_other_companys_order_via_direct_rest(live_stack, make_order, rest_url):
    order = make_order()
    auth = live_stack["auth"]

    resp = _get(
        rest_url,
        "orders",
        live_stack["company_b_token"],
        auth,
        params={"id": f"eq.{order['id']}", "select": "id,status"},
    )

    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_company_cannot_read_other_companys_record_via_direct_rest(live_stack, rest_url):
    auth = live_stack["auth"]

    resp = _get(
        rest_url,
        "companies",
        live_stack["company_a_token"],
        auth,
        params={"id": f"eq.{live_stack['company_b_id']}", "select": "id,company_name"},
    )

    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_unassigned_driver_cannot_read_order_not_theirs_via_direct_rest(
    live_stack, make_order, fresh_approved_driver, rest_url
):
    order = make_order()
    auth = live_stack["auth"]

    resp = _get(
        rest_url,
        "orders",
        fresh_approved_driver["driver_token"],
        auth,
        params={"id": f"eq.{order['id']}", "select": "id,status"},
    )

    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_assigned_driver_can_read_its_own_order_via_direct_rest(
    live_stack, make_order, fresh_approved_driver, rest_url
):
    order = make_order()
    auth = live_stack["auth"]
    resp = live_stack["client"].patch(
        f"/api/v1/orders/{order['id']}/assign",
        headers={"Authorization": f"Bearer {live_stack['admin_token']}"},
        json={
            "driver_id": fresh_approved_driver["driver_id"],
            "vehicle_id": fresh_approved_driver["vehicle_id"],
        },
    )
    assert resp.status_code == 200, resp.text

    resp = _get(
        rest_url,
        "orders",
        fresh_approved_driver["driver_token"],
        auth,
        params={"id": f"eq.{order['id']}", "select": "id,status"},
    )

    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["status"] == "assigned"


def test_admin_can_read_orders_across_companies_via_direct_rest(live_stack, make_order, rest_url):
    order = make_order()
    auth = live_stack["auth"]

    resp = _get(
        rest_url,
        "orders",
        live_stack["admin_token"],
        auth,
        params={"id": f"eq.{order['id']}", "select": "id,status"},
    )

    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["id"] == order["id"]


def test_driver_cannot_bypass_state_machine_with_direct_rest_update(
    live_stack, make_order, fresh_approved_driver, rest_url
):
    order = make_order()
    auth = live_stack["auth"]
    resp = live_stack["client"].patch(
        f"/api/v1/orders/{order['id']}/assign",
        headers={"Authorization": f"Bearer {live_stack['admin_token']}"},
        json={
            "driver_id": fresh_approved_driver["driver_id"],
            "vehicle_id": fresh_approved_driver["vehicle_id"],
        },
    )
    assert resp.status_code == 200, resp.text

    # There is no RLS policy granting drivers UPDATE on `orders` at all —
    # only the SECURITY DEFINER transition_order_status() function (called
    # through our backend) may change status. A direct table PATCH as the
    # driver must not change anything, however PostgREST chooses to respond.
    _patch(
        rest_url,
        "orders",
        fresh_approved_driver["driver_token"],
        auth,
        params={"id": f"eq.{order['id']}"},
        json={"status": "delivered"},
    )

    resp = _get(
        rest_url,
        "orders",
        live_stack["admin_token"],
        auth,
        params={"id": f"eq.{order['id']}", "select": "id,status"},
    )
    assert resp.json()[0]["status"] == "assigned"


def test_company_cannot_modify_other_companys_order_via_direct_rest(
    live_stack, make_order, rest_url
):
    order = make_order()
    auth = live_stack["auth"]

    _patch(
        rest_url,
        "orders",
        live_stack["company_b_token"],
        auth,
        params={"id": f"eq.{order['id']}"},
        json={"pickup_address": "Jl. Diubah Paksa Oleh Company B No. 99"},
    )

    resp = _get(
        rest_url,
        "orders",
        live_stack["company_a_token"],
        auth,
        params={"id": f"eq.{order['id']}", "select": "pickup_address"},
    )
    assert resp.json()[0]["pickup_address"] == order["pickup_address"]
