# llm_extract.py
import os, json, time
from typing import Dict, Any
from dotenv import load_dotenv
from openai import AzureOpenAI

# ------------------------
# Load config from .env
# ------------------------
load_dotenv()
AZURE_OPENAI_ENDPOINT   = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")  # e.g. https://eastus.api.cognitive.microsoft.com
AZURE_OPENAI_API_KEY    = os.getenv("AZURE_OPENAI_API_KEY")                   # key from Keys & Endpoint
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5-mini")  # your exact deployment name
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

# Lazily initialize the client to avoid raising at import time
_client = None

def _get_client() -> AzureOpenAI:
    global _client
    if _client is not None:
        return _client
    if not (AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT and AZURE_OPENAI_API_KEY):
        raise RuntimeError("Missing one or more env vars: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT")
    _client = AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
    )
    return _client

# ------------------------
# Strict JSON Schema
# ------------------------
JSON_SCHEMA = {
    "name": "sow_staffing_schema",
    "schema": {
        "type": "object",
        "properties": {
            "blob_name": {"type": "string"},
            "company":   {"type": ["string","null"]},
            "sow_id":    {"type": ["string","null"]},
            "format":    {"type": "string", "enum": ["pdf","docx","txt","unknown"]},
            "term": {
                "type": "object",
                "properties": {
                    "start":    {"type": ["string","null"]},
                    "end":      {"type": ["string","null"]},
                    "months":   {"type": ["number","null"]},
                    "inferred": {"type": "boolean"}
                },
                "required": ["start","end","months","inferred"]
            },
            "scope_bullets": {"type": "array", "items": {"type":"string"}},
            "deliverables":  {"type": "array", "items": {"type":"string"}},
            "units": {
                "type": "object",
                "properties": {
                    "explicit_hours": {"type": ["array","null"], "items":{"type":"number"}},
                    "fte_pct":        {"type": ["array","null"], "items":{"type":"number"}},
                    "fees":           {"type": "array", "items":{"type":"string"}},
                    "rate_table":     {"type": "array", "items":{
                        "type":"object",
                        "properties":{
                            "role":   {"type":["string","null"]},
                            "unit":   {"type":["string","null"], "enum":["hour","day","month","project","unknown"]},
                            "amount": {"type":["number","null"]},
                            "notes":  {"type":["string","null"]}
                        },
                        "required":["role","unit","amount","notes"]
                    }}
                },
                "required": ["explicit_hours","fte_pct","fees","rate_table"]
            },
            "roles_detected": {
                "type":"array",
                "items":{"type":"object","properties":{
                    "title":{"type":"string"},
                    "canonical":{"type":["string","null"]}
                },"required":["title","canonical"]}
            },
            "assumptions": {"type":"array","items":{"type":"string"}},
            "provenance": {
                "type":"object",
                "properties": {
                    "quotes": {"type":"array","items":{"type":"string"}},
                    "sections": {"type":"array","items":{"type":"string"}},
                    "notes": {"type":["string","null"]}
                },
                "required":["quotes","sections","notes"]
            }
        },
        "required": ["blob_name","format","term","scope_bullets","deliverables","units","roles_detected","assumptions","provenance"]
    }
}

SYSTEM_PROMPT = """You are an expert SOW-to-staffing parser. Extract ONLY what is present in the text.
- Do not invent values.
- If uncertain, return null and add a brief reason in provenance.notes.
- Return short bullet strings (not paragraphs).
- For dates, prefer explicit dates; otherwise leave null and set term.inferred=false.
- If fees/rates are in tables, normalize each row into rate_table with role/unit/amount/notes.
- Include 2–5 short supporting quotes in provenance.quotes and brief section/page hints in provenance.sections."""

def llm_parse_schema(blob_name: str, file_format: str, text: str) -> Dict[str, Any]:
    """
    Calls Azure OpenAI Chat Completions with response_format json_schema.
    Returns a dict strictly matching JSON_SCHEMA (plus blob_name/format enforced).
    """
    # Trim text to keep token usage predictable
    doc = text[:60_000]

    user_prompt = f"""Document: {blob_name}
Format: {file_format}

Extract the schema from the following SOW text:

<<<SOW_TEXT_BEGIN>>>
{doc}
<<<SOW_TEXT_END>>>"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_prompt},
    ]

    # Prefer strict schema. If deployment doesn't support json_schema, we fall back to json_object.
    response_format = {"type": "json_schema", "json_schema": JSON_SCHEMA}

    # Retry a couple of times for transient issues
    last_err = None
    for attempt in range(3):
        try:
            resp = _get_client().chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=messages,
                response_format=response_format,
                temperature=1,
            )
            raw = resp.choices[0].message.content
            data = json.loads(raw)
            data["blob_name"] = blob_name
            data["format"] = file_format if file_format in ["pdf","docx","txt"] else "unknown"
            return data
        except Exception as e:
            last_err = e
            # One graceful fallback: try json_object format once
            if attempt == 0:
                try:
                    resp = _get_client().chat.completions.create(
                        model=AZURE_OPENAI_DEPLOYMENT,
                        messages=messages + [
                            {"role":"system","content":"Return ONLY valid JSON matching the schema. No commentary."}
                        ],
                        response_format={"type":"json_object"},
                        temperature=1,
                    )
                    raw = resp.choices[0].message.content
                    data = json.loads(raw)
                    data["blob_name"] = blob_name
                    data["format"] = file_format if file_format in ["pdf","docx","txt"] else "unknown"
                    return data
                except Exception as e2:
                    last_err = e2
            time.sleep(1.0 + attempt * 0.8)

    # If all attempts fail, raise the last error so the caller can log/skip gracefully
    raise last_err
