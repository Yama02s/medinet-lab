import io
import uuid
import hashlib
from pathlib import Path
from typing import Tuple, Iterator
import boto3
from botocore.exceptions import BotoCoreError, ClientError
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
    def _get_s3_client():
        # Toma credenciales automáticamente desde LabInstanceProfile en AWS Academy
        return boto3.client("s3", region_name=settings.AWS_REGION)

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
    async def process_and_save_upload(cls, file: UploadFile) -> Tuple[str, str, str, int, str, str]:
        if not file.filename:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nombre de archivo inválido")

        original_filename = Path(file.filename).name
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

        sha256_hasher = hashlib.sha256()
        total_size = 0
        memory_buffer = io.BytesIO()

        # Lectura controlada por bloques de 64 KB con límite de cuota
        while chunk := await file.read(1024 * 64):
            total_size += len(chunk)
            if total_size > settings.MAX_FILE_SIZE_BYTES:
                memory_buffer.close()
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"El archivo excede el tamaño máximo permitido de {settings.MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB"
                )
            sha256_hasher.update(chunk)
            memory_buffer.write(chunk)

        final_hash = sha256_hasher.hexdigest()
        stored_filename = f"{uuid.uuid4()}{ext}"
        memory_buffer.seek(0)

        # Modo 1: Almacenamiento compartido en Amazon S3 (Multi-AZ)
        if settings.STORAGE_BACKEND.lower() == "s3":
            if not settings.AWS_S3_BUCKET_NAME:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Configuración de almacenamiento en nube incompleta"
                )
            s3_key = f"resultados/{stored_filename}"
            try:
                s3 = cls._get_s3_client()
                s3.put_object(
                    Bucket=settings.AWS_S3_BUCKET_NAME,
                    Key=s3_key,
                    Body=memory_buffer.getvalue(),
                    ContentType=detected_mime,
                    ServerSideEncryption="AES256",
                    Metadata={"sha256": final_hash}
                )
            except (BotoCoreError, ClientError):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Error al almacenar el documento clínico de forma segura"
                )
            finally:
                memory_buffer.close()

            storage_uri = f"s3://{settings.AWS_S3_BUCKET_NAME}/{s3_key}"
            return original_filename, stored_filename, detected_mime, total_size, final_hash, storage_uri

        # Modo 2: Almacenamiento local en disco (Pruebas en Windows)
        storage_base = Path(settings.UPLOAD_STORAGE_PATH).resolve()
        storage_base.mkdir(parents=True, exist_ok=True)
        destination_path = (storage_base / stored_filename).resolve()

        if not str(destination_path).startswith(str(storage_base)):
            memory_buffer.close()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ruta de archivo no autorizada")

        with open(destination_path, "wb") as out_file:
            out_file.write(memory_buffer.getvalue())
        memory_buffer.close()

        return original_filename, stored_filename, detected_mime, total_size, final_hash, str(destination_path)

    @classmethod
    def stream_from_s3(cls, storage_path: str) -> Iterator[bytes]:
        """Obtiene el flujo binario de un objeto privado en S3."""
        # Formato esperado: s3://nombre-bucket/resultados/uuid.pdf
        without_scheme = storage_path.replace("s3://", "", 1)
        bucket_name, key = without_scheme.split("/", 1)
        try:
            s3 = cls._get_s3_client()
            obj = s3.get_object(Bucket=bucket_name, Key=key)
            return obj["Body"].iter_chunks(chunk_size=1024 * 64)
        except (BotoCoreError, ClientError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El documento clínico no está disponible en el almacenamiento seguro"
            )