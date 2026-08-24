import io
import itertools
import os
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

REPO_ROOT = Path(__file__).resolve().parents[2]

_unique_counter = itertools.count(1)


def _unique_digits(length: int) -> str:
    """A digit string unique within this test run — for columns with a
    unique constraint (phone_number lives on `profiles`, ktp_number and
    plate_number have their own unique constraints) that a plain timestamp
    isn't safe enough for when fixtures run faster than the clock ticks.
    """
    n = next(_unique_counter)
    return str(n).zfill(length)[-length:]


def _parse_env_file(path: Path) -> dict:
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def _anon_key() -> str:
    frontend_env = _parse_env_file(REPO_ROOT / "frontend" / ".env.local")
    key = frontend_env.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    if not key:
        pytest.skip("frontend/.env.local with NEXT_PUBLIC_SUPABASE_ANON_KEY not found")
    return key


def require_integration() -> None:
    if os.environ.get("RUN_INTEGRATION_TESTS") != "1":
        pytest.skip(
            "integration test skipped — set RUN_INTEGRATION_TESTS=1 to run against "
            "the live Supabase project (see backend/.env)"
        )


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


class LiveAuthHelper:
    """Creates/deletes real Supabase Auth users and mints password-grant JWTs.

    Used only by integration tests (see require_integration) — talks directly
    to the same live Supabase project the app itself uses.
    """

    PASSWORD = "TestFase9!2026"

    def __init__(self):
        settings = get_settings()
        self.supabase_url = settings.supabase_url.rstrip("/")
        self.service_key = settings.supabase_service_role_key
        self.anon_key = _anon_key()
        self._created_user_ids: list[str] = []
        self._admin_client = httpx.Client(
            base_url=f"{self.supabase_url}/auth/v1",
            headers={
                "apikey": self.service_key,
                "Authorization": f"Bearer {self.service_key}",
            },
            timeout=30,
        )

    def create_user(self, email_prefix: str, role: str) -> str:
        email = f"st-fase9-{email_prefix}-{int(time.time() * 1000)}@mailinator.com"
        resp = self._admin_client.post(
            "/admin/users",
            json={
                "email": email,
                "password": self.PASSWORD,
                "email_confirm": True,
                "user_metadata": {"role": role, "full_name": email_prefix},
            },
        )
        resp.raise_for_status()
        user_id = resp.json()["id"]
        self._created_user_ids.append(user_id)
        return email

    def sign_in(self, email: str) -> str:
        resp = httpx.post(
            f"{self.supabase_url}/auth/v1/token?grant_type=password",
            headers={"apikey": self.anon_key, "Content-Type": "application/json"},
            json={"email": email, "password": self.PASSWORD},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def rest_headers(self, user_token: str) -> dict:
        """Headers for calling Supabase's REST API directly as this user (anon key + their JWT) — used to probe RLS without going through our FastAPI backend at all."""
        return {"apikey": self.anon_key, "Authorization": f"Bearer {user_token}"}

    def cleanup(self) -> None:
        for user_id in self._created_user_ids:
            try:
                self._admin_client.delete(f"/admin/users/{user_id}")
            except httpx.HTTPError:
                pass


class LiveDataHelper:
    """Deletes rows created by integration tests via the service-role REST API."""

    def __init__(self):
        settings = get_settings()
        self._rest = httpx.Client(
            base_url=f"{settings.supabase_url.rstrip('/')}/rest/v1",
            headers={
                "apikey": settings.supabase_service_role_key,
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        self._order_ids: list[str] = []
        self._driver_ids: list[str] = []
        self._company_ids: list[str] = []

    def track_order(self, order_id: str) -> None:
        self._order_ids.append(order_id)

    def track_driver(self, driver_id: str) -> None:
        self._driver_ids.append(driver_id)

    def track_company(self, company_id: str) -> None:
        self._company_ids.append(company_id)

    def cleanup(self) -> None:
        for order_id in self._order_ids:
            self._rest.delete("/orders", params={"id": f"eq.{order_id}"})
        for driver_id in self._driver_ids:
            self._rest.delete("/drivers", params={"id": f"eq.{driver_id}"})
        for company_id in self._company_ids:
            self._rest.delete("/companies", params={"id": f"eq.{company_id}"})


@pytest.fixture(scope="session")
def live_stack(client):
    """Seeds 2 companies, 1 admin, 1 driver+vehicle against the real live
    Supabase project via the actual FastAPI endpoints, tears everything down
    afterward. Session-scoped since setup does several real network calls.
    """
    require_integration()

    auth = LiveAuthHelper()
    data = LiveDataHelper()

    def _auth_header(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    company_a_email = auth.create_user("company-a", "company")
    company_b_email = auth.create_user("company-b", "company")
    admin_email = auth.create_user("admin", "admin")
    driver_email = auth.create_user("driver", "driver")

    company_a_token = auth.sign_in(company_a_email)
    company_b_token = auth.sign_in(company_b_email)
    admin_token = auth.sign_in(admin_email)
    driver_token = auth.sign_in(driver_email)

    resp = client.post(
        "/api/v1/companies",
        headers=_auth_header(company_a_token),
        json={"company_name": "PT Fase9 A", "company_address": "Jl. Fase9 A No. 1, Jakarta"},
    )
    assert resp.status_code == 201, resp.text
    company_a_id = resp.json()["id"]
    data.track_company(company_a_id)

    resp = client.post(
        "/api/v1/companies",
        headers=_auth_header(company_b_token),
        json={"company_name": "PT Fase9 B", "company_address": "Jl. Fase9 B No. 2, Jakarta"},
    )
    assert resp.status_code == 201, resp.text
    company_b_id = resp.json()["id"]
    data.track_company(company_b_id)

    fake_photo = ("photo.jpg", io.BytesIO(b"\xff\xd8\xff\xe0fakejpeg"), "image/jpeg")
    resp = client.post(
        "/api/v1/drivers",
        headers=_auth_header(driver_token),
        data={
            "full_name": "Driver Fase9",
            "phone_number": f"08{_unique_digits(9)}",
            "ktp_number": f"31712345{_unique_digits(8)}",
            "sim_number": "SIM-FASE9-001",
            "bank_name": "BCA",
            "bank_account_number": "1234567890",
            "vehicle_plate_number": f"B{_unique_digits(4)}F9",
            "vehicle_type": "pickup",
            "vehicle_max_weight_kg": "1000",
        },
        files={"ktp_photo": fake_photo, "sim_photo": fake_photo, "stnk_photo": fake_photo},
    )
    assert resp.status_code == 201, resp.text
    driver_id = resp.json()["id"]
    data.track_driver(driver_id)

    resp = client.patch(
        f"/api/v1/drivers/{driver_id}/review",
        headers=_auth_header(admin_token),
        json={"status": "approved"},
    )
    assert resp.status_code == 200, resp.text

    resp = client.get(
        "/api/v1/vehicles/available",
        headers=_auth_header(admin_token),
        params={"vehicle_type": "pickup"},
    )
    assert resp.status_code == 200, resp.text
    vehicle_id = resp.json()[0]["id"]

    stack = {
        "client": client,
        "auth": auth,
        "data": data,
        "company_a_id": company_a_id,
        "company_b_id": company_b_id,
        "company_a_token": company_a_token,
        "company_b_token": company_b_token,
        "admin_token": admin_token,
        "driver_token": driver_token,
        "driver_id": driver_id,
        "vehicle_id": vehicle_id,
    }

    yield stack

    data.cleanup()
    auth.cleanup()


@pytest.fixture
def fresh_approved_driver(live_stack):
    """A brand-new approved driver+vehicle, independent per test.

    Tests that assign/advance an order make the driver briefly unavailable
    (business rule: one active order per driver) — reusing the same driver
    across tests would couple their ordering. A fresh driver per test avoids
    that entirely.
    """
    auth = live_stack["auth"]
    client = live_stack["client"]
    data = live_stack["data"]

    driver_email = auth.create_user("driver-fresh", "driver")
    driver_token = auth.sign_in(driver_email)

    fake_photo = ("photo.jpg", io.BytesIO(b"\xff\xd8\xff\xe0fakejpeg"), "image/jpeg")
    resp = client.post(
        "/api/v1/drivers",
        headers={"Authorization": f"Bearer {driver_token}"},
        data={
            "full_name": "Driver Fase9 Fresh",
            "phone_number": f"08{_unique_digits(9)}",
            "ktp_number": f"31712345{_unique_digits(8)}",
            "sim_number": "SIM-FASE9-FRESH",
            "bank_name": "BCA",
            "bank_account_number": "1234567891",
            "vehicle_plate_number": f"B{_unique_digits(4)}FR",
            "vehicle_type": "pickup",
            "vehicle_max_weight_kg": "1000",
        },
        files={"ktp_photo": fake_photo, "sim_photo": fake_photo, "stnk_photo": fake_photo},
    )
    assert resp.status_code == 201, resp.text
    driver_id = resp.json()["id"]
    data.track_driver(driver_id)

    resp = client.patch(
        f"/api/v1/drivers/{driver_id}/review",
        headers={"Authorization": f"Bearer {live_stack['admin_token']}"},
        json={"status": "approved"},
    )
    assert resp.status_code == 200, resp.text

    resp = client.get(
        "/api/v1/vehicles/available",
        headers={"Authorization": f"Bearer {live_stack['admin_token']}"},
        params={"vehicle_type": "pickup"},
    )
    assert resp.status_code == 200, resp.text
    vehicle_id = next(v["id"] for v in resp.json() if v["driver_id"] == driver_id)

    return {"driver_id": driver_id, "vehicle_id": vehicle_id, "driver_token": driver_token}


@pytest.fixture
def make_order(live_stack):
    """Creates a fresh pending order for company A and tracks it for cleanup."""

    def _make(**overrides):
        payload = {
            "pickup_address": "Jl. Gudang Fase9 No. 1, Jakarta Utara",
            "dropoff_address": "Jl. Tujuan Fase9 No. 2, Jakarta Selatan",
            "cargo_type": "general",
            "weight_kg": 100,
            "vehicle_type_requested": "pickup",
            "scheduled_pickup_at": _future_iso(hours=2),
            "pod_required": True,
        }
        payload.update(overrides)
        resp = live_stack["client"].post(
            "/api/v1/orders",
            headers={"Authorization": f"Bearer {live_stack['company_a_token']}"},
            json=payload,
        )
        assert resp.status_code == 201, resp.text
        order = resp.json()
        live_stack["data"].track_order(order["id"])
        return order

    return _make


def _future_iso(*, hours: int) -> str:
    from datetime import datetime, timedelta, timezone

    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
