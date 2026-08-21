from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import select
from .database import (
    check_database_connection,
    get_session,
    initialize_database,
)
from .models import Product
from .schemas.product import ProductCreate
from .models import Evidence, Product
from .schemas.product import EvidenceCreate, ProductCreate
from fastapi.middleware.cors import CORSMiddleware
import httpx

from .schemas.product import (
    EvidenceCreate,
    IngestPreviewRequest,
    ProductCreate,
)
from .services.ingestion import fetch_page

app = FastAPI(
    title="Industrial Product Intelligence API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.get("/products")
def list_products(
    session: Session = Depends(get_session),
):
    products = session.scalars(
        select(Product).order_by(Product.id)
    ).all()

    return [
        {
            "id": product.id,
            "brand": product.brand,
            "model": product.model,
            "name": product.name,
            "category": product.category,
            "description": product.description,
            "specifications": product.specifications,
            "source_urls": product.source_urls,
            "created_at": product.created_at,
        }
        for product in products
    ]

@app.get("/products/{product_id}")
def get_product(
    product_id: int,
    session: Session = Depends(get_session),
):
    product = session.scalar(
        select(Product).where(Product.id == product_id)
    )

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return {
        "id": product.id,
        "brand": product.brand,
        "model": product.model,
        "name": product.name,
        "category": product.category,
        "description": product.description,
        "specifications": product.specifications,
        "source_urls": product.source_urls,
        "created_at": product.created_at,
    }

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

@app.post("/evidence")
def create_evidence(
    evidence_data: EvidenceCreate,
    session: Session = Depends(get_session),
):
    evidence = Evidence(
        **evidence_data.model_dump(mode="json"),
    )

    session.add(evidence)
    session.commit()
    session.refresh(evidence)

    return {
        "id": evidence.id,
        "product_id": evidence.product_id,
        "status": "created",
    }

@app.get("/products/{product_id}/evidence")
def list_product_evidence(
    product_id: int,
    session: Session = Depends(get_session),
):
    evidence_records = session.scalars(
        select(Evidence)
        .where(Evidence.product_id == product_id)
        .order_by(Evidence.id)
    ).all()

    return [
        {
            "id": evidence.id,
            "product_id": evidence.product_id,
            "field_name": evidence.field_name,
            "value": evidence.value,
            "source_url": evidence.source_url,
            "confidence": evidence.confidence,
            "extraction_method": evidence.extraction_method,
            "created_at": evidence.created_at,
        }
        for evidence in evidence_records
    ]

@app.post("/ingest/preview")
async def ingest_preview(request: IngestPreviewRequest):
    try:
        page = await fetch_page(str(request.url))
    except httpx.HTTPError:
        raise HTTPException(
            status_code=400,
            detail="Could not fetch the source URL",
        )

    return {
        "url": page["url"],
        "title": page["title"],
        "character_count": len(page["text"]),
        "text_preview": page["text"][:1000],
    }