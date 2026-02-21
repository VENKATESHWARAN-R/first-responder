"""Admin endpoints for user management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user, require_admin
from app.models.schemas import CreateUserRequest, UpdateUserRequest, UserOut
from app.services.auth import (
    add_audit_log,
    create_user,
    delete_user,
    get_user_by_email,
    list_users,
    update_user,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _admin_guard(user: dict = Depends(get_current_user)) -> dict:
    return require_admin(user)


@router.get("/users", response_model=list[UserOut])
def get_users(admin: dict = Depends(_admin_guard)) -> list[UserOut]:
    users = list_users()
    return [
        UserOut(
            id=u["id"],
            email=u["email"],
            role=u["role"],
            allowed_namespaces=u["allowed_namespaces"],
            theme_pref=u["theme_pref"],
        )
        for u in users
    ]


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_new_user(
    body: CreateUserRequest,
    admin: dict = Depends(_admin_guard),
) -> UserOut:
    existing = get_user_by_email(body.email)
    if existing:
        raise HTTPException(status_code=409, detail="User with this email already exists")
    if body.role not in ("admin", "viewer"):
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'viewer'")
    user = create_user(body.email, body.password, body.role, body.allowed_namespaces)
    add_audit_log(admin["id"], "create_user", f"created user {body.email}")
    return UserOut(
        id=user["id"],
        email=user["email"],
        role=user["role"],
        allowed_namespaces=user["allowed_namespaces"],
        theme_pref=user["theme_pref"],
    )


@router.patch("/users/{user_id}", response_model=UserOut)
def patch_user(
    user_id: int,
    body: UpdateUserRequest,
    admin: dict = Depends(_admin_guard),
) -> UserOut:
    if body.role is not None and body.role not in ("admin", "viewer"):
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'viewer'")
    user = update_user(user_id, body.role, body.allowed_namespaces, body.password)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    add_audit_log(admin["id"], "update_user", f"updated user {user_id}")
    return UserOut(
        id=user["id"],
        email=user["email"],
        role=user["role"],
        allowed_namespaces=user["allowed_namespaces"],
        theme_pref=user["theme_pref"],
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def remove_user(
    user_id: int,
    admin: dict = Depends(_admin_guard),
) -> None:
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    success = delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    add_audit_log(admin["id"], "delete_user", f"deleted user {user_id}")
