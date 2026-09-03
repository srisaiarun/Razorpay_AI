from pydantic import BaseModel, ConfigDict, EmailStr, Field


# =========================================================
# REGISTRATION
# =========================================================

class RegisterRequest(BaseModel):
    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    full_name: str = Field(
        min_length=2,
        max_length=200,
    )

    role: str


# =========================================================
# LOGIN
# =========================================================

class LoginRequest(BaseModel):
    email: EmailStr

    password: str = Field(
        min_length=1,
        max_length=128,
    )


# =========================================================
# USER RESPONSE
# =========================================================

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    status: str
    customer_id: int | None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# AUTH RESPONSE
# =========================================================

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse