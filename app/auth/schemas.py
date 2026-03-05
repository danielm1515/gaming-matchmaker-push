from pydantic import BaseModel, EmailStr, field_validator
import re


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    country_code: str | None = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]{3,30}$", v):
            raise ValueError("Username must be 3-30 chars: letters, numbers, underscores only")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 128:
            raise ValueError("Password must be at most 128 characters")
        return v

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, v: str | None) -> str | None:
        if v and not re.match(r"^[A-Z]{2}$", v.upper()):
            raise ValueError("Country code must be 2 uppercase letters (ISO 3166-1 alpha-2)")
        return v.upper() if v else None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
