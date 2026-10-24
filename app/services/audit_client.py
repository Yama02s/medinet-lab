import httpx
import logging
from app.core.config import settings
from app.schemas.audit import AuditEventPayload

logger = logging.getLogger("medinet_audit")

async def send_audit_event(event: AuditEventPayload) -> None:
    """Envía eventos de seguridad al módulo AUD sin bloquear la petición principal."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            payload = event.model_dump(mode="json")
            response = await client.post(settings.AUD_WEBHOOK_URL, json=payload)
            if response.status_code not in (200, 201, 202):
                logger.warning(f"AUD webhook respondió con estado {response.status_code}")
    except Exception as exc:
        logger.error(f"Fallo al emitir evento de auditoría a AUD ({event.event_type}): {str(exc)}")
