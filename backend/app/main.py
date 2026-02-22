"""Namespace Observatory — FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import admin, auth, kubernetes
from app.services.k8s import init_k8s

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Initializing database …")
    init_db()
    logger.info("Initializing Kubernetes client …")
    init_k8s()
    logger.info("Namespace Observatory is ready.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Namespace Observatory",
    description="Read-only Kubernetes namespace monitoring API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(kubernetes.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
