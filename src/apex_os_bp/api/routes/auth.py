"""Authentication routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from apex_os_bp.api.middleware.auth import AuthMiddleware
from apex_os_bp.api.models import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from apex_os_bp.security.auth import Authenticator

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_auth_middleware(request: Request) -> AuthMiddleware:
    """Get the auth middleware instance."""
    instance = AuthMiddleware.get_instance()
    if instance is None:
        raise RuntimeError("AuthMiddleware not initialized")
    return instance


def get_authenticator(request: Request) -> Authenticator:
    """Get the authenticator from the app state."""
    return request.app.state.authenticator


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    body: LoginRequest,
    authenticator: Authenticator = Depends(get_authenticator),
    auth_middleware: AuthMiddleware = Depends(get_auth_middleware),
) -> TokenResponse:
    """Authenticate and receive a token."""
    user = authenticator.authenticate(body.username, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = auth_middleware.create_token(user.id)
    return TokenResponse(access_token=token, token_type="bearer", expires_in=3600)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    authenticator: Authenticator = Depends(get_authenticator),
) -> UserResponse:
    """Register a new user."""
    # Check if username already exists
    for user in authenticator._users.values():
        if user.username == body.username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists",
            )
    user = authenticator.register(body.username, body.email, body.password)
    return UserResponse(id=user.id, username=user.username, email=user.email, roles=user.roles)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    auth_middleware: AuthMiddleware = Depends(get_auth_middleware),
) -> dict:
    """Logout and revoke the current token."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        auth_middleware.revoke_token(token)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    request: Request,
    authenticator: Authenticator = Depends(get_authenticator),
) -> UserResponse:
    """Get the current authenticated user."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    user = authenticator._users.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserResponse(id=user.id, username=user.username, email=user.email, roles=user.roles)
