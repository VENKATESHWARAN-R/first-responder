"""gateway — public entry point of the shop stack.

Routes browse traffic to catalog and checkout traffic to orders. Generates an
X-Request-ID per inbound request and propagates it downstream so one user request
can be traced across every service's logs.
"""

import asyncio
import json
import logging
import os
import random
import time
import uuid

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, make_asgi_app

SERVICE = "gateway"
CATALOG_URL = os.getenv("CATALOG_URL", "http://catalog.shop.svc.cluster.local:8000")
ORDERS_URL = os.getenv("ORDERS_URL", "http://orders.shop.svc.cluster.local:8000")
UPSTREAM_TIMEOUT_S = float(os.getenv("UPSTREAM_TIMEOUT_S", "5"))

# Fault knobs — see apps/README.md. Flipped by scenarios via `kubectl set env`.
ERROR_RATE = float(os.getenv("ERROR_RATE", "0"))
EXTRA_LATENCY_MS = int(os.getenv("EXTRA_LATENCY_MS", "0"))
ERROR_MESSAGE = "internal error"

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


async def proxy(request: Request, method: str, base: str, upstream: str, path: str, json_body=None):
    request_id = request.state.request_id
    try:
        resp = await client.request(method, f"{base}{path}", json=json_body,
                                    headers={"x-request-id": request_id})
    except httpx.HTTPError as exc:
        logger.error("upstream %s unreachable: %s", upstream, exc,
                     extra={"request_id": request_id, "upstream": upstream, "error": type(exc).__name__})
        return JSONResponse(status_code=502,
                            content={"error": f"{upstream} unreachable", "request_id": request_id})
    try:
        content = resp.json()
    except ValueError:
        content = {"raw": resp.text}
    if resp.status_code >= 500:
        logger.warning("upstream %s returned %s for %s %s", upstream, resp.status_code, method, path,
                       extra={"request_id": request_id, "upstream": upstream, "status": resp.status_code})
        return JSONResponse(status_code=502,
                            content={"error": f"{upstream} failed", "upstream_status": resp.status_code,
                                     "upstream_error": content, "request_id": request_id})
    return JSONResponse(status_code=resp.status_code, content=content)


@app.get("/api/products")
async def list_products(request: Request):
    return await proxy(request, "GET", CATALOG_URL, "catalog", "/products")


@app.get("/api/products/{product_id}")
async def get_product(request: Request, product_id: int):
    return await proxy(request, "GET", CATALOG_URL, "catalog", f"/products/{product_id}")


@app.post("/api/checkout")
async def checkout(request: Request):
    body = await request.json()
    return await proxy(request, "POST", ORDERS_URL, "orders", "/orders", json_body=body)


@app.get("/api/health")
async def health():
    upstreams = {}
    for name, base in (("catalog", CATALOG_URL), ("orders", ORDERS_URL)):
        try:
            resp = await client.get(f"{base}/healthz", timeout=2)
            upstreams[name] = "up" if resp.status_code == 200 else f"degraded ({resp.status_code})"
        except httpx.HTTPError:
            upstreams[name] = "down"
    return {"service": SERVICE, "upstreams": upstreams}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    return {"status": "ok"}
