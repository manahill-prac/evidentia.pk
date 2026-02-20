import base64
import json
import os
import ollama
from groq import Groq


# =============================
# CONFIG
# =============================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)


# =============================
# INTERNAL HELPERS
# =============================

def _encode_image(file_bytes: bytes) -> str:
    return base64.b64encode(file_bytes).decode("utf-8")


def _build_vision_prompt() -> str:
    return """
You are a neutral forensic visual analyst.

Describe ONLY observable facts in this image.
Do NOT speculate.
Do NOT guess identities.
If unclear, say: "Not clearly visible".

Provide a detailed paragraph description.
"""


def _call_moondream(base64_image: str) -> str:
    """
    Stage 1: Get natural language description from moondream.
    """

    response = ollama.chat(
        model="moondream",
        messages=[
            {
                "role": "user",
                "content": _build_vision_prompt(),
                "images": [base64_image],
            }
        ],
        options={
            "temperature": 0.2
        }
    )

    return response["message"]["content"]


def _build_structuring_prompt(description: str) -> str:
    return f"""
You are a legal forensic analyst.

Convert the following scene description into STRICT JSON.

Rules:
- No speculation
- No extra keys
- If unclear → "Not clearly visible"
- Choose ONE incident_type from:
    Physical assault | Theft | Traffic accident | Property damage | Harassment | Unknown

Return ONLY valid JSON.
Do NOT include explanations.

Structure:

{{
    "incident_type": "",
    "summary": "",
    "people_observed": [
    {{
        "description": "",
        "visible_actions": ""
    }}
    ],
    "objects_observed": [],
    "visible_damage_or_injury": "",
    "location_clues": "",
    "confidence_level": ""
}}

Scene description:
\"\"\"{description}\"\"\"
"""


def _call_groq_structurer(description: str) -> str:
    """
    Stage 2: Convert description → strict JSON using Groq LLM
    """

    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "user", "content": _build_structuring_prompt(description)}
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content


def _safe_json_parse(raw_output: str) -> dict:
    try:
        return json.loads(raw_output)
    except json.JSONDecodeError:
        try:
            start = raw_output.index("{")
            end = raw_output.rindex("}") + 1
            cleaned = raw_output[start:end]
            return json.loads(cleaned)
        except Exception:
            return {
                "incident_type": "Unknown",
                "summary": "Not clearly visible.",
                "people_observed": [
                    {
                        "description": "Not clearly visible",
                        "visible_actions": "Not clearly visible"
                    }
                ],
                "objects_observed": [],
                "visible_damage_or_injury": "Not clearly visible",
                "location_clues": "Not clearly visible",
                "confidence_level": "Low"
            }


def _validate_schema(data: dict) -> dict:

    required_keys = {
        "incident_type",
        "summary",
        "people_observed",
        "objects_observed",
        "visible_damage_or_injury",
        "location_clues",
        "confidence_level"
    }

    if not isinstance(data, dict):
        return _safe_json_parse("{}")

    for key in required_keys:
        if key not in data:
            data[key] = "Not clearly visible"

    if not isinstance(data.get("people_observed"), list) or not data["people_observed"]:
        data["people_observed"] = [
            {
                "description": "Not clearly visible",
                "visible_actions": "Not clearly visible"
            }
        ]

    return data


# =============================
# PUBLIC API (DO NOT CHANGE)
# =============================

def analyze_image(file_bytes: bytes) -> dict:
    """
    Input:
        file_bytes (raw image bytes)

    Output:
        Dictionary matching Vision JSON schema exactly.
    """

    base64_image = _encode_image(file_bytes)

    # Stage 1: Vision description
    description = _call_moondream(base64_image)

    # Stage 2: Structured extraction
    structured_output = _call_groq_structurer(description)

    parsed = _safe_json_parse(structured_output)

    validated = _validate_schema(parsed)

    return validated