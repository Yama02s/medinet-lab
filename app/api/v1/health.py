from fastapi import APIRouter, status

router = APIRouter(tags=["Health"])

@router.get("/health", status_code=status.HTTP_200_OK, summary="Healthcheck del servicio")
async def health_check():
    return {"status": "healthy", "module": "LAB", "version": "1.0.0"}
