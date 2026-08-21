from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from ..config import settings


class ExtractedSpecification(BaseModel):
    key: str
    value: str


class ExtractedEvidence(BaseModel):
    field_name: str
    value: str
    page: int | None = None
    source_url: str | None = None


class GeminiExtraction(BaseModel):
    brand: str | None = None
    model: str | None = None
    name: str
    category: str | None = None
    description: str | None = None
    specifications: list[ExtractedSpecification] = Field(
        default_factory=list
    )
    evidence: list[ExtractedEvidence] = Field(
        default_factory=list
    )


def extract_pdf(pdf_bytes: bytes) -> GeminiExtraction:
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    client = genai.Client(api_key=settings.gemini_api_key)

    prompt = """
Analyze this industrial product PDF.

Extract:
- brand
- model
- product name
- category
- description
- technical specifications
- evidence for important extracted fields

Return only JSON matching the requested schema.

Specifications must be a list of objects with:
- key
- value

Evidence must be a list of objects with:
- field_name
- value
- page, when available
- source_url, when available

Do not invent values. Use null or an empty list when information is unavailable.
"""

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=[
            types.Part.from_bytes(
                data=pdf_bytes,
                mime_type="application/pdf",
            ),
            prompt,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=GeminiExtraction,
        ),
    )

    return GeminiExtraction.model_validate_json(response.text)