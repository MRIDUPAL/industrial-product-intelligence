from fastapi import FastAPI, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from .database import check_database_connection

app = FastAPI(
    title="Industrial Product Intelligence API",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/database")
def database_health_check():
    try:
        check_database_connection()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database is unavailable",
        )

    return {"status": "ok", "database": "connected"}