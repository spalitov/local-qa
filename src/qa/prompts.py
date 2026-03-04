from __future__ import annotations
from typing import Any, Dict
import json

def build_llm_only_prompt(payload: Dict[str, Any]) -> str:
    schema = {
        "understandable": 0,
        "preferred_tone_followed": 0,
        "empathy": 0,
        "personalization": 0,
        "finding": "one sentence"
    }

    return f"""
You are grading ONLY these categories for the audited agent message:
- understandable
- preferred_tone_followed
- empathy
- personalization

Return ONLY valid JSON matching exactly:
{json.dumps(schema, ensure_ascii=False)}

Rules:
- Every score must be 0 or 1.
- finding must be exactly one sentence summarizing the most important issues (or why it passes).
- Use tone_rules.json only for preferred_tone_followed.
- Use empathy_rules.json only for empathy, based on the prior customer message context.
- Use personalization_rules.json only for personalization, based on the conversation context.
- Consider blocklisted_words: if the audited agent message contains any, set ALL four scores to 0 and mention it in finding.
- Do not grade grammar/typos/repetition; those are handled locally.

Inputs (JSON):
{json.dumps(payload, ensure_ascii=False)}
""".strip()
