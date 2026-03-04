from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from .schema import AuditInput, Message

_ROLE_MAP = {
    "system": "system",
    "customer": "customer",
    "agent": "agent",
}

_TONE_MAP = {
    "polished": "polished",
    "casual": "casual",
    "formal": "formal",
}


def _normalize_tone(value: Any) -> str:
    tone = str(value or "").strip().lower()
    if tone not in _TONE_MAP:
        raise ValueError(
            f"Unsupported tone '{value}'. Expected one of: polished, casual, formal."
        )
    return _TONE_MAP[tone]


def _parse_json_list(raw: Any, field_name: str) -> List[Any]:
    text = str(raw or "").strip()
    if not text:
        return []
    if text.startswith("["):
        parsed = json.loads(text)
        if not isinstance(parsed, list):
            raise ValueError(f"{field_name} must be a JSON array.")
        return parsed
    return [text]


def _parse_blocklisted_words(raw: Any) -> List[str]:
    text = str(raw or "").strip()
    if not text:
        return []

    if text.startswith("["):
        items = _parse_json_list(text, "BLOCKLISTED_WORDS")
    else:
        items = [part.strip() for part in text.split(",")]

    out: List[str] = []
    for item in items:
        s = str(item).strip()
        if s:
            out.append(s)
    return out


def _parse_conversation(raw: Any) -> List[Message]:
    items = _parse_json_list(raw, "CONVERSATION_JSON")
    messages: List[Message] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"Conversation item at index {idx} is not an object.")
        role_raw = str(item.get("message_type", "")).strip().lower()
        text = str(item.get("message_text", "")).strip()
        if not role_raw or role_raw not in _ROLE_MAP:
            continue
        if not text:
            continue
        messages.append(
            Message(
                role=_ROLE_MAP[role_raw],  # type: ignore[arg-type]
                text=text,
                timestamp=item.get("date_time"),
            )
        )
    if not messages:
        raise ValueError("CONVERSATION_JSON did not produce any valid messages.")
    return messages


def csv_row_to_audit_input(row: Dict[str, Any], row_num: int) -> AuditInput:
    send_id = str(row.get("SEND_ID", "")).strip()
    if not send_id:
        raise ValueError(f"CSV row {row_num}: missing SEND_ID.")

    return AuditInput(
        id=send_id,
        preferred_tone=_normalize_tone(row.get("MESSAGE_TONE")),  # type: ignore[arg-type]
        blocklisted_words=_parse_blocklisted_words(row.get("BLOCKLISTED_WORDS")),
        conversation=_parse_conversation(row.get("CONVERSATION_JSON")),
    )


def load_audit_input(path: Path, row_num: int = 1, send_id: str | None = None) -> AuditInput:
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return AuditInput(**data)

    if suffix != ".csv":
        raise ValueError(f"Unsupported input file type: {path.suffix}. Use .json or .csv.")

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row.")

        selected: Dict[str, Any] | None = None
        selected_row_num = row_num

        if send_id:
            for i, row in enumerate(reader, start=1):
                if str(row.get("SEND_ID", "")).strip() == send_id:
                    selected = row
                    selected_row_num = i
                    break
            if selected is None:
                raise ValueError(f"SEND_ID '{send_id}' was not found in CSV.")
        else:
            if row_num < 1:
                raise ValueError("CSV row number must be >= 1.")
            for i, row in enumerate(reader, start=1):
                if i == row_num:
                    selected = row
                    break
            if selected is None:
                raise ValueError(f"CSV row {row_num} not found.")

    return csv_row_to_audit_input(selected, selected_row_num)
