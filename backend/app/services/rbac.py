from app.models.db import User, UserRole


def can_access_namespace(user: User, namespace: str) -> bool:
    if user.role == UserRole.admin:
        return True
    return namespace in user.allowed_namespaces


def filter_namespaces(user: User, namespaces: list[str]) -> list[str]:
    if user.role == UserRole.admin:
        return sorted(namespaces)
    allowed = set(user.allowed_namespaces)
    return sorted([ns for ns in namespaces if ns in allowed])
