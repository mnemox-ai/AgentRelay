"""Input sanitizer — detect prompt injection patterns in task descriptions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class ThreatLevel(Enum):
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    BLOCKED = "blocked"


@dataclass
class SanitizeResult:
    clean: bool
    threat_level: ThreatLevel
    flagged_patterns: list[str] = field(default_factory=list)
    sanitized_text: str = ""


# --- Prompt injection patterns ---

_SYSTEM_OVERRIDE_PATTERNS = [
    re.compile(r"(?:you\s+are|act\s+as|pretend\s+to\s+be)\s+(?:a\s+)?(?:system|admin|root)", re.IGNORECASE),
    re.compile(r"(?:new|override|replace|set)\s+system\s+prompt", re.IGNORECASE),
    re.compile(r"\[SYSTEM\]", re.IGNORECASE),
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
]

_IGNORE_INSTRUCTION_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+(?:instructions?|prompts?|rules?)", re.IGNORECASE),
    re.compile(r"disregard\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+(?:instructions?|prompts?|rules?)", re.IGNORECASE),
    re.compile(r"forget\s+(?:everything|all|your)\s+(?:you\s+were\s+told|instructions?|rules?|prompts?)", re.IGNORECASE),
    re.compile(r"do\s+not\s+follow\s+(?:any|your|the)\s+(?:instructions?|rules?|guidelines?)", re.IGNORECASE),
]

_ROLE_PLAY_PATTERNS = [
    re.compile(r"(?:you\s+are\s+now|from\s+now\s+on\s+you\s+are|switch\s+to)\s+(?:in\s+)?\w+\s+mode", re.IGNORECASE),
    re.compile(r"enter\s+(?:DAN|developer|god|jailbreak|unrestricted)\s+mode", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"DAN\s+mode", re.IGNORECASE),
]

_ENCODED_INSTRUCTION_PATTERNS = [
    re.compile(r"(?:decode|execute|run|eval)\s+(?:the\s+)?(?:following\s+)?base64", re.IGNORECASE),
    re.compile(r"\\x[0-9a-fA-F]{2}(?:\\x[0-9a-fA-F]{2}){3,}"),  # hex escape sequences
    re.compile(r"&#x?[0-9a-fA-F]+;(?:&#x?[0-9a-fA-F]+;){3,}"),  # HTML entities chain
]

_ALL_PATTERNS: list[tuple[str, list[re.Pattern]]] = [
    ("system_prompt_override", _SYSTEM_OVERRIDE_PATTERNS),
    ("ignore_previous_instructions", _IGNORE_INSTRUCTION_PATTERNS),
    ("role_play_attack", _ROLE_PLAY_PATTERNS),
    ("encoded_instructions", _ENCODED_INSTRUCTION_PATTERNS),
]


def scan_input(text: str) -> SanitizeResult:
    """Scan task input for prompt injection patterns.

    Returns a SanitizeResult indicating whether the input is safe,
    suspicious, or should be blocked.
    """
    if not text or not text.strip():
        return SanitizeResult(clean=True, threat_level=ThreatLevel.SAFE, sanitized_text=text)

    flagged: list[str] = []

    for category, patterns in _ALL_PATTERNS:
        for pattern in patterns:
            if pattern.search(text):
                flagged.append(category)
                break  # one match per category is enough

    if not flagged:
        return SanitizeResult(clean=True, threat_level=ThreatLevel.SAFE, sanitized_text=text)

    threat = ThreatLevel.BLOCKED if len(flagged) >= 2 else ThreatLevel.SUSPICIOUS
    return SanitizeResult(
        clean=False,
        threat_level=threat,
        flagged_patterns=flagged,
        sanitized_text=text,
    )
