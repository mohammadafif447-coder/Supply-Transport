from enum import Enum

from pydantic import BaseModel


class UserRole(str, Enum):
    company = "company"
    admin = "admin"
    driver = "driver"


class CurrentUser(BaseModel):
    id: str
    email: str | None = None
    role: UserRole
    full_name: str
