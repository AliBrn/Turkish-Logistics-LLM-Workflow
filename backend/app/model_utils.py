import json
import re
from typing import Any


class ModelOutputParseError(ValueError):
    pass


def strip_think_blocks(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL | re.IGNORECASE)
    return text.strip()


def extract_first_json_object(text: str) -> dict[str, Any]:
    cleaned = strip_think_blocks(text)
    cleaned = cleaned.replace("```json", "```").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    if start < 0:
        raise ModelOutputParseError("Model cevabinda JSON nesnesi bulunamadi.")

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(cleaned)):
        char = cleaned[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                candidate = cleaned[start : index + 1]
                try:
                    parsed = json.loads(candidate)
                except json.JSONDecodeError as exc:
                    raise ModelOutputParseError(f"JSON parse edilemedi: {exc}") from exc
                if not isinstance(parsed, dict):
                    raise ModelOutputParseError("Model JSON cevabi obje degil.")
                return parsed

    raise ModelOutputParseError("Model cevabindaki JSON blogu tamamlanmamis.")


def coerce_model_payload(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        return extract_first_json_object(payload)
    raise ModelOutputParseError(f"Desteklenmeyen model cevabi tipi: {type(payload).__name__}")
