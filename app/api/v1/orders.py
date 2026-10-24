import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import CurrentUser, UserRole
from app.api.deps import get_current_user, require_roles, get_client_ip
from app.models.order import LabOrder
from app.schemas.order import LabOrderCreate, LabOrderResponse, LabOrderListResponse, LabOrderStatusUpdate
from app.schemas.audit import AuditEventPayload
from app.services.order_service import validate_status_transition
from app.services.audit_client import send_audit_event

router = APIRouter(prefix="/api/lab/orders", tags=["Órdenes de Laboratorio"])

@router.post("", response_model=LabOrderResponse, status_code=status.HTTP_201_CREATED, summary="Médico crea orden")
async def create_order(
    payload: LabOrderCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles([UserRole.MEDICO]))
):
    new_order = LabOrder(
        patient_id=payload.patient_id,
        doctor_id=current_user.user_id,  # OWASP A01: Siempre se toma el doctor del JWT autenticado
        exam_type=payload.exam_type,
        priority=payload.priority,
        clinical_notes=payload.clinical_notes,
        status="SOLICITADO"
    )
    db.add(new_order)
    await db.commit()
    await db.refresh(new_order)

    background_tasks.add_task(
        send_audit_event,
        AuditEventPayload(
            event_type="ORDER_CREATED",
            severity="INFO",
            actor_id=current_user.user_id,
            actor_role=current_user.role.value,
            resource_id=str(new_order.id),
            ip=get_client_ip(request)
        )
    )
    return new_order

@router.get("", response_model=LabOrderListResponse, summary="Listar órdenes según rol con paginación")
async def list_orders(
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    query = select(LabOrder)
    count_query = select(func.count(LabOrder.id))

    # Control de acceso horizontal estricto
    if current_user.role == UserRole.MEDICO:
        query = query.where(LabOrder.doctor_id == current_user.user_id)
        count_query = count_query.where(LabOrder.doctor_id == current_user.user_id)
    elif current_user.role == UserRole.PACIENTE:
        query = query.where(LabOrder.patient_id == current_user.user_id)
        count_query = count_query.where(LabOrder.patient_id == current_user.user_id)
    elif current_user.role not in (UserRole.LABORATORISTA, UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso no autorizado")

    if status_filter:
        query = query.where(LabOrder.status == status_filter)
        count_query = count_query.where(LabOrder.status == status_filter)

    total_records = await db.scalar(count_query) or 0
    query = query.order_by(LabOrder.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    orders = result.scalars().all()

    return LabOrderListResponse(total=total_records, page=page, page_size=page_size, items=orders)

@router.get("/{id}", response_model=LabOrderResponse, summary="Consultar detalle de una orden")
async def get_order_by_id(
    id: uuid.UUID,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    order = await db.get(LabOrder, id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada")

    # Validación IDOR
    if current_user.role == UserRole.PACIENTE and order.patient_id != current_user.user_id:
        background_tasks.add_task(
            send_audit_event,
            AuditEventPayload(
                event_type="ACCESS_DENIED_IDOR",
                severity="WARNING",
                actor_id=current_user.user_id,
                actor_role=current_user.role.value,
                resource_id=str(id),
                ip=get_client_ip(request)
            )
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado a esta orden")

    if current_user.role == UserRole.MEDICO and order.doctor_id != current_user.user_id:
        background_tasks.add_task(
            send_audit_event,
            AuditEventPayload(
                event_type="ACCESS_DENIED_IDOR",
                severity="WARNING",
                actor_id=current_user.user_id,
                actor_role=current_user.role.value,
                resource_id=str(id),
                ip=get_client_ip(request)
            )
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado a esta orden")

    return order

@router.patch("/{id}/status", response_model=LabOrderResponse, summary="Laboratorista actualiza estado")
async def update_order_status(
    id: uuid.UUID,
    payload: LabOrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles([UserRole.LABORATORISTA]))
):
    order = await db.get(LabOrder, id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada")

    validate_status_transition(order.status, payload.status)
    order.status = payload.status
    await db.commit()
    await db.refresh(order)
    return order

@router.delete("/{id}", status_code=status.HTTP_200_OK, summary="Cancelación lógica por el médico creador")
async def cancel_order(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles([UserRole.MEDICO]))
):
    order = await db.get(LabOrder, id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada")

    if order.doctor_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el médico creador puede cancelar la orden")

    if order.status != "SOLICITADO":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solo órdenes en estado SOLICITADO pueden cancelarse")

    order.status = "CANCELADO"
    await db.commit()
    return {"detail": "Orden cancelada exitosamente", "id": str(id)}
