import time
import uuid
from collections import defaultdict
from typing import List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.security import decode_access_token, CurrentUser, UserRole

security_scheme = HTTPBearer(auto_error=True)

# Almacén en memoria para Rate Limiting por IP (ventana deslizante)
_rate_limit_store = defaultdict(list)

def rate_limit(max_requests: int = 15, window_seconds: int = 60):
    """Mitiga ataques de denegación de servicio (DoS) y fuerza bruta en carga/descarga."""
    def limiter(request: Request):
        client_ip = get_client_ip(request)
        now = time.time()
        window_start = now - window_seconds
        # Limpia timestamps antiguos fuera de la ventana
        _rate_limit_store[client_ip] = [t for t in _rate_limit_store[client_ip] if t > window_start]
        if len(_rate_limit_store[client_ip]) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Límite de peticiones excedido. Intente nuevamente más tarde."
            )
        _rate_limit_store[client_ip].append(now)
    return limiter

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme)
) -> CurrentUser:
    return decode_access_token(credentials.credentials)

def require_roles(allowed_roles: List[UserRole]):
    def role_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No posee los privilegios requeridos para ejecutar esta operación"
            )
        return current_user
    return role_checker

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
