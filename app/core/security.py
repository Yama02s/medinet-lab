import uuid
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field
from jose import JWTError, jwt
from fastapi import HTTPException, status
from app.core.config import settings

class UserRole(str, Enum):
    MEDICO = "medico"
    LABORATORISTA = "laboratorista"
    PACIENTE = "paciente"
    ADMIN = "admin"

class CurrentUser(BaseModel):
    user_id: uuid.UUID
    role: UserRole

def decode_access_token(token: str) -> CurrentUser:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id_raw: Optional[str] = payload.get("sub")
        role_raw: Optional[str] = payload.get("role")

        if user_id_raw is None or role_raw is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token JWT inválido: faltan claims obligatorios (sub, role)",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return CurrentUser(
            user_id=uuid.UUID(user_id_raw),
            role=UserRole(role_raw)
        )
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de autenticación inválidas o expiradas",
            headers={"WWW-Authenticate": "Bearer"},
        )
