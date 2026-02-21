"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Auth
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480  # 8 hours

    # Admin seed
    admin_email: str = "admin@namespace-observatory.local"
    admin_password: str = "admin"

    # Kubernetes
    k8s_in_cluster: bool = False  # Set True when running inside K8s
    k8s_kubeconfig: str | None = None  # Path to kubeconfig file, None = default

    # Cache
    cache_ttl_seconds: int = 15

    # Database
    db_path: str = "data/users.db"

    # Server
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = {"env_prefix": "NSO_"}


settings = Settings()
