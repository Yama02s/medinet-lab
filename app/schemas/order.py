import uuid
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, ConfigDict, constr

class LabOrderCreate(BaseModel):
    patient_id: uuid.UUID
    exam_type: constr(strip_whitespace=True, min_length=3, max_length=100) # type: ignore
    priority: Literal["normal", "urgente"] = "normal"
    clinical_notes: Optional[constr(strip_whitespace=True, max_length=2000)] = None # type: ignore

class LabOrderStatusUpdate(BaseModel):
    status: Literal["SOLICITADO", "EN_PROCESO", "RESULTADO_CARGADO", "ENTREGADO", "CANCELADO"]

class LabOrderResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    exam_type: str
    priority: str
    clinical_notes: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class LabOrderListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[LabOrderResponse]
