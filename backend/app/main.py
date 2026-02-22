import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from app.api.routes import router
from app.core.config import settings
from app.core.db import engine, init_db
from app.core.security import get_password_hash
from app.models.db import User, UserRole

logging.basicConfig(level=logging.INFO)

app = FastAPI(title=settings.app_name)
app.include_router(router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.on_event('startup')
def startup() -> None:
    init_db()
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == settings.admin_email)).first()
        if not user:
            session.add(
                User(
                    email=settings.admin_email,
                    password_hash=get_password_hash(settings.admin_password),
                    role=UserRole.admin,
                    allowed_namespaces=[],
                )
            )
            session.commit()


@app.get('/healthz')
def healthz() -> dict[str, str]:
    return {'status': 'ok'}
