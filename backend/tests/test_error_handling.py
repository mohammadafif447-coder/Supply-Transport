import httpx
import pytest
from fastapi import HTTPException

from app.core import security
from app.db.supabase_client import _RetryTransport
from app.main import http_exception_handler, unhandled_exception_handler


class _FakeRequest:
    method = "GET"
    url = httpx.URL("http://testserver/api/v1/orders")


async def test_http_exception_handler_returns_standard_error_shape():
    exc = HTTPException(status_code=403, detail="Anda tidak berhak mengakses order ini.")
    response = await http_exception_handler(_FakeRequest(), exc)

    assert response.status_code == 403
    body = response.body.decode()
    assert '"message":"Anda tidak berhak mengakses order ini."' in body
    assert '"status_code":403' in body


async def test_unhandled_exception_handler_hides_internal_details():
    exc = RuntimeError("leaked secret connection string: postgres://...")
    response = await unhandled_exception_handler(_FakeRequest(), exc)

    assert response.status_code == 500
    body = response.body.decode()
    assert "leaked secret" not in body
    assert "postgres://" not in body
    assert "RuntimeError" not in body
    assert '"message":"Terjadi kesalahan internal pada server."' in body
    assert '"status_code":500' in body


class _CountingTransport(httpx.BaseTransport):
    def __init__(self, failures_before_success: int, exc_type=httpx.RemoteProtocolError):
        self.failures_before_success = failures_before_success
        self.exc_type = exc_type
        self.call_count = 0

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.call_count += 1
        if self.call_count <= self.failures_before_success:
            raise self.exc_type("Server disconnected")
        return httpx.Response(200, request=request)


def _request(method: str) -> httpx.Request:
    return httpx.Request(method, "http://example.test/rest/v1/orders")


def test_retry_transport_retries_get_on_transient_error_and_succeeds(monkeypatch):
    monkeypatch.setattr("app.db.supabase_client.time.sleep", lambda _seconds: None)
    inner = _CountingTransport(failures_before_success=2)
    transport = _RetryTransport(inner)

    response = transport.handle_request(_request("GET"))

    assert response.status_code == 200
    assert inner.call_count == 3  # 2 failures + 1 success


def test_retry_transport_gives_up_after_max_retries(monkeypatch):
    monkeypatch.setattr("app.db.supabase_client.time.sleep", lambda _seconds: None)
    inner = _CountingTransport(failures_before_success=10)
    transport = _RetryTransport(inner)

    with pytest.raises(httpx.RemoteProtocolError):
        transport.handle_request(_request("GET"))

    assert inner.call_count == 3  # 1 initial attempt + 2 retries


def test_retry_transport_does_not_retry_non_idempotent_methods():
    inner = _CountingTransport(failures_before_success=10)
    transport = _RetryTransport(inner)

    with pytest.raises(httpx.RemoteProtocolError):
        transport.handle_request(_request("POST"))

    assert inner.call_count == 1  # no retry attempted for POST


def test_fetch_jwks_retries_transient_failure_then_succeeds(monkeypatch):
    monkeypatch.setattr(security.time, "sleep", lambda _seconds: None)
    calls = {"n": 0}

    class _FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"keys": ["fake"]}

    def fake_get(url, timeout):
        calls["n"] += 1
        if calls["n"] < 2:
            raise httpx.RemoteProtocolError("Server disconnected")
        return _FakeResponse()

    monkeypatch.setattr(security.httpx, "get", fake_get)

    result = security._fetch_jwks()

    assert result == {"keys": ["fake"]}
    assert calls["n"] == 2


def test_fetch_jwks_gives_up_with_503_after_exhausting_retries(monkeypatch):
    monkeypatch.setattr(security.time, "sleep", lambda _seconds: None)

    def fake_get(url, timeout):
        raise httpx.RemoteProtocolError("Server disconnected")

    monkeypatch.setattr(security.httpx, "get", fake_get)

    with pytest.raises(HTTPException) as exc_info:
        security._fetch_jwks()

    assert exc_info.value.status_code == 503
