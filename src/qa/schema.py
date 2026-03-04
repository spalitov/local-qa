from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

ToneName = Literal["polished", "casual", "formal"]
RoleName = Literal["system", "customer", "agent"]

class Message(BaseModel):
    role: RoleName
    text: str
    timestamp: Optional[str] = None

class AuditInput(BaseModel):
    id: str
    conversation: List[Message]
    preferred_tone: ToneName
    blocklisted_words: List[str] = Field(default_factory=list)

class LocalFindings(BaseModel):
    grammar_error_count: int
    typo_count: int
    repetition_max_cosine: float
    repetition_hit_examples: List[Dict[str, Any]] = Field(default_factory=list)

    # authoritative local 0/1
    correct_grammar: int
    no_typos: int
    no_repetition: int

class LLMFindings(BaseModel):
    # LLM-only 0/1
    understandable: int
    preferred_tone_followed: int
    empathy: int
    personalization: int

    # single sentence covering all categories
    finding: str

class AuditOutput(BaseModel):
    # echoed inputs
    id: str
    preferred_tone: ToneName
    blocklisted_words: List[str]
    conversation: List[Message]

    # derived
    audited_agent_message: str

    # results
    local: LocalFindings
    llm: LLMFindings

    # debug
    llm_raw: Dict[str, Any] = Field(default_factory=dict)
