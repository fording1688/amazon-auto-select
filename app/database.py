from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import get_settings


settings = get_settings()
database_url = settings.database_url
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {}
if database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    database_url,
    connect_args=connect_args,
    future=True,
    pool_pre_ping=True,
    pool_recycle=1800,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    migrate_reporting_columns()


def migrate_reporting_columns() -> None:
    dialect = engine.dialect.name

    def col_type(kind: str) -> str:
        if dialect == "postgresql":
            return {
                "string": "varchar(255)",
                "text": "text",
                "int": "integer",
                "float": "double precision",
                "bool": "boolean default true",
                "datetime": "timestamp",
            }[kind]
        return {
            "string": "varchar(255)",
            "text": "text",
            "int": "integer",
            "float": "float",
            "bool": "boolean default 1",
            "datetime": "datetime",
        }[kind]

    def table_exists(conn, table: str) -> bool:
        if dialect == "postgresql":
            return bool(conn.execute(text("select to_regclass(:table_name) is not null"), {"table_name": table}).scalar())
        return inspect(conn).has_table(table)

    def column_exists(conn, table: str, column: str) -> bool:
        if dialect == "postgresql":
            return bool(
                conn.execute(
                    text(
                        "select exists ("
                        "select 1 from information_schema.columns "
                        "where table_schema = 'public' and table_name = :table_name and column_name = :column_name"
                        ")"
                    ),
                    {"table_name": table, "column_name": column},
                ).scalar()
            )
        return column in {item["name"] for item in inspect(conn).get_columns(table)}

    additions: dict[str, dict[str, str]] = {
        "stores": {
            "user_id": "int",
        },
        "import_batches": {
            "user_id": "int",
            "store_id": "int",
            "store_name": "string",
            "business_date": "datetime",
            "project_name": "string",
            "marketplace": "string",
            "uploaded_by": "string",
            "uploaded_at": "datetime",
            "period_start": "datetime",
            "period_end": "datetime",
            "duplicate_strategy": "string",
            "duplicate_count": "int",
        },
        "listing_projects": {
            "user_id": "int",
        },
        "recommendations": {
            "user_id": "int",
        },
    }
    metric_tables = [
        "business_metrics",
        "search_term_metrics",
        "advertised_product_metrics",
        "campaign_metrics",
        "targeting_metrics",
        "bulk_operation_items",
        "inventory_items",
        "cost_items",
        "listing_items",
        "sales_daily",
        "ads_daily",
        "search_terms",
        "inventory_daily",
    ]
    metric_columns = {
        "user_id": "int",
        "import_batch_id": "int",
        "marketplace": "string",
        "report_date": "datetime",
        "period_start": "datetime",
        "period_end": "datetime",
        "is_active": "bool",
        "data_hash": "string",
    }
    for table in metric_tables:
        additions[table] = metric_columns

    with engine.begin() as conn:
        for table, columns in additions.items():
            if not table_exists(conn, table):
                continue
            for name, kind in columns.items():
                if column_exists(conn, table, name):
                    continue
                conn.execute(text(f"alter table {table} add column {name} {col_type(kind)}"))
        if dialect == "postgresql" and table_exists(conn, "stores"):
            conn.execute(text("alter table stores drop constraint if exists stores_name_key"))
        if table_exists(conn, "import_batches"):
            conn.execute(text("update import_batches set uploaded_at = created_at where uploaded_at is null"))
            conn.execute(text("update import_batches set business_date = coalesce(period_end, period_start, uploaded_at, created_at) where business_date is null"))
            conn.execute(text("update import_batches set project_name = coalesce(project_name, store_name || '-' || report_type) where project_name is null or project_name = ''"))


if __name__ == "__main__":
    init_db()
    print("Database initialized.")
