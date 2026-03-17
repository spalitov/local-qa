from __future__ import annotations
from typing import Any, Dict
import json
import re

import requests


def _extract_first_balanced_json_object(text: str) -> str:
    start = text.find("{")
    if start < 0:
        return ""

    depth = 0
    in_string = False
    escaped = False

    for i in range(start, len(text)):
        ch = text[i]

        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    return ""


def _parse_ollama_json_response(resp: Any) -> Dict[str, Any]:
    if isinstance(resp, dict):
        return resp

    text = str(resp or "").strip()
    if not text:
        raise ValueError("Ollama returned an empty response.")

    candidates: list[str] = [text]

    fenced = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    for block in fenced:
        block = block.strip()
        if block:
            candidates.append(block)

    balanced = _extract_first_balanced_json_object(text)
    if balanced:
        candidates.append(balanced)

    # Minor recovery for trailing commas before '}' or ']'.
    repaired: list[str] = []
    for candidate in candidates:
        fixed = re.sub(r",\s*([}\]])", r"\1", candidate)
        if fixed != candidate:
            repaired.append(fixed)
    candidates.extend(repaired)

    seen: set[str] = set()
    first_error: Exception | None = None
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
            first_error = ValueError(f"Expected JSON object, got: {type(parsed).__name__}")
        except Exception as exc:
            if first_error is None:
                first_error = exc

    preview = text[:300].replace("\n", "\\n")
    if first_error is None:
        raise ValueError(f"Ollama returned invalid JSON. Response preview: {preview}")
    raise ValueError(
        f"Ollama returned invalid JSON: {first_error}. Response preview: {preview}"
    )


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        temperature: float = 0.0,
        timeout_s: int = 180,
        keep_alive: str | int | None = None,
        options: Dict[str, Any] | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout_s = timeout_s
        self.keep_alive = keep_alive
        self.options = dict(options or {})

    def _generate(self, prompt: str, as_json: bool = True) -> Any:
        url = f"{self.base_url}/api/generate"
        payload_options = dict(self.options)
        if "temperature" not in payload_options:
            payload_options["temperature"] = self.temperature

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": payload_options,
        }
        if self.keep_alive is not None and str(self.keep_alive).strip():
            payload["keep_alive"] = self.keep_alive
        if as_json:
            payload["format"] = "json"

        r = requests.post(url, json=payload, timeout=self.timeout_s)
        r.raise_for_status()
        data = r.json()
        return data.get("response", "")

    def generate_json(self, prompt: str) -> Dict[str, Any]:
        resp = self._generate(prompt, as_json=True)
        try:
            return _parse_ollama_json_response(resp)
        except Exception:
            # One-shot repair pass for occasionally malformed JSON.
            repair_prompt = (
                "Rewrite the text below as VALID JSON only. "
                "Return exactly one JSON object with keys: "
                "understandable, preferred_tone_followed, empathy, personalization, finding. "
                "The first four keys must be integers 0 or 1. "
                "The finding key must be one concise sentence.\n\n"
                f"TEXT:\n{str(resp)}"
            )
            repaired = self._generate(repair_prompt, as_json=True)
            return _parse_ollama_json_response(repaired)
