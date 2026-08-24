from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def upsert_insert(model):
    """DB별 ON CONFLICT upsert insert()를 반환한다 (postgresql/sqlite 둘 다 on_conflict_do_nothing/
    on_conflict_do_update를 같은 시그니처로 지원해서, 호출부 코드는 DB에 상관없이 그대로 쓸 수 있다)."""
    if engine.dialect.name == "postgresql":
        return postgresql.insert(model)
    return sqlite.insert(model)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
