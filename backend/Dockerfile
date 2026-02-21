FROM python:3.11-slim

WORKDIR /app

# Assume build context is repository root
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code into /app/backend
COPY backend/ backend/

# Set PYTHONPATH to /app so 'backend' package is importable
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
