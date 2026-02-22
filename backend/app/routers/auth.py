"""Authentication endpoints: login, logout, me, theme."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.dependencies import get_current_user
from app.models.schemas import LoginRequest, ThemeUpdateRequest, TokenResponse, UserOut
from app.services.auth import (
    add_audit_log,
    create_access_token,
    get_user_by_email,
    update_theme,
    verify_password,
)

router = APIRouter(tags=["auth"])


@router.post("/api/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, response: Response) -> TokenResponse:
    user = get_user_by_email(body.email)
    if user is None or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = create_access_token(user["id"])
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set True in production behind TLS
        max_age=8 * 60 * 60,
        path="/",
    )
    add_audit_log(user["id"], "login", f"email={body.email}")
    return TokenResponse(message="Login successful")


@router.post("/api/auth/logout", response_model=TokenResponse)
def logout(
    response: Response,
    user: dict = Depends(get_current_user),
) -> TokenResponse:
    response.delete_cookie("session_token", path="/")
    add_audit_log(user["id"], "logout")
    return TokenResponse(message="Logged out")


@router.get("/api/me", response_model=UserOut)
def me(user: dict = Depends(get_current_user)) -> UserOut:
    return UserOut(
        id=user["id"],
        email=user["email"],
        role=user["role"],
        allowed_namespaces=user["allowed_namespaces"],
        theme_pref=user["theme_pref"],
    )


@router.patch("/api/me/theme", response_model=UserOut)
def update_my_theme(
    body: ThemeUpdateRequest,
    user: dict = Depends(get_current_user),
) -> UserOut:
    if body.theme_pref not in ("minimal", "neo-brutal"):
        raise HTTPException(status_code=400, detail="Invalid theme. Use 'minimal' or 'neo-brutal'.")
    update_theme(user["id"], body.theme_pref)
    user["theme_pref"] = body.theme_pref
    return UserOut(
        id=user["id"],
        email=user["email"],
        role=user["role"],
        allowed_namespaces=user["allowed_namespaces"],
        theme_pref=user["theme_pref"],
    )
