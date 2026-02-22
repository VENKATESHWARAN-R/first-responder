from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.security import get_password_hash
from app.main import app
from app.models.db import User, UserRole


def _setup_db() -> Session:
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    session.add(User(email='admin@test.dev', password_hash=get_password_hash('pass'), role=UserRole.admin, allowed_namespaces=[]))
    session.commit()
    return session


def test_namespaces_endpoint_contract(monkeypatch) -> None:
    from app.api import routes
    from app.api.deps import get_session

    session = _setup_db()
    app.dependency_overrides[get_session] = lambda: session

    monkeypatch.setattr(routes.k8s_service, 'list_namespaces', lambda: ['default'])
    monkeypatch.setattr(
        routes.k8s_service,
        'namespace_summary',
        lambda ns: {
            'namespace': ns,
            'health': 'Healthy',
            'deployments': '1/1',
            'pods': {'running': 1, 'pending': 0, 'failed': 0},
            'top_restart_count': 0,
            'last_refreshed': datetime.now(timezone.utc),
        },
    )

    client = TestClient(app)
    response = client.post('/api/auth/login', json={'email': 'admin@test.dev', 'password': 'pass'})
    assert response.status_code == 200
    cookies = response.cookies
    result = client.get('/api/namespaces', cookies=cookies)
    assert result.status_code == 200
    body = result.json()
    assert isinstance(body, list)
    assert body[0]['namespace'] == 'default'
    assert 'health' in body[0]
