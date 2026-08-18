from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class ProductCreate(BaseModel):
    brand: str = Field(min_length=1, max_length=200)
    model: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=300)
    category: str | None = Field(default=None, max_length=200)
    description: str | None = None
    specifications: dict[str, Any] = Field(default_factory=dict)
    source_urls: list[HttpUrl] = Field(default_factory=list)