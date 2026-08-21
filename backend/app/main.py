from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
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
from .services.gemini_extractor import GeminiExtraction, extract_pdf

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

@app.post("/ai/extract-pdf", response_model=GeminiExtraction)
async def extract_pdf_endpoint(
    file: UploadFile = File(...),
):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported",
        )

    pdf_bytes = await file.read()

    try:
        return extract_pdf(pdf_bytes)
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error))
    except Exception as error:
        print(
            f"Gemini extraction failed: "
            f"{type(error).__name__}: {error}"
        )
        raise HTTPException(
            status_code=502,
            detail="Gemini extraction failed",
        )

@app.post("/ai/import-pdf")
async def import_pdf(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported",
        )

    pdf_bytes = await file.read()

    try:
        extraction = extract_pdf(pdf_bytes)
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error))
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Gemini extraction failed",
        )

    source_reference = f"uploaded://{file.filename or 'document.pdf'}"

    product = Product(
        brand=extraction.brand or "Unknown",
        model=extraction.model or "Unknown",
        name=extraction.name,
        category=extraction.category,
        description=extraction.description,
        specifications={
            item.key: item.value
            for item in extraction.specifications
        },
        source_urls=[source_reference],
    )

    session.add(product)
    session.flush()

    for item in extraction.evidence:
        session.add(
            Evidence(
                product_id=product.id,
                field_name=item.field_name,
                value=item.value,
                source_url=item.source_url or source_reference,
                extraction_method="gemini",
            )
        )

    session.commit()
    session.refresh(product)

    return {
        "product_id": product.id,
        "name": product.name,
        "evidence_count": len(extraction.evidence),
        "status": "imported",
    }