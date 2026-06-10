"""orders — order creation service.

Charges the customer via the payments service, then persists the order to Redis.
Unlike catalog, orders degrades gracefully if Redis is down (orders still go
through, they just aren't persisted) — payments is its only hard dependency.

ENABLE_ORDER_CACHE keeps every confirmed order, including its rendered invoice
blob, in process memory for fast lookups. The cache is unbounded — that is the
deliberate memory-leak bug behind the OOM scenario.
"""

import asyncio
import json
import logging
import os
import random
import time
import uuid

import httpx
import redis as redis_lib
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, make_asgi_app
from pydantic import BaseModel

SERVICE = "orders"
PAYMENTS_URL = os.getenv("PAYMENTS_URL", "http://payments.shop.svc.cluster.local:8000")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis.shop.svc.cluster.local:6379/0")
UPSTREAM_TIMEOUT_S = float(os.getenv("UPSTREAM_TIMEOUT_S", "5"))
ENABLE_ORDER_CACHE = os.getenv("ENABLE_ORDER_CACHE", "false").lower() == "true"
UNIT_PRICE = 19.99

# Fault knobs — see apps/README.md. Flipped by scenarios via `kubectl set env`.
ERROR_RATE = float(os.getenv("ERROR_RATE", "0"))
EXTRA_LATENCY_MS = int(os.getenv("EXTRA_LATENCY_MS", "0"))
ERROR_MESSAGE = "order processing failed"

QUIET_PATHS = ("/metrics", "/healthz", "/readyz")


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

app = FastAPI(title=SERVICE)
app.mount("/metrics", make_asgi_app())

REQUESTS = Counter("http_requests_total", "HTTP requests", ["service", "method", "path", "status"])
LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency", ["service", "method", "path"])

client = httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT_S)
rdb = redis_lib.Redis.from_url(REDIS_URL, socket_connect_timeout=2, socket_timeout=2,
                               decode_responses=True)

_order_cache: dict[str, dict] = {}


class OrderRequest(BaseModel):
    product_id: int
    quantity: int = 1


@app.middleware("http")
async def observe(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    request.state.request_id = request_id
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


@app.post("/orders", status_code=201)
async def create_order(request: Request, payload: OrderRequest):
    request_id = request.state.request_id
    order_id = uuid.uuid4().hex[:10]
    amount = round(payload.quantity * UNIT_PRICE, 2)

    try:
        resp = await client.post(f"{PAYMENTS_URL}/charge",
                                 json={"order_id": order_id, "amount": amount},
                                 headers={"x-request-id": request_id})
    except httpx.HTTPError as exc:
        logger.error("payments unreachable at %s: %s", PAYMENTS_URL, exc,
                     extra={"request_id": request_id, "upstream": "payments",
                            "error": type(exc).__name__})
        return JSONResponse(status_code=502,
                            content={"error": "payments unreachable", "request_id": request_id})
    if resp.status_code == 402:
        logger.info("order %s declined by payments", order_id,
                    extra={"request_id": request_id, "upstream": "payments"})
        return JSONResponse(status_code=402,
                            content={"error": "payment declined", "order_id": order_id})
    if resp.status_code >= 400:
        logger.warning("charge failed for order %s: payments returned %s", order_id, resp.status_code,
                       extra={"request_id": request_id, "upstream": "payments",
                              "status": resp.status_code})
        return JSONResponse(status_code=502,
                            content={"error": "payment failed", "upstream_status": resp.status_code,
                                     "request_id": request_id})

    charge = resp.json()
    order = {"id": order_id, "product_id": payload.product_id, "quantity": payload.quantity,
             "amount": amount, "charge_id": charge["charge_id"], "status": "confirmed"}

    try:
        rdb.set(f"order:{order_id}", json.dumps(order))
    except redis_lib.exceptions.RedisError as exc:
        logger.warning("order %s confirmed but not persisted: %s", order_id, exc,
                       extra={"request_id": request_id, "upstream": "redis"})

    if ENABLE_ORDER_CACHE:
        _order_cache[order_id] = {"order": order, "invoice_pdf": os.urandom(8 * 1024 * 1024)}

    logger.info("order %s confirmed, amount %.2f", order_id, amount,
                extra={"request_id": request_id})
    return order


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    cached = _order_cache.get(order_id)
    if cached is not None:
        return cached["order"]
    try:
        raw = rdb.get(f"order:{order_id}")
    except redis_lib.exceptions.RedisError:
        raw = None
    if raw is None:
        raise HTTPException(status_code=404, detail="order not found")
    return json.loads(raw)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    return {"status": "ok"}
