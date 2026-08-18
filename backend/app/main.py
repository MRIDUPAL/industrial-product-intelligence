from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .database import (
    check_database_connection,
    get_session,
    initialize_database,
)
from .models import Product
from .schemas.product import ProductCreate

app = FastAPI(
    title="Industrial Product Intelligence API",
    version="0.1.0",
)


@app.on_event("startup")
def startup():
    initialize_database()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/database")
def database_health_check():
    try:
        check_database_connection()
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database is unavailable")

    return {"status": "ok", "database": "connected"}


@app.post("/products")
def create_product(
    product_data: ProductCreate,
    session: Session = Depends(get_session),
):
    product = Product(**product_data.model_dump(mode="json"))

    session.add(product)
    session.commit()
    session.refresh(product)

    return {
        "id": product.id,
        "name": product.name,
        "status": "created",
    }