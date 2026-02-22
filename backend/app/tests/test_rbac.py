from app.models.db import User, UserRole
from app.services.rbac import can_access_namespace, filter_namespaces


def test_filter_namespaces_for_viewer() -> None:
    user = User(email='v@example.com', password_hash='x', role=UserRole.viewer, allowed_namespaces=['team-a'])
    assert filter_namespaces(user, ['team-a', 'team-b']) == ['team-a']
    assert can_access_namespace(user, 'team-b') is False


def test_filter_namespaces_admin() -> None:
    user = User(email='a@example.com', password_hash='x', role=UserRole.admin, allowed_namespaces=[])
    assert filter_namespaces(user, ['z', 'a']) == ['a', 'z']
    assert can_access_namespace(user, 'any') is True
