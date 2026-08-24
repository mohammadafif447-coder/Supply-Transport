from pydantic import BaseModel, EmailStr, Field


class CompanyCreate(BaseModel):
    company_name: str = Field(min_length=2, max_length=150)
    company_address: str = Field(min_length=10, max_length=255)
    tax_id: str | None = Field(default=None, max_length=30)
    billing_email: EmailStr | None = None


class CompanyResponse(BaseModel):
    id: str
    owner_profile_id: str
    company_name: str
    company_address: str
    tax_id: str | None
    billing_email: str | None
    created_at: str
