import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# For isolated tests we default to SQLite; for MySQL-specific concurrency/locking behavior
# set DATABASE_URL to a MySQL instance (e.g. from docker-compose).
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")

# Trava de segurança: estes testes recriam as tabelas (drop_all/create_all) e
# semeiam apenas 10 assentos. Rodar contra o banco de desenvolvimento "teatro"
# apagaria os 300 assentos. Use sempre um banco terminado em "_test".
if TEST_DATABASE_URL.startswith("mysql"):
    database_name = TEST_DATABASE_URL.rsplit("/", 1)[-1].split("?")[0]
    if not database_name.endswith("_test"):
        raise RuntimeError(
            f"TEST_DATABASE_URL aponta para o banco '{database_name}', que não termina em '_test'.\n"
            "Os testes apagam e recriam as tabelas. Use o banco de teste, por exemplo:\n"
            "  mysql+pymysql://app:app@localhost:3306/teatro_test\n"
            "(criado automaticamente pelo docker-compose.yml)"
        )

engine_kwargs = {}
if TEST_DATABASE_URL.startswith("sqlite"):
    engine_kwargs = {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
elif TEST_DATABASE_URL.startswith("mysql"):
    # pool maior para o teste de 100 requisições simultâneas
    engine_kwargs = {"pool_size": 20, "max_overflow": 40, "pool_pre_ping": True}

engine = create_engine(TEST_DATABASE_URL, **engine_kwargs)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture()
def client():
    from app import database
    from app import main as main_module

    # Point app modules to test engine/session for this run
    database.engine = engine
    database.SessionLocal = TestingSessionLocal
    main_module.engine = engine
    main_module.SessionLocal = TestingSessionLocal

    database.Base.metadata.drop_all(bind=engine)
    database.Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        main_module.seed_seats(db, total=10)
    finally:
        db.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main_module.app.dependency_overrides[database.get_db] = override_get_db
    with TestClient(main_module.app) as c:
        yield c
    main_module.app.dependency_overrides.clear()
