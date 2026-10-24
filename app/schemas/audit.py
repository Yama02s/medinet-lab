import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class AuditEventPayload(BaseModel):
    module: str = Field(default="LAB")
    event_type: str
    severity: str  # INFO, WARNING, CRITICAL
    actor_id: Optional[uuid.UUID] = None
    actor_role: Optional[str] = None
    resource_id: Optional[str] = None
    ip: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
