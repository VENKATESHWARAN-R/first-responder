from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'Namespace Observatory API'
    secret_key: str = 'change-me'
    access_token_exp_minutes: int = 120
    database_url: str = 'sqlite:///./namespace_observatory.db'
    admin_email: str = 'admin@example.com'
    admin_password: str = 'admin123!'
    cache_ttl_seconds: int = 20
    k8s_timeout_seconds: int = 10
    secure_cookies: bool = False


settings = Settings()


class HealthStatus(BaseModel):
    status: str
    reason: str
