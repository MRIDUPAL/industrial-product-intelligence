from sqlalchemy import create_engine, text

from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)


def check_database_connection() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))