from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from .config import settings
from .models import Base

engine = create_engine(settings.database_url, pool_pre_ping=True)


def check_database_connection() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def initialize_database() -> None:
    Base.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session