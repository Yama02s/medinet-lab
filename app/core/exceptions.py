from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

logger = logging.getLogger("medinet_security")

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Sanitiza la salida de error de validación sin exponer rutas de código
    errors = exc.errors()
    clean_errors = [{"field": " -> ".join(str(loc) for loc in err.get("loc", [])), "message": err.get("msg")} for err in errors]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Error de validación en la petición", "errors": clean_errors}
    )

async def unhandled_exception_handler(request: Request, exc: Exception):
    # OWASP A05: Nunca exponer stack trace al cliente en producción
    logger.error(f"Error interno no controlado en {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Error interno del servidor. Incidente registrado."}
    )
