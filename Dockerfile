# ==============================================================================
# ETAPA 1: BUILDER (Compilación de dependencias e aislamiento de herramientas)
# ==============================================================================
FROM python:3.12-alpine AS builder

# Evita que Python escriba archivos .pyc en disco y fuerza logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Instala dependencias de sistema necesarias SOLO para compilar paquetes en Alpine
RUN apk add --no-cache gcc musl-dev libffi-dev postgresql-dev

# Crea entorno virtual aislado para empaquetar todas las librerías limpias
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copia e instala los requerimientos dentro del entorno virtual /opt/venv
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ==============================================================================
# ETAPA 2: RUNTIME (Imagen final de producción endurecida / Hardened)
# ==============================================================================
FROM python:3.12-alpine AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Instala únicamente librerías dinámicas de ejecución (libpq para asyncpg y curl para healthcheck)
RUN apk add --no-cache libpq curl && \
    # Crea grupo y usuario del sistema sin privilegios (nonroot) sin acceso a shell
    addgroup -g 10001 -S nonroot && \
    adduser -u 10001 -S nonroot -G nonroot -s /sbin/nologin

WORKDIR /app

# Copia el entorno virtual compilado desde la etapa builder
COPY --from=builder /opt/venv /opt/venv

# Copia el código fuente de la aplicación y configuración de migraciones
COPY --chown=nonroot:nonroot ./app ./app
COPY --chown=nonroot:nonroot ./alembic ./alembic
COPY --chown=nonroot:nonroot ./alembic.ini ./alembic.ini

# Crea el directorio de almacenamiento seguro fuera del código y asigna propiedad a nonroot
RUN mkdir -p /app/storage/secure_uploads && \
    chown -R nonroot:nonroot /app/storage && \
    chmod 700 /app/storage/secure_uploads

# Cambia al usuario sin privilegios antes de iniciar el proceso (Requisito Crítico)
USER nonroot

EXPOSE 8000

# Healthcheck nativo del contenedor
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Ejecuta migraciones de Alembic automáticamente y levanta Uvicorn
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
