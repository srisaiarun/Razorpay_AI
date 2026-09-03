from __future__ import annotations

from datetime import datetime
from backend.app.models import Customer, User
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.app.core.security import (
    create_access_token,
    decode_access_token,
    verify_password,
)
from backend.app.db.session import SessionLocal
from backend.app.models import User
from backend.app.schemas.auth import (
    AuthResponse,
    CustomerLoginRequest,
    LoginRequest,
    UserResponse,
)


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)

security = HTTPBearer()


# =========================================================
# DATABASE
# =========================================================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# =========================================================
# MANAGEMENT / STANDARD LOGIN
# =========================================================

@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Management/staff authentication using email + password.

    This endpoint remains unchanged for the management portal.
    """

    user = (
        db.query(User)
        .filter(User.email == request.email)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(
        request.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    user.last_login_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=user,
    )


# =========================================================
# CUSTOMER LOGIN
# =========================================================

@router.post(
    "/customer-login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
)
def customer_login(
    request: CustomerLoginRequest,
    db: Session = Depends(get_db),
):
    customer = (
        db.query(Customer)
        .filter(
            Customer.customer_access_id == request.customer_access_id
        )
        .first()
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid customer access ID.",
        )

    user = (
        db.query(User)
        .filter(
            User.customer_id == customer.id,
            User.role == "CUSTOMER",
        )
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Customer account is not configured.",
        )

    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer account is inactive.",
        )

    user.last_login_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=user,
    )


# =========================================================
# CURRENT AUTHENTICATED USER
# =========================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate authentication credentials.",
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )

    token = credentials.credentials

    try:
        payload = decode_access_token(token)

        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

        user_id_int = int(user_id)

    except Exception:
        raise credentials_exception

    user = db.get(User, user_id_int)

    if user is None:
        raise credentials_exception

    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    return user


# =========================================================
# CUSTOMER AUTHORIZATION
# =========================================================

def require_customer_user(
    current_user: User = Depends(get_current_user),
) -> User:

    if current_user.role != "CUSTOMER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer access required.",
        )

    if current_user.customer_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer account is not linked to a customer profile.",
        )

    return current_user


# =========================================================
# MANAGEMENT AUTHORIZATION
# =========================================================

def require_management_user(
    current_user: User = Depends(get_current_user),
) -> User:

    if current_user.role != "MANAGEMENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Management access required.",
        )

    return current_user


# =========================================================
# CURRENT USER
# =========================================================

@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user