from pydantic import BaseModel, ConfigDict, EmailStr, Field


# =========================================================
# MANAGEMENT LOGIN
# =========================================================

class LoginRequest(BaseModel):
    email: EmailStr

    password: str = Field(
        min_length=1,
        max_length=128,
    )


# =========================================================
# CUSTOMER LOGIN
# =========================================================

class CustomerLoginRequest(BaseModel):
    """
    Demo/customer portal authentication.

    Customers authenticate using their customer access ID.
    The backend resolves that ID to the linked customer profile.
    """

    customer_id: int = Field(
        ge=1,
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