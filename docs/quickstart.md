# Quickstart

## Local run

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev
```

Login with `ADMIN_EMAIL` / `ADMIN_PASSWORD` (defaults: `admin@example.com` / `admin123!`).

## In-cluster deploy (Helm)

```bash
docker build -t namespace-observatory-backend:latest backend
docker build -t namespace-observatory-frontend:latest frontend
helm upgrade --install namespace-observatory charts/namespace-observatory -n observatory --create-namespace
kubectl -n observatory get pods
kubectl -n observatory port-forward svc/namespace-observatory-frontend 3000:80
```
