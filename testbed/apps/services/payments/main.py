"""payments — simulated third-party payment processor.

Stands in for a Stripe-like external dependency: charges take a few dozen
milliseconds and a small fraction decline (402) as normal business noise.
ERROR_RATE simulates the upstream processor degrading (500s).
"""

import asyncio
import json
import logging
import os
import random
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, make_asgi_app
from pydantic import BaseModel

SERVICE = "payments"
DECLINE_RATE = float(os.getenv("DECLINE_RATE", "0.05"))

# Fault knobs — see apps/README.md. Flipped by scenarios via `kubectl set env`.
ERROR_RATE = float(os.getenv("ERROR_RATE", "0"))
EXTRA_LATENCY_MS = int(os.getenv("EXTRA_LATENCY_MS", "0"))
ERROR_MESSAGE = "charge failed: upstream payment processor timed out"

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


class ChargeRequest(BaseModel):
    order_id: str
    amount: float


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


@app.post("/charge")
async def charge(payload: ChargeRequest):
    # Simulated processor round-trip.
    await asyncio.sleep(random.uniform(0.02, 0.08))
    if random.random() < DECLINE_RATE:
        return JSONResponse(status_code=402,
                            content={"status": "declined", "order_id": payload.order_id})
    return {"charge_id": uuid.uuid4().hex[:12], "order_id": payload.order_id,
            "amount": payload.amount, "status": "captured"}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    return {"status": "ok"}
