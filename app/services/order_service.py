from fastapi import HTTPException, status

VALID_TRANSITIONS = {
    "SOLICITADO": ["EN_PROCESO", "CANCELADO"],
    "EN_PROCESO": ["RESULTADO_CARGADO", "CANCELADO"],
    "RESULTADO_CARGADO": ["ENTREGADO"],
    "ENTREGADO": [],
    "CANCELADO": []
}

def validate_status_transition(current_status: str, new_status: str) -> None:
    allowed = VALID_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transición de estado inválida: no se puede pasar de '{current_status}' a '{new_status}'"
        )
