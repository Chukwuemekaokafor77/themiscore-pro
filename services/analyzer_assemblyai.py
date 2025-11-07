import os
import json
import time
import requests
from typing import Any, Dict, Optional

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
LEMUR_URL = "https://api.assemblyai.com/lemur/v3/generate"

PROMPT = (
    "You are a legal intake classifier. Read the given client narrative and extract structured fields. "
    "Return ONLY strict JSON with the following schema keys: "
    "category (string), urgency (Low|Medium|High), key_facts (object), dates (object), parties (object), "
    "suggested_actions (array of strings), checklists (object of string[]), department (string|optional), confidence (number 0-1|optional)."
)

SCHEMA_HINT = {
    "category": "",
    "urgency": "Low",
    "key_facts": {},
    "dates": {},
    "parties": {},
    "suggested_actions": [],
    "checklists": {},
    "department": None,
    "confidence": 0.7,
}

HEADERS = {"authorization": ASSEMBLYAI_API_KEY or "", "content-type": "application/json"}

class AAIAnalyzerError(Exception):
    pass


def _post_with_retry(url: str, payload: Dict[str, Any], retries: int = 2, timeout: int = 20) -> requests.Response:
    last = None
    for i in range(retries + 1):
        try:
            return requests.post(url, headers=HEADERS, data=json.dumps(payload), timeout=timeout)
        except Exception as e:
            last = e
            time.sleep(min(2 ** i, 8))
    raise AAIAnalyzerError(str(last) if last else "request failed")


def analyze_with_aai(text: str) -> Dict[str, Any]:
    if not ASSEMBLYAI_API_KEY:
        raise AAIAnalyzerError("ASSEMBLYAI_API_KEY not set")
    prompt = f"{PROMPT}\n\nText:\n{text}\n\nReturn JSON only."
    payload = {
        "model": "lemur-3-sonar-large-32k-online",
        "input": prompt,
        "max_output_tokens": 800,
        "format": "json",
    }
    res = _post_with_retry(LEMUR_URL, payload)
    if res.status_code != 200:
        raise AAIAnalyzerError(f"LeMUR error: {res.status_code} {res.text[:200]}")
    try:
        data = res.json()
    except Exception:
        raise AAIAnalyzerError("Invalid JSON from LeMUR")
    # Some responses wrap JSON in a field; attempt to unwrap
    if isinstance(data, dict) and "response" in data and isinstance(data["response"], (dict, list, str)):
        candidate = data["response"]
        if isinstance(candidate, str):
            try:
                candidate = json.loads(candidate)
            except Exception:
                raise AAIAnalyzerError("LeMUR response not JSON")
        data = candidate
    if not isinstance(data, dict):
        raise AAIAnalyzerError("LeMUR response malformed")
    # Normalize keys & defaults
    out: Dict[str, Any] = {**SCHEMA_HINT}
    out.update(data)
    # Coerce types
    urg = str(out.get("urgency") or "").strip().lower()
    if urg in ("high",):
        out["urgency"] = "High"
    elif urg in ("medium", "med", "mid"):
        out["urgency"] = "Medium"
    elif urg in ("low",):
        out["urgency"] = "Low"
    else:
        out["urgency"] = "Medium"
    try:
        conf = float(out.get("confidence"))
        out["confidence"] = max(0.0, min(1.0, conf))
    except Exception:
        out["confidence"] = 0.7
    # Ensure shapes
    out["key_facts"] = out.get("key_facts") or {}
    out["dates"] = out.get("dates") or {}
    out["parties"] = out.get("parties") or {}
    out["suggested_actions"] = out.get("suggested_actions") or []
    out["checklists"] = out.get("checklists") or {}
    return out
