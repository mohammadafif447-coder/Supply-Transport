import time

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt
from postgrest.exceptions import APIError as PostgrestAPIError

from app.core.config import get_settings
from app.db.supabase_client import get_supabase
from app.models.user import CurrentUser, UserRole

bearer_scheme = HTTPBearer()

# Cache JWKS in-process; Supabase rotates signing keys rarely and always
# publishes the new key alongside the old one before switching, so a simple
# "refetch once if kid is unknown" strategy (see _get_signing_key) is enough.
_jwks_cache: dict | None = None


def _fetch_jwks() -> dict:
    settings = get_settings()
    # Observed transient httpx.RemoteProtocolError ("Server disconnected")
    # against this endpoint — retry a couple of times before giving up.
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = httpx.get(settings.supabase_jwks_url, timeout=5.0)
            response.raise_for_status()
            return response.json()
        except (httpx.RemoteProtocolError, httpx.ConnectError, httpx.ReadError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(0.3 * (attempt + 1))
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Gagal memverifikasi token: layanan autentikasi sedang tidak dapat dijangkau.",
    ) from last_error


def _get_signing_key(kid: str) -> dict:
    global _jwks_cache

    if _jwks_cache is None:
        _jwks_cache = _fetch_jwks()

    for key in _jwks_cache.get("keys", []):
        if key.get("kid") == kid:
            return key

    # kid tidak ditemukan di cache — mungkin key baru saja dirotasi, refetch sekali.
    _jwks_cache = _fetch_jwks()
    for key in _jwks_cache.get("keys", []):
        if key.get("kid") == kid:
            return key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Signing key token tidak dikenali.",
    )


def _decode_token(token: str) -> dict:
    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        alg = unverified_header.get("alg", "ES256")
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Header token tidak lengkap."
            )

        jwk_dict = _get_signing_key(kid)
        signing_key = jwk.construct(jwk_dict, alg)

        return jwt.decode(
            token,
            signing_key,
            algorithms=[alg],
            audience="authenticated",
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid atau kedaluwarsa.",
        ) from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    payload = _decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Klaim token tidak lengkap.")

    supabase = get_supabase()
    try:
        result = (
            supabase.table("profiles")
            .select("id, role, full_name")
            .eq("id", user_id)
            .single()
            .execute()
        )
        profile = result.data if result else None
    except PostgrestAPIError:
        profile = None
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Profil pengguna belum terdaftar. Lengkapi onboarding terlebih dahulu.",
        )

    return CurrentUser(
        id=profile["id"],
        email=payload.get("email"),
        role=UserRole(profile["role"]),
        full_name=profile["full_name"],
    )


def require_role(*allowed_roles: UserRole):
    """Dependency factory — batasi endpoint hanya untuk role tertentu.

    Contoh: `current_user: CurrentUser = Depends(require_role(UserRole.admin))`
    """

    async def _check(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Aksi ini hanya untuk role: {', '.join(r.value for r in allowed_roles)}.",
            )
        return current_user

    return _check
