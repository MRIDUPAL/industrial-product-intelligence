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

def validate_output(
    output_rows: list[dict[str, Any]],
    expected_headers: list[str],
    input_row_count: int,
) -> None:
    if len(expected_headers) != 252:
        raise ValueError(
            f"Expected 252 output headers, found {len(expected_headers)}."
        )

    if len(output_rows) != input_row_count:
        raise ValueError(
            "Output row count does not match input row count."
        )

    for index, row in enumerate(output_rows, start=1):
        missing_headers = [
            header for header in expected_headers if header not in row
        ]

        if missing_headers:
            raise ValueError(
                f"Row {index} is missing required output headers."
            )

def clean_json_response(text: str) -> str:
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "")
        cleaned = cleaned.replace("```", "")
        cleaned = cleaned.strip()

    return cleaned


def enrich_rows(
    input_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not settings.gemini_api_key:
        print("Gemini API key is missing.")
        return [{} for _ in input_rows]

    client = genai.Client(api_key=settings.gemini_api_key)

    prompt = f"""
You are an industrial product data enrichment system.

Process every product row below.

Return only a valid JSON array.
Return exactly one object for each input row, in the same order.

Each object must contain:
- brand
- model
- name
- category
- description
- specifications

The specifications value must be a JSON object of key-value pairs.

Do not invent uncertain values.
Use empty strings or an empty object when unavailable.

Input rows:
{json.dumps(input_rows, ensure_ascii=False)}
"""

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    raw_text = clean_json_response(response.text)

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        print("Could not parse batch response:", raw_text)
        return [{} for _ in input_rows]

    if not isinstance(result, list):
        return [{} for _ in input_rows]

    print(f"Enriched {len(result)} rows in one Gemini request.")

    return [
        item if isinstance(item, dict) else {}
        for item in result
    ]


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
    
    input_headers = input_reader.fieldnames or []
    validate_input_headers(input_headers)

    input_rows = list(input_reader)
    expected_headers = load_expected_headers()
    enriched_rows = enrich_rows(input_rows)

    output_rows = []

    for input_row, enriched_values in zip(
        input_rows,
        enriched_rows,
    ):
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

    validate_output(
        output_rows,
        expected_headers,
        len(input_rows),
    )

    output_buffer = io.StringIO(newline="")

    writer = csv.DictWriter(
        output_buffer,
        fieldnames=expected_headers,
        extrasaction="ignore",
    )

    writer.writeheader()
    writer.writerows(output_rows)

    return output_buffer.getvalue().encode("utf-8-sig")

REQUIRED_INPUT_HEADERS = {
    "Mfg_Part_Num",
    "Part_Desc",
    "E1_Brand",
    "Unilog_Brand",
    "DIB_Brand",
    "Part_Manuf",
}

def validate_input_headers(
    input_headers: list[str],
) -> None:
    missing_headers = REQUIRED_INPUT_HEADERS - set(input_headers)

    if missing_headers:
        missing = ", ".join(sorted(missing_headers))

        raise ValueError(
            f"Invalid input CSV. Missing required columns: {missing}"
        )