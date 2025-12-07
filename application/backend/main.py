import os
import time

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Load Testing Backend")

# Allow all origins for simplicity in this experiment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variable to hold memory for memory stress test
_memory_holder = []


@app.get("/")
def read_root():
    return {"Hello": "World", "Service": "Backend", "status": "healthy"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/crash")
def crash():
    """
    Endpoint to simulate a service crash.
    Uses os._exit(1) to forcefully terminate the process,
    bypassing Python's cleanup handlers and FastAPI's signal handling.
    """
    # Force exit - no cleanup, no signal handling
    os._exit(1)


@app.get("/stress/cpu")
def stress_cpu(
    duration: int = Query(default=5, ge=1, le=60, description="Duration in seconds"),
):
    """
    CPU stress test: performs heavy computation for the specified duration.
    Computes prime numbers using a naive algorithm to maximize CPU usage.
    """
    start_time = time.time()
    count = 0

    def is_prime(n):
        if n < 2:
            return False
        for i in range(2, int(n**0.5) + 1):
            if n % i == 0:
                return False
        return True

    num = 2
    while time.time() - start_time < duration:
        if is_prime(num):
            count += 1
        num += 1

    elapsed = time.time() - start_time
    return {
        "type": "cpu_stress",
        "duration_requested": duration,
        "duration_actual": round(elapsed, 2),
        "primes_found": count,
        "last_number_checked": num,
    }


@app.get("/stress/memory")
def stress_memory(
    size_mb: int = Query(
        default=100, ge=1, le=2000, description="Memory to allocate in MB"
    ),
):
    """
    Memory stress test: allocates a large array in memory.
    The memory is held until the next call or server restart.
    """
    global _memory_holder

    # Clear previous allocation
    _memory_holder.clear()

    # Allocate memory (1 MB = 1024 * 1024 bytes, using integers)
    # Each Python int in a list takes about 28 bytes overhead, so we use bytes
    try:
        # Allocate as bytes - more memory efficient representation
        _memory_holder.append(bytearray(size_mb * 1024 * 1024))

        return {
            "type": "memory_stress",
            "allocated_mb": size_mb,
            "status": "allocated",
            "message": f"Allocated {size_mb} MB of memory",
        }
    except MemoryError:
        return {
            "type": "memory_stress",
            "requested_mb": size_mb,
            "status": "failed",
            "message": "Memory allocation failed - not enough memory",
        }


@app.get("/stress/memory/release")
def release_memory():
    """Release previously allocated memory."""
    global _memory_holder
    size_released = len(_memory_holder)
    _memory_holder.clear()
    return {
        "type": "memory_release",
        "status": "released",
        "allocations_cleared": size_released,
    }


@app.get("/stress/io")
def stress_io(
    duration: int = Query(default=5, ge=1, le=60, description="Duration in seconds"),
):
    """
    I/O stress test: simulates I/O delay by sleeping.
    This blocks the worker and simulates slow I/O operations.
    """
    time.sleep(duration)
    return {"type": "io_stress", "duration": duration, "status": "completed"}


@app.get("/stress/combined")
def stress_combined(
    cpu_duration: int = Query(default=3, ge=1, le=30),
    memory_mb: int = Query(default=50, ge=1, le=500),
):
    """
    Combined stress test: allocates memory AND runs CPU stress.
    Useful for simulating realistic load patterns.
    """
    global _memory_holder

    # Allocate memory
    try:
        _memory_holder.append(bytearray(memory_mb * 1024 * 1024))
    except MemoryError:
        pass

    # CPU stress
    start_time = time.time()
    count = 0
    num = 2

    def is_prime(n):
        if n < 2:
            return False
        for i in range(2, int(n**0.5) + 1):
            if n % i == 0:
                return False
        return True

    while time.time() - start_time < cpu_duration:
        if is_prime(num):
            count += 1
        num += 1

    return {
        "type": "combined_stress",
        "memory_allocated_mb": memory_mb,
        "cpu_duration": cpu_duration,
        "primes_found": count,
    }


@app.get("/metrics/info")
def metrics_info():
    """
    Returns basic process info useful for monitoring demos.
    """
    import resource

    usage = resource.getrusage(resource.RUSAGE_SELF)

    return {
        "pid": os.getpid(),
        "memory_holder_allocations": len(_memory_holder),
        "user_time": usage.ru_utime,
        "system_time": usage.ru_stime,
        "max_rss_kb": usage.ru_maxrss,
    }
