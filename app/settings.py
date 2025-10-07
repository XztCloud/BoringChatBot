import secrets

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 有效期 1 天
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 1
    SECRET_KEY: str = secrets.token_urlsafe(32)


settings = Settings()
