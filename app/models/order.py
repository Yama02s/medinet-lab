from __future__ import annotations
import uuid
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, CheckConstraint, Index, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.result import LabResult

class LabOrder(Base, TimestampMixin):
    __tablename__ = "lab_orders"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, 
        primary_key=True, 
        default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    doctor_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    exam_type: Mapped[str] = mapped_column(String(100), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), default="normal", nullable=False)
    clinical_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(25), default="SOLICITADO", nullable=False)

    results: Mapped[List[LabResult]] = relationship(
        "LabResult", 
        back_populates="order", 
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint(
            "priority IN ('normal', 'urgente')", 
            name="chk_lab_orders_priority"
        ),
        CheckConstraint(
            "status IN ('SOLICITADO', 'EN_PROCESO', 'RESULTADO_CARGADO', 'ENTREGADO', 'CANCELADO')", 
            name="chk_lab_orders_status"
        ),
        Index("idx_lab_orders_patient_id", "patient_id"),
        Index("idx_lab_orders_doctor_id", "doctor_id"),
        Index("idx_lab_orders_status", "status"),
    )
