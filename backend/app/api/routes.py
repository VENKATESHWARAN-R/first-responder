from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_admin
from app.core.config import settings
from app.core.db import get_session
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.db import User
from app.models.schemas import LoginRequest, UserCreate, UserOut, UserUpdate
from app.services.cache import TTLCache
from app.services.diagnostics import likely_cause
from app.services.k8s import k8s_service
from app.services.rbac import can_access_namespace, filter_namespaces

router = APIRouter(prefix='/api')
logger = logging.getLogger('audit')
cache = TTLCache(settings.cache_ttl_seconds)


def _assert_ns(user: User, namespace: str) -> None:
    if not can_access_namespace(user, namespace):
        raise HTTPException(status_code=403, detail='Insufficient RBAC')


@router.post('/auth/login')
def login(payload: LoginRequest, response: Response, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == payload.email)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        logger.warning('auth.login.failed email=%s', payload.email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials')
    token = create_access_token(user.email)
    response.set_cookie('access_token', token, httponly=True, secure=settings.secure_cookies, samesite='lax')
    logger.info('auth.login.success email=%s', user.email)
    return {'ok': True}


@router.post('/auth/logout')
def logout(response: Response, user: User = Depends(get_current_user)):
    response.delete_cookie('access_token')
    logger.info('auth.logout email=%s', user.email)
    return {'ok': True}


@router.get('/me', response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.get('/namespaces')
def namespaces(user: User = Depends(get_current_user)):
    all_ns = cache.get_or_set('namespaces', k8s_service.list_namespaces)
    allowed = filter_namespaces(user, all_ns)
    return [cache.get_or_set(f'summary:{ns}', lambda ns=ns: k8s_service.namespace_summary(ns)) for ns in allowed]


@router.get('/namespaces/{namespace}/summary')
def namespace_summary(namespace: str, user: User = Depends(get_current_user)):
    _assert_ns(user, namespace)
    logger.info('access.namespace email=%s namespace=%s route=summary', user.email, namespace)
    return cache.get_or_set(f'summary:{namespace}', lambda: k8s_service.namespace_summary(namespace))


@router.get('/namespaces/{namespace}/workloads')
def namespace_workloads(namespace: str, user: User = Depends(get_current_user)):
    _assert_ns(user, namespace)
    return cache.get_or_set(f'workloads:{namespace}', lambda: k8s_service.list_workloads(namespace))


@router.get('/namespaces/{namespace}/pods')
def namespace_pods(namespace: str, user: User = Depends(get_current_user)):
    _assert_ns(user, namespace)
    return cache.get_or_set(f'pods:{namespace}', lambda: k8s_service.list_pods(namespace))


@router.get('/namespaces/{namespace}/events')
def namespace_events(namespace: str, user: User = Depends(get_current_user)):
    _assert_ns(user, namespace)
    return cache.get_or_set(f'events:{namespace}', lambda: k8s_service.list_events(namespace))


@router.get('/namespaces/{namespace}/config')
def namespace_config(namespace: str, user: User = Depends(get_current_user)):
    _assert_ns(user, namespace)
    return cache.get_or_set(f'config:{namespace}', lambda: k8s_service.list_config(namespace))


@router.get('/workloads/{kind}/{namespace}/{name}')
def workload_detail(kind: str, namespace: str, name: str, user: User = Depends(get_current_user)):
    _assert_ns(user, namespace)
    workloads = k8s_service.list_workloads(namespace)
    for item in workloads:
        if item['kind'].lower() == kind.lower() and item['name'] == name:
            pods = k8s_service.list_pods_by_selector(namespace, item.get('selector') or {})
            item['pods'] = pods
            return item
    raise HTTPException(status_code=404, detail='Workload not found')


@router.get('/pods/{namespace}/{name}')
def pod_detail(namespace: str, name: str, user: User = Depends(get_current_user)):
    _assert_ns(user, namespace)
    pod = k8s_service.get_pod(namespace, name)
    pod_events = [e for e in k8s_service.list_events(namespace) if e['obj'] == name]
    pod['events'] = pod_events
    event_signals = [f"{event['reason']} {event['message']}" for event in pod_events]
    pod['likely_cause'] = likely_cause(pod['container_statuses'], event_signals)
    return pod




@router.patch('/me/theme', response_model=UserOut)
def update_theme(payload: UserUpdate, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if payload.theme_pref is None:
        raise HTTPException(status_code=400, detail='theme_pref required')
    user.theme_pref = payload.theme_pref
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@router.get('/admin/users', response_model=list[UserOut])
def list_users(_: User = Depends(require_admin), session: Session = Depends(get_session)):
    return list(session.exec(select(User)).all())


@router.post('/admin/users', response_model=UserOut)
def create_user(payload: UserCreate, _: User = Depends(require_admin), session: Session = Depends(get_session)):
    existing = session.exec(select(User).where(User.email == payload.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail='Email already exists')
    user = User(
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        role=payload.role,
        allowed_namespaces=payload.allowed_namespaces,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.patch('/admin/users/{user_id}', response_model=UserOut)
def patch_user(user_id: int, payload: UserUpdate, _: User = Depends(require_admin), session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    data = payload.model_dump(exclude_none=True)
    for key, value in data.items():
        setattr(user, key, value)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
