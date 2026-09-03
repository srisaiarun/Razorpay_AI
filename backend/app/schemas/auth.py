from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class CustomerLoginRequest(BaseModel):
    customer_access_id: str = Field(min_length=1, max_length=50)


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    status: str
    customer_id: int | None

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse