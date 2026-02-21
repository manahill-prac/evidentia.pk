
import base64
import json
import os
from groq import Groq


# =============================
# CONFIG
# =============================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client  = Groq(api_key=GROQ_API_KEY)

# Model used for Stage 1 (Vision) —
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# Model used for Stage 2 (JSON structuring) — same as before
STRUCTURING_MODEL = "llama-3.1-8b-instant"


# =============================
# INTERNAL HELPERS
# =============================

def _encode_image(file_bytes: bytes) -> str:
    """Convert raw bytes to base64 string for Groq Vision API."""
    return base64.b64encode(file_bytes).decode("utf-8")


def _detect_mime_type(file_bytes: bytes) -> str:
    """
    Detect image MIME type from file magic bytes.
    Groq Vision needs the correct media type in the data URL.
    """
    if file_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return "image/png"
    elif file_bytes[:3] == b'\xff\xd8\xff':
        return "image/jpeg"
    elif file_bytes[:6] in (b'GIF87a', b'GIF89a'):
        return "image/gif"
    elif file_bytes[:4] == b'RIFF' and file_bytes[8:12] == b'WEBP':
        return "image/webp"
    else:
        return "image/jpeg"  # Safe default


def _build_vision_prompt() -> str:
    """
    System prompt for Stage 1 — neutral forensic observer.
    Kept identical in spirit to the original moondream prompt.
    """
    return """You are a neutral forensic visual analyst assisting in legal documentation.

Your task: Describe ONLY what is directly observable in this image.

STRICT RULES:
- Describe ONLY observable facts. No speculation.
- Do NOT guess or infer identities of any person.
- Do NOT assume intent or cause.
- If something is unclear or not visible, say: "Not clearly visible"
- Describe people by clothing, position, and visible actions ONLY.
- Note any visible damage, injuries, objects, vehicles, or environmental details.
- Include visible text, signs, or location clues if present.

Provide a single detailed paragraph. Be precise and factual."""


def _build_structuring_prompt(description: str) -> str:
    """
    Stage 2 prompt — same as original, converts description to strict JSON.
    """
    return f"""You are a legal forensic analyst.

Convert the following scene description into STRICT JSON.

Rules:
- No speculation
- No extra keys
- If unclear → "Not clearly visible"
- Choose ONE incident_type from:
    Physical assault | Theft | Traffic accident | Property damage | Harassment | Unknown
- "objects_observed" MUST be a simple list of short object names as STRINGS only.
    Example: ["Knife", "Car", "Broken window"]
- Do NOT create nested objects inside "objects_observed".

Return ONLY valid JSON.
Do NOT include explanations, markdown, or code blocks.

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
\"\"\"{description}\"\"\""""


# =============================
# STAGE 1 — GROQ VISION
# (replaces _call_moondream)
# =============================

def _call_groq_vision(file_bytes: bytes) -> str:
    """
    Stage 1: Get natural language description using Groq Llama 3.2 Vision.

    This replaces _call_moondream() from the original.
    Uses the same Groq API key — no new credentials needed.

    Args:
        file_bytes: Raw image bytes (JPG, PNG, WEBP, GIF)

    Returns:
        Natural language scene description string
    """
    base64_image = _encode_image(file_bytes)
    mime_type    = _detect_mime_type(file_bytes)
    data_url     = f"data:{mime_type};base64,{base64_image}"

    response = groq_client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": _build_vision_prompt()
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": data_url
                        }
                    }
                ]
            }
        ],
        temperature=0.2,
        max_tokens=800
    )

    return response.choices[0].message.content


# =============================
# STAGE 2 — GROQ STRUCTURER
# =============================

def _call_groq_structurer(description: str) -> str:
    """
    Stage 2: Convert description → strict JSON using Groq LLM.
    Identical to original implementation.
    """
    response = groq_client.chat.completions.create(
        model=STRUCTURING_MODEL,
        messages=[
            {"role": "user", "content": _build_structuring_prompt(description)}
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content


# =============================
# JSON PARSING & VALIDATION
# (unchanged from original)
# =============================

def _safe_json_parse(raw_output: str) -> dict:
    """
    Safely parse JSON output from LLM.
    Handles markdown code blocks and partial JSON gracefully.
    """
    # Strip markdown code fences if present
    cleaned = raw_output.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        try:
            start = cleaned.index("{")
            end   = cleaned.rindex("}") + 1
            return json.loads(cleaned[start:end])
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
    """
    Ensure all required keys exist with correct types.
    Identical to original implementation.
    """
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

        # Ensure objects_observed is a list of STRINGS only
    if not isinstance(data.get("objects_observed"), list):
        data["objects_observed"] = []
    else:
        cleaned_objects = []
        for obj in data["objects_observed"]:
            if isinstance(obj, str):
                cleaned_objects.append(obj)
            elif isinstance(obj, dict) and "description" in obj:
                cleaned_objects.append(str(obj["description"]))
        data["objects_observed"] = cleaned_objects

    return data


# =============================
# PUBLIC API (DO NOT CHANGE)
# =============================

def analyze_image(file_bytes: bytes) -> dict:
    """
    Analyze an evidence image and return structured forensic data.

    Input:
        file_bytes : Raw image bytes (JPG, PNG, WEBP supported)

    Output:
        Dictionary matching Vision JSON schema exactly:
        {
            "incident_type"           : str,
            "summary"                 : str,
            "people_observed"         : [{"description": str, "visible_actions": str}],
            "objects_observed"        : [str],
            "visible_damage_or_injury": str,
            "location_clues"          : str,
            "confidence_level"        : str
        }

    This output is consumed by:
        - rag.generate_fir(vision_json)
        - pdf_generator.create_pdf(..., vision_data, ...)
    """

    # Stage 1: Vision description via Groq Vision (replaces moondream)
    description = _call_groq_vision(file_bytes)

    # Stage 2: Structured JSON extraction via Groq LLM (unchanged)
    structured_output = _call_groq_structurer(description)

    # Parse and validate
    parsed    = _safe_json_parse(structured_output)
    validated = _validate_schema(parsed)

    return validated


# =============================
# LOCAL TEST BLOCK
# =============================

if __name__ == "__main__":
    """
    Quick test — place any test image as 'test_image.jpg' in same folder.
    Run: python vision.py
    """
    import sys

    test_image_path = "test_image.jpg"

    if not os.path.exists(test_image_path):
        print(f" Place a test image at '{test_image_path}' and run again.")
        sys.exit(1)

    print(" Running vision analysis...\n")

    with open(test_image_path, "rb") as f:
        image_bytes = f.read()

    result = analyze_image(image_bytes)

    print(" Vision Analysis Result:")
    print("=" * 50)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("=" * 50)
    print(f"\nIncident Type : {result['incident_type']}")
    print(f"Confidence    : {result['confidence_level']}")
    print(f"Summary       : {result['summary'][:120]}...")
