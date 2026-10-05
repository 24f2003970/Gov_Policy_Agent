import re
import unicodedata
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator


def normalize_username(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().lower()


class Registration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr = Field(max_length=254)
    username: str
    password: SecretStr
    preferred_language: Literal["en", "hi", "hinglish"] = "en"

    @field_validator("email", mode="before")
    @classmethod
    def email_normalize(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("username")
    @classmethod
    def username_check(cls, value):
        value = normalize_username(value)
        if not re.fullmatch(r"[a-z0-9_]{3,32}", value):
            raise ValueError("Username: 3–32 letters, digits or underscores")
        return value

    @field_validator("password")
    @classmethod
    def password_check(cls, value):
        if not 12 <= len(value.get_secret_value()) <= 128:
            raise ValueError("Password must contain 12–128 characters")
        return value


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr = Field(max_length=254)
    password: SecretStr

    @field_validator("email", mode="before")
    @classmethod
    def email_normalize(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def password_check(cls, value):
        if not 1 <= len(value.get_secret_value()) <= 128:
            raise ValueError("Invalid password length")
        return value


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    username: str
    role: Literal["user", "admin"]
    preferred_language: str
    active: bool
    created_at: datetime
    updated_at: datetime


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preferred_language: Literal["en", "hi", "hinglish"]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
