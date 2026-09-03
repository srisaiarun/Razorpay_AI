from __future__ import annotations

from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from pydantic import BaseModel
from sqlalchemy import select
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
    LoginRequest,
    UserResponse,
)


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)


# =========================================================
# JWT BEARER AUTHENTICATION
# =========================================================

security = HTTPBearer()


# =========================================================
# DATABASE DEPENDENCY
# =========================================================

def get_db():
    """
    Provide a SQLAlchemy database session for one request.
    """

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# =========================================================
# LOGIN
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
    Authenticate an existing user.

    There is intentionally NO public registration endpoint.

    Users must already exist in the users table.
    """

    email = request.email.strip().lower()

    # -----------------------------------------------------
    # Find existing user
    # -----------------------------------------------------

    user = db.scalar(
        select(User).where(
            User.email == email
        )
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    # -----------------------------------------------------
    # Verify password
    # -----------------------------------------------------

    if not verify_password(
        request.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    # -----------------------------------------------------
    # Check account status
    # -----------------------------------------------------

    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not active.",
        )

    # -----------------------------------------------------
    # Update last login
    # -----------------------------------------------------

    user.last_login_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    # -----------------------------------------------------
    # Create JWT
    # -----------------------------------------------------

    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


# =========================================================
# CURRENT USER
# =========================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        security
    ),
    db: Session = Depends(get_db),
) -> User:
    """
    Resolve the authenticated user from the JWT bearer token.
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token.",
        headers={
            "WWW-Authenticate": "Bearer"
        },
    )

    token = credentials.credentials

    try:
        payload = decode_access_token(token)

        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

        user_id_int = int(user_id)

    except HTTPException:
        raise

    except Exception as exc:
        raise credentials_exception from exc

    # -----------------------------------------------------
    # Find user
    # -----------------------------------------------------

    user = db.get(
        User,
        user_id_int,
    )

    if user is None:
        raise credentials_exception

    # -----------------------------------------------------
    # Check account status
    # -----------------------------------------------------

    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not active.",
        )

    return user


# =========================================================
# CUSTOMER AUTHORIZATION
# =========================================================

def require_customer_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Require the authenticated user to be a CUSTOMER.
    """

    if current_user.role != "CUSTOMER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer access required.",
        )

    return current_user


# =========================================================
# MANAGEMENT AUTHORIZATION
# =========================================================

def require_management_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Require the authenticated user to be MANAGEMENT.

    Additional defense-in-depth:
    management accounts must use the approved
    @klh.edu.in domain.
    """

    if current_user.role != "MANAGEMENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Management access required.",
        )

    if not current_user.email.lower().endswith(
        "@klh.edu.in"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Management access is restricted.",
        )

    return current_user


# =========================================================
# CURRENT USER ENDPOINT
# =========================================================

@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    """
    Return the currently authenticated user.
    """

    return UserResponse.model_validate(
        current_user
    )