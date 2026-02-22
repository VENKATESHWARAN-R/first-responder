from fastapi import Cookie, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.db import get_session
from app.core.security import decode_token
from app.models.db import User, UserRole
from app.services.rbac import can_access_namespace


def get_current_user(session: Session = Depends(get_session), access_token: str | None = Cookie(default=None)) -> User:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authenticated')
    payload = decode_token(access_token)
    if not payload or 'sub' not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid session')
    user = session.exec(select(User).where(User.email == payload['sub'])).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid user')
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Admin role required')
    return user


def require_namespace(namespace: str, user: User = Depends(get_current_user)) -> None:
    if not can_access_namespace(user, namespace):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Insufficient RBAC for namespace')
