from __future__ import annotations
import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, BigInteger, ForeignKey, CheckConstraint, Index, DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.order import LabOrder

class LabResult(Base):
    __tablename__ = "lab_results"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, 
        primary_key=True, 
        default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, 
        ForeignKey("lab_orders.id", ondelete="RESTRICT"), 
        nullable=False
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.utcnow, 
        nullable=False
    )

    order: Mapped[LabOrder] = relationship("LabOrder", back_populates="results")

    __table_args__ = (
        CheckConstraint("file_size_bytes > 0", name="chk_lab_results_size"),
        Index("idx_lab_results_order_id", "order_id"),
        Index("idx_lab_results_sha256", "sha256_hash"),
    )
