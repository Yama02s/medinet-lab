import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class LabResultResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    uploaded_by: uuid.UUID
    original_filename: str
    mime_type: str
    file_size_bytes: int
    sha256_hash: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)
