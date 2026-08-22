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
        return {}

    client = genai.Client(api_key=settings.gemini_api_key)

    prompt = f"""
You are an industrial product data enrichment system.

Convert this source product row into structured catalog fields.
Only return a valid JSON object.
Do not invent uncertain values.
Use empty strings for unavailable values.

Source row:
{json.dumps(input_row, ensure_ascii=False)}
"""

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    try:
        result = json.loads(response.text)
    except json.JSONDecodeError:
        return {}

    return result if isinstance(result, dict) else {}


def process_dataset(input_bytes: bytes) -> bytes:
    input_text = input_bytes.decode("utf-8-sig")
    input_reader = csv.DictReader(io.StringIO(input_text))
    expected_headers = load_expected_headers()

    output_rows = []

    for input_row in input_reader:
        enriched_values = enrich_row(input_row)

        output_row = {
            header: enriched_values.get(header, "")
            for header in expected_headers
        }

        # Preserve original source values.
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