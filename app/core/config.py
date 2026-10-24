from typing import List
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "MediNet LAB Service"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    # PostgreSQL 16
    DATABASE_URL: str

    # JWT Config (Emitido por módulo IAM)
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"

    # Storage y Seguridad de Archivos
    UPLOAD_STORAGE_PATH: str = "./storage/secure_uploads"
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB por defecto

    # Auditoría Externa (AUD)
    AUD_WEBHOOK_URL: str = "http://medinet-aud:8000/api/v1/audit/events"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()
