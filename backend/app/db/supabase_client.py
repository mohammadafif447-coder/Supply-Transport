import time
from functools import lru_cache

import httpx
from supabase import Client, ClientOptions, create_client

from app.core.config import get_settings

# Observed transient failures (see docs memory: httpx.RemoteProtocolError /
# "Server disconnected") happen mid-connection against Supabase's PostgREST,
# not on our own logic. Only GET/HEAD/OPTIONS are retried automatically —
# retrying a write blindly risks double-submitting it if the request actually
# reached the server and only the response was lost in transit.
_RETRYABLE_METHODS = {"GET", "HEAD", "OPTIONS"}
_MAX_RETRIES = 2
_BACKOFF_SECONDS = 0.3


class _RetryTransport(httpx.BaseTransport):
    def __init__(self, transport: httpx.BaseTransport) -> None:
        self._transport = transport

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if request.method not in _RETRYABLE_METHODS:
            return self._transport.handle_request(request)

        attempt = 0
        while True:
            try:
                return self._transport.handle_request(request)
            except (httpx.RemoteProtocolError, httpx.ConnectError, httpx.ReadError) as exc:
                attempt += 1
                if attempt > _MAX_RETRIES:
                    raise
                time.sleep(_BACKOFF_SECONDS * attempt)

    def close(self) -> None:
        self._transport.close()


def _build_retrying_httpx_client() -> httpx.Client:
    return httpx.Client(transport=_RetryTransport(httpx.HTTPTransport()))


@lru_cache
def get_supabase() -> Client:
    """Client dengan service_role key — bypass RLS.

    HANYA dipakai di backend, setelah request divalidasi & di-scope
    secara manual di layer service (lihat app/services/*). Jangan pernah
    expose service_role key ke frontend.
    """
    settings = get_settings()
    options = ClientOptions(httpx_client=_build_retrying_httpx_client())
    return create_client(settings.supabase_url, settings.supabase_service_role_key, options)
