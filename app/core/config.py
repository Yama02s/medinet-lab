from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "MediNet LAB Service"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_STR: str = "/api/lab"

    # Base de datos (SQLite en local Windows / Amazon RDS PostgreSQL en AWS)
    DATABASE_URL: str

    # JWT Config (Emitido por módulo IAM)
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"

    # Storage Híbrido ("local" para Windows / "s3" para AWS Multi-AZ)
    STORAGE_BACKEND: str = "local"
    UPLOAD_STORAGE_PATH: str = "./storage/secure_uploads"
    AWS_S3_BUCKET_NAME: str = ""
    AWS_REGION: str = "us-east-1"
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB por defecto

    # Auditoría Externa (AUD)
    AUD_WEBHOOK_URL: str = "http://medinet-aud:8000/api/v1/audit/events"

    # CORS Restrictivo (Criterio 2.1.4)
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()