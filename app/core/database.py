"""
数据库连接
"""
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_runtime_schema():
    inspector = inspect(engine)
    if not inspector.has_table("users"):
        return
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "color" not in user_columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE users ADD COLUMN color VARCHAR(20) NULL DEFAULT '#93c5fd'")
            )
    if inspector.has_table("tasks"):
        task_columns = {column["name"] for column in inspector.get_columns("tasks")}
        statements = []
        if "node_output" not in task_columns:
            statements.append("ALTER TABLE tasks ADD COLUMN node_output TEXT NULL")
        if "linked_document_id" not in task_columns:
            statements.append("ALTER TABLE tasks ADD COLUMN linked_document_id INTEGER NULL")
        if "delivery_dates" not in task_columns:
            statements.append("ALTER TABLE tasks ADD COLUMN delivery_dates TEXT NULL")
        if "completed_by" not in task_columns:
            statements.append("ALTER TABLE tasks ADD COLUMN completed_by TEXT NULL")
        if statements:
            with engine.begin() as connection:
                for statement in statements:
                    connection.execute(text(statement))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
