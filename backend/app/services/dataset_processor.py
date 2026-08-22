import csv
import io
import json
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from ..config import settings


EXPECTED_HEADERS_FILE = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "raw"
    / "expected_output_headers.csv"
)


def load_expected_headers() -> list[str]:
    with EXPECTED_HEADERS_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return next(csv.reader(file))


def enrich_row(input_row: dict[str, Any]) -> dict[str, Any]:
    if not settings.gemini_api_key:
        print("Gemini API key is missing.")
        return {}

    client = genai.Client(api_key=settings.gemini_api_key)

    prompt = f"""
You are an industrial product data enrichment system.

Convert this source product row into structured catalog fields.

Return only a valid JSON object using these keys:
- brand
- model
- name
- category
- description
- specifications

The specifications value must be a JSON object of key-value pairs.

Do not invent uncertain values.
Use empty strings or an empty object when unavailable.

Source product row:
{json.dumps(input_row, ensure_ascii=False)}
"""

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    raw_text = response.text.strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.replace("```json", "")
        raw_text = raw_text.replace("```", "")
        raw_text = raw_text.strip()

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        print("Could not parse Gemini response:", raw_text)
        return {}

    print("Parsed enrichment:", result)

    return result if isinstance(result, dict) else {}


def map_enriched_fields(
    output_row: dict[str, Any],
    enriched: dict[str, Any],
) -> None:
    output_row["BRAND_NAME"] = (
        output_row["BRAND_NAME"]
        or enriched.get("brand", "")
    )

    output_row["MANUFACTURER_PART_NUMBER"] = (
        output_row["MANUFACTURER_PART_NUMBER"]
        or enriched.get("model", "")
    )

    output_row["Product Name"] = (
        output_row["Product Name"]
        or enriched.get("name", "")
    )

    output_row["Classpath"] = (
        output_row["Classpath"]
        or enriched.get("category", "")
    )

    output_row["LONG_DESC1"] = (
        output_row["LONG_DESC1"]
        or enriched.get("description", "")
    )

    specifications = enriched.get("specifications", {})

    if isinstance(specifications, dict):
        for index, (key, value) in enumerate(
            specifications.items(),
            start=1,
        ):
            if index > 50:
                break

            output_row[f"ATTRIBUTE_LABEL {index}"] = str(key)
            output_row[f"ATTRIBUTE_VALUE {index}"] = str(value)


def process_dataset(input_bytes: bytes) -> bytes:
    input_text = input_bytes.decode("utf-8-sig")
    input_reader = csv.DictReader(io.StringIO(input_text))
    expected_headers = load_expected_headers()

    output_rows = []

    for input_row in input_reader:
        enriched_values = enrich_row(input_row)

        output_row = {
            header: input_row.get(header, "")
            for header in expected_headers
        }

        map_enriched_fields(output_row, enriched_values)

        output_row["PART_NUMBER"] = (
            output_row["PART_NUMBER"]
            or input_row.get("Mfg_Part_Num", "")
        )

        output_row["MANUFACTURER_PART_NUMBER"] = (
            output_row["MANUFACTURER_PART_NUMBER"]
            or input_row.get("Mfg_Part_Num", "")
        )

        output_row["Part_Desc"] = (
            output_row["Part_Desc"]
            or input_row.get("Part_Desc", "")
        )

        output_row["BRAND_NAME"] = (
            output_row["BRAND_NAME"]
            or input_row.get("E1_Brand", "")
        )

        output_row["MANUFACTURER_NAME"] = (
            output_row["MANUFACTURER_NAME"]
            or input_row.get("Part_Manuf", "")
        )

        output_rows.append(output_row)

    output_buffer = io.StringIO(newline="")

    writer = csv.DictWriter(
        output_buffer,
        fieldnames=expected_headers,
        extrasaction="ignore",
    )

    writer.writeheader()
    writer.writerows(output_rows)

    return output_buffer.getvalue().encode("utf-8-sig")