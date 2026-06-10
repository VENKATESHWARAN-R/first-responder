"""catalog — product listing service, backed by Redis.

Fails fast at startup if Redis is unreachable: a catalog without its datastore
cannot serve anything meaningful, so it exits and lets Kubernetes restart it
(which surfaces bad datastore config as a CrashLoopBackOff instead of silent 500s).
"""

import asyncio
import json
import logging
import os
import random
import time
import uuid
from contextlib import asynccontextmanager

import redis as redis_lib
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, make_asgi_app

SERVICE = "catalog"
REDIS_URL = os.getenv("REDIS_URL", "redis://redis.shop.svc.cluster.local:6379/0")
STARTUP_RETRIES = 5

# Fault knobs — see apps/README.md. Flipped by scenarios via `kubectl set env`.
ERROR_RATE = float(os.getenv("ERROR_RATE", "0"))
EXTRA_LATENCY_MS = int(os.getenv("EXTRA_LATENCY_MS", "0"))
ERROR_MESSAGE = "catalog query failed"

QUIET_PATHS = ("/metrics", "/healthz", "/readyz")

SEED_PRODUCTS = [
    {"id": 1, "name": "Mechanical Keyboard", "price": 89.0, "stock": 120},
    {"id": 2, "name": "USB-C Dock", "price": 149.0, "stock": 45},
    {"id": 3, "name": "27in 4K Monitor", "price": 329.0, "stock": 60},
    {"id": 4, "name": "1080p Webcam", "price": 59.0, "stock": 200},
    {"id": 5, "name": "Laptop Stand", "price": 39.0, "stock": 310},
]


class JsonFormatter(logging.Formatter):
    EXTRA_FIELDS = ("request_id", "status", "latency_ms", "upstream", "error")

    def format(self, record):
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)) + "Z",
            "level": record.levelname,
            "service": SERVICE,
            "msg": record.getMessage(),
        }
        for field in self.EXTRA_FIELDS:
            value = record.__dict__.get(field)
            if value is not None:
                entry[field] = value
        return json.dumps(entry)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.getLogger().handlers = [handler]
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("uvicorn.access").disabled = True
logger = logging.getLogger(SERVICE)

rdb: redis_lib.Redis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global rdb
    last_error = None
    for attempt in range(1, STARTUP_RETRIES + 1):
        try:
            rdb = redis_lib.Redis.from_url(REDIS_URL, socket_connect_timeout=2,
                                           socket_timeout=2, decode_responses=True)
            rdb.ping()
            last_error = None
            break
        except redis_lib.exceptions.RedisError as exc:
            last_error = exc
            logger.warning("cannot reach redis at %s (attempt %d/%d): %s",
                           REDIS_URL, attempt, STARTUP_RETRIES, exc)
            await asyncio.sleep(2)
    if last_error is not None:
        logger.critical("giving up after %d attempts: redis unreachable at %s: %s",
                        STARTUP_RETRIES, REDIS_URL, last_error)
        raise RuntimeError(f"redis unreachable at {REDIS_URL}")
    for product in SEED_PRODUCTS:
        rdb.setnx(f"product:{product['id']}", json.dumps(product))
    logger.info("connected to redis at %s, %d products available", REDIS_URL, len(SEED_PRODUCTS))
    yield


app = FastAPI(title=SERVICE, lifespan=lifespan)
app.mount("/metrics", make_asgi_app())

REQUESTS = Counter("http_requests_total", "HTTP requests", ["service", "method", "path", "status"])
LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency", ["service", "method", "path"])


@app.middleware("http")
async def observe(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    quiet = request.url.path.startswith(QUIET_PATHS)
    start = time.perf_counter()

    if not quiet and EXTRA_LATENCY_MS:
        await asyncio.sleep(EXTRA_LATENCY_MS / 1000)
    if not quiet and ERROR_RATE and random.random() < ERROR_RATE:
        response = JSONResponse(status_code=500, content={"error": ERROR_MESSAGE, "request_id": request_id})
    else:
        response = await call_next(request)

    latency_ms = round((time.perf_counter() - start) * 1000, 1)
    response.headers["x-request-id"] = request_id
    route = request.scope.get("route")
    path = route.path if route else request.url.path
    REQUESTS.labels(SERVICE, request.method, path, response.status_code).inc()
    LATENCY.labels(SERVICE, request.method, path).observe(latency_ms / 1000)
    if not quiet:
        level = logging.WARNING if response.status_code >= 500 else logging.INFO
        logger.log(level, "%s %s -> %s", request.method, request.url.path, response.status_code,
                   extra={"request_id": request_id, "status": response.status_code, "latency_ms": latency_ms})
    return response


@app.get("/products")
def list_products():
    keys = sorted(rdb.keys("product:*"))
    return [json.loads(rdb.get(key)) for key in keys]


@app.get("/products/{product_id}")
def get_product(product_id: int):
    raw = rdb.get(f"product:{product_id}")
    if raw is None:
        raise HTTPException(status_code=404, detail="product not found")
    return json.loads(raw)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    try:
        rdb.ping()
    except (redis_lib.exceptions.RedisError, AttributeError):
        return JSONResponse(status_code=503, content={"status": "redis unreachable"})
    return {"status": "ok"}
