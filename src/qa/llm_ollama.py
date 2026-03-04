from __future__ import annotations
from typing import Any, Dict
import json
import requests

class OllamaClient:
    def __init__(self, base_url: str, model: str, temperature: float = 0.0, timeout_s: int = 180):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout_s = timeout_s

    def generate_json(self, prompt: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": self.temperature},
            "format": "json",
        }
        r = requests.post(url, json=payload, timeout=self.timeout_s)
        r.raise_for_status()
        data = r.json()
        resp = data.get("response", "")
        if isinstance(resp, dict):
            return resp
        return json.loads(resp)
