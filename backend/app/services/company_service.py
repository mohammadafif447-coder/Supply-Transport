from fastapi import HTTPException, status
from postgrest.exceptions import APIError

from app.core.errors import db_error_to_http
from app.db.supabase_client import get_supabase
from app.models.company import CompanyCreate, CompanyResponse


def create_company(*, owner_profile_id: str, payload: CompanyCreate) -> CompanyResponse:
    supabase = get_supabase()

    existing = (
        supabase.table("companies")
        .select("id")
        .eq("owner_profile_id", owner_profile_id)
        .execute()
    )
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profil perusahaan sudah terdaftar untuk akun ini.",
        )

    try:
        result = (
            supabase.table("companies")
            .insert(
                {
                    "owner_profile_id": owner_profile_id,
                    "company_name": payload.company_name,
                    "company_address": payload.company_address,
                    "tax_id": payload.tax_id,
                    "billing_email": payload.billing_email,
                }
            )
            .execute()
        )
    except APIError as exc:
        raise db_error_to_http(exc) from exc

    return CompanyResponse(**result.data[0])


def get_company_by_owner(owner_profile_id: str) -> CompanyResponse:
    supabase = get_supabase()
    result = (
        supabase.table("companies")
        .select("*")
        .eq("owner_profile_id", owner_profile_id)
        .maybe_single()
        .execute()
    )
    if not result or not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil perusahaan belum dibuat. Lengkapi onboarding lewat POST /companies.",
        )
    return CompanyResponse(**result.data)
