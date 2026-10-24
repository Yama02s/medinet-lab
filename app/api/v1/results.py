import uuid
from typing import List
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, BackgroundTasks, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import CurrentUser, UserRole
from app.api.deps import get_current_user, require_roles, get_client_ip, rate_limit
from app.models.order import LabOrder
from app.models.result import LabResult
from app.schemas.result import LabResultResponse
from app.schemas.audit import AuditEventPayload
from app.services.file_service import SecureFileService
from app.services.audit_client import send_audit_event

router = APIRouter(prefix="/api/lab", tags=["Resultados de Laboratorio"])

ERROR_RESPONSES = {
    400: {"description": "Petición inválida o estado de orden incompatible"},
    401: {"description": "Token JWT ausente, inválido o expirado"},
    403: {"description": "Acceso denegado (Rol insuficiente o bloqueo IDOR)"},
    404: {"description": "Orden o resultado no encontrado"},
    413: {"description": "El archivo supera el tamaño máximo permitido en .env"},
    415: {"description": "Tipo MIME real (magic bytes) o extensión no permitida"},
    422: {"description": "Error de validación de esquema de entrada"},
    429: {"description": "Demasiadas peticiones (Rate Limit alcanzado)"},
    500: {"description": "Error interno del servidor sanitizado"},
}

@router.post(
    "/orders/{id}/results",
    response_model=LabResultResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
    summary="Laboratorista carga archivo de resultado validado por magic bytes"
)
async def upload_result_file(
    id: uuid.UUID,
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles([UserRole.LABORATORISTA])),
    _limit: None = Depends(rate_limit(max_requests=10, window_seconds=60))
):
    order = await db.get(LabOrder, id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden clínica no encontrada")

    if order.status in ("CANCELADO", "ENTREGADO"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"No se pueden adjuntar resultados a una orden en estado {order.status}")

    try:
        orig_name, stored_name, mime, size, sha256, path = await SecureFileService.process_and_save_upload(file)
    except HTTPException as e:
        background_tasks.add_task(
            send_audit_event,
            AuditEventPayload(
                event_type="REJECTED_FILE_UPLOAD",
                severity="WARNING",
                actor_id=current_user.user_id,
                actor_role=current_user.role.value,
                resource_id=str(id),
                ip=get_client_ip(request)
            )
        )
        raise e

    result_record = LabResult(
        order_id=order.id,
        uploaded_by=current_user.user_id,
        original_filename=orig_name,
        stored_filename=stored_name,
        mime_type=mime,
        file_size_bytes=size,
        sha256_hash=sha256,
        storage_path=path
    )
    order.status = "RESULTADO_CARGADO"

    db.add(result_record)
    await db.commit()
    await db.refresh(result_record)

    background_tasks.add_task(
        send_audit_event,
        AuditEventPayload(
            event_type="RESULT_UPLOADED",
            severity="INFO",
            actor_id=current_user.user_id,
            actor_role=current_user.role.value,
            resource_id=str(result_record.id),
            ip=get_client_ip(request)
        )
    )
    return result_record

@router.get(
    "/results/{id}/download",
    responses=ERROR_RESPONSES,
    summary="Descarga segura de informe con validación anti-IDOR"
)
async def download_result_file(
    id: uuid.UUID,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    _limit: None = Depends(rate_limit(max_requests=20, window_seconds=60))
):
    result_record = await db.get(LabResult, id)
    if not result_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archivo de resultado no encontrado")

    order = await db.get(LabOrder, result_record.order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden asociada inexistente")

    is_authorized = False
    if current_user.role in (UserRole.ADMIN, UserRole.LABORATORISTA):
        is_authorized = True
    elif current_user.role == UserRole.PACIENTE and order.patient_id == current_user.user_id:
        is_authorized = True
    elif current_user.role == UserRole.MEDICO and order.doctor_id == current_user.user_id:
        is_authorized = True

    if not is_authorized:
        background_tasks.add_task(
            send_audit_event,
            AuditEventPayload(
                event_type="UNAUTHORIZED_DOWNLOAD_ATTEMPT",
                severity="CRITICAL",
                actor_id=current_user.user_id,
                actor_role=current_user.role.value,
                resource_id=str(id),
                ip=get_client_ip(request)
            )
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene autorización para descargar este documento")

    file_path = Path(result_record.storage_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El archivo físico no se encuentra en el repositorio")

    background_tasks.add_task(
        send_audit_event,
        AuditEventPayload(
            event_type="RESULT_DOWNLOADED",
            severity="INFO",
            actor_id=current_user.user_id,
            actor_role=current_user.role.value,
            resource_id=str(id),
            ip=get_client_ip(request)
        )
    )

    headers = {
        "X-Content-Type-Options": "nosniff",
        "Content-Disposition": f'attachment; filename="{result_record.original_filename}"'
    }
    return FileResponse(
        path=file_path,
        media_type=result_record.mime_type,
        headers=headers
    )

@router.get(
    "/patients/{patient_id}/results",
    response_model=List[LabResultResponse],
    responses=ERROR_RESPONSES,
    summary="Listado de resultados autorizados de un paciente"
)
async def get_patient_results(
    patient_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    if current_user.role == UserRole.PACIENTE and current_user.user_id != patient_id:
        background_tasks.add_task(
            send_audit_event,
            AuditEventPayload(
                event_type="ACCESS_DENIED_IDOR",
                severity="WARNING",
                actor_id=current_user.user_id,
                actor_role=current_user.role.value,
                resource_id=str(patient_id),
                ip=get_client_ip(request)
            )
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puede acceder a registros de otro paciente")

    query = select(LabResult).join(LabOrder).where(LabOrder.patient_id == patient_id)
    if current_user.role == UserRole.MEDICO:
        query = query.where(LabOrder.doctor_id == current_user.user_id)

    res = await db.execute(query)
    return res.scalars().all()
