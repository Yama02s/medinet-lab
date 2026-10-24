import os
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from jose import jwt
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Variables de entorno para entorno de testing aislado
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test_super_secret_jwt_key_2026_medinet"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["UPLOAD_STORAGE_PATH"] = "/tmp/medinet_lab_test_uploads"
os.environ["MAX_FILE_SIZE_BYTES"] = "1048576"  # 1 MB límite en tests para probar error 413 rápido

from app.main import app
from app.core.database import get_db
from app.core.config import settings
from app.models.base import Base
from app.api.deps import _rate_limit_store

# Ajustar configuración en tiempo de ejecución para el test
settings.MAX_FILE_SIZE_BYTES = 1048576
settings.UPLOAD_STORAGE_PATH = "/tmp/medinet_lab_test_uploads"

TEST_ENGINE = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestSessionLocal = async_sessionmaker(bind=TEST_ENGINE, class_=AsyncSession, expire_on_commit=False)

@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as session:
        yield session
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    # Limpiar rate limiter entre tests
    _rate_limit_store.clear()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

def create_test_token(user_id: uuid.UUID, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

@pytest.fixture
def test_ids():
    return {
        "doctor_1": uuid.uuid4(),
        "doctor_2": uuid.uuid4(),
        "patient_1": uuid.uuid4(),
        "patient_2": uuid.uuid4(),
        "lab_tech": uuid.uuid4(),
        "admin": uuid.uuid4(),
    }
