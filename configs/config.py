from enum import Enum
from pydantic_settings import BaseSettings

class EnvironmentMode(Enum):
    DEVELOPMENT = 0
    STAGING = 1
    PRODUCTION = 2

class Settings(BaseSettings):

    OAUTH2_URL: str = ""
    OAUTH2_TOKEN: str = ""
    DB_CONFIG: str = ""
    OAUTH_ROLE: str = 'PROJECT_USER'
    IS_STAGING: bool = True
    QUEUE_LOCATION: str
    PROJECT_NAME: str
    POSTGRES_SCHEMA: str
    RABBITMQ_EXCHANGE_NAME: str
    RABBITMQ_BASE_URL: str
    RABBITMQ_USER: str
    RABBITMQ_PASS: str
    RABBITMQ_VHOST: str
    EXPECTED_AUDIENCE: str
    EXPECTED_SA_EMAIL: str

    ENV_MODE: int = 0

    #Redis
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str

    #OpenTelemetry
    OTEL_EXPORTER_OTLP_ENDPOINT: str
    OTEL_SERVICE_NAME: str
    OTEL_SERVICE_VERSION: str

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
