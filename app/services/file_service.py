import os
import uuid
import hashlib
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

MAGIC_NUMBERS = {
    b"%PDF-": ("application/pdf", [".pdf"]),
    b"\xff\xd8\xff": ("image/jpeg", [".jpg", ".jpeg"]),
    b"\x89PNG\r\n\x1a\n": ("image/png", [".png"]),
}

DANGEROUS_EXTENSIONS = {
    ".exe", ".php", ".phtml", ".sh", ".bash", ".js", ".py", ".pl", ".cgi", 
    ".bat", ".cmd", ".msi", ".jar", ".vbs", ".ps1"
}

class SecureFileService:

    @staticmethod
    def _check_double_extensions(filename: str) -> None:
        parts = filename.lower().split(".")
        if len(parts) > 2:
            for part in parts[1:-1]:
                if f".{part}" in DANGEROUS_EXTENSIONS:
                    raise HTTPException(
                        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        detail="Doble extensión o extensión maliciosa detectada en el archivo"
                    )

    @staticmethod
    def _verify_magic_bytes(header: bytes, ext: str) -> str:
        for magic, (mime, valid_exts) in MAGIC_NUMBERS.items():
            if header.startswith(magic):
                if ext in valid_exts:
                    return mime
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="Inconsistencia entre el contenido real (magic bytes) y la extensión declarada"
                )
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Firma de archivo no permitida o contenido no seguro (Solo PDF, JPG, PNG)"
        )

    @classmethod
    async def process_and_save_upload(cls, file: UploadFile) -> Tuple[str, str, int, str]:
        if not file.filename:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nombre de archivo inválido")

        original_filename = Path(file.filename).name  # Sanitiza ruta / path traversal
        cls._check_double_extensions(original_filename)

        ext = Path(original_filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Extensión no permitida. Formatos válidos: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        header = await file.read(16)
        if len(header) < 4:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Archivo vacío o corrupto")
        
        detected_mime = cls._verify_magic_bytes(header, ext)
        await file.seek(0)

        # Genera nombre UUID único en disco
        stored_filename = f"{uuid.uuid4()}{ext}"
        storage_base = Path(settings.UPLOAD_STORAGE_PATH).resolve()
        storage_base.mkdir(parents=True, exist_ok=True)
        destination_path = (storage_base / stored_filename).resolve()

        # Mitigación Path Traversal estricta
        if not str(destination_path).startswith(str(storage_base)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ruta de archivo no autorizada")

        sha256_hasher = hashlib.sha256()
        total_size = 0

        # Escritura en streaming verificando tamaño máximo
        with open(destination_path, "wb") as buffer:
            while chunk := await file.read(1024 * 64):
                total_size += len(chunk)
                if total_size > settings.MAX_FILE_SIZE_BYTES:
                    buffer.close()
                    if destination_path.exists():
                        destination_path.unlink()
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"El archivo excede el tamaño máximo permitido de {settings.MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB"
                    )
                sha256_hasher.update(chunk)
                buffer.write(chunk)

        final_hash = sha256_hasher.hexdigest()
        return original_filename, stored_filename, detected_mime, total_size, final_hash, str(destination_path)
