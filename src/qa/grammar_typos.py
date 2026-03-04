from __future__ import annotations
from typing import Tuple
from functools import lru_cache
import language_tool_python

# Heuristic split:
# - typos = spelling mistakes (MORFOLOGIK rule ids or message containing 'spelling')
# - grammar = everything else
@lru_cache(maxsize=8)
def _get_tool(language: str) -> language_tool_python.LanguageTool:
    return language_tool_python.LanguageTool(language)


def count_grammar_and_typos(text: str, language: str = "en-US") -> Tuple[int, int]:
    tool = _get_tool(language)
    matches = tool.check(text)

    typos = 0
    grammar = 0

    for m in matches:
        rid = (getattr(m, "ruleId", "") or "").upper()
        msg = (getattr(m, "message", "") or "").lower()

        is_typo = False
        if "MORFOLOGIK" in rid:
            is_typo = True
        if "spelling" in msg:
            is_typo = True

        if is_typo:
            typos += 1
        else:
            grammar += 1

    return grammar, typos
