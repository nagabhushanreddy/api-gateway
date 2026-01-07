from pydantic_settings import BaseSettings
from utils_api.config import load_settings


class Settings(BaseSettings):
    SERVICE_NAME: str = "api-gateway"
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "local"


settings = load_settings(Settings)
