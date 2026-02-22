from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from backend.app.models.user import User, UserCreate, UserInDB
from backend.app.services.auth import (
    get_current_active_user,
    fake_users_db,
    get_password_hash,
    save_users
)
import uuid

router = APIRouter()

def check_admin(user: User):
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )

@router.get("/users", response_model=List[User])
async def read_users(
    current_user: User = Depends(get_current_active_user)
):
    check_admin(current_user)
    return list(fake_users_db.values())

@router.post("/users", response_model=User)
async def create_user(
    user_in: UserCreate,
    current_user: User = Depends(get_current_active_user)
):
    check_admin(current_user)
    if user_in.email in fake_users_db:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = UserInDB(
        email=user_in.email,
        role=user_in.role,
        allowed_namespaces=user_in.allowed_namespaces,
        theme_pref=user_in.theme_pref,
        id=str(uuid.uuid4()),
        hashed_password=get_password_hash(user_in.password)
    )
    fake_users_db[user.email] = user
    save_users()
    return user

@router.patch("/users/{user_id}", response_model=User)
async def update_user(
    user_id: str,
    user_update: dict,
    current_user: User = Depends(get_current_active_user)
):
    check_admin(current_user)
    # Find user by ID
    target_user = None
    target_email = None
    for email, user in fake_users_db.items():
        if user.id == user_id:
            target_user = user
            target_email = email
            break

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update fields
    if "allowed_namespaces" in user_update:
        target_user.allowed_namespaces = user_update["allowed_namespaces"]
    if "role" in user_update:
        target_user.role = user_update["role"]
    if "theme_pref" in user_update:
        target_user.theme_pref = user_update["theme_pref"]

    fake_users_db[target_email] = target_user
    save_users()
    return target_user

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_active_user)
):
    check_admin(current_user)
    target_email = None
    for email, user in fake_users_db.items():
        if user.id == user_id:
            target_email = email
            break

    if not target_email:
        raise HTTPException(status_code=404, detail="User not found")

    if target_email == current_user.email:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    del fake_users_db[target_email]
    save_users()
    return {"message": "User deleted"}
