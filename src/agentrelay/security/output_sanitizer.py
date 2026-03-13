"""Output sanitizer — detect malicious commands and payloads in agent output."""

from __future__ import annotations

import base64
import re

from .task_sanitizer import SanitizeResult, ThreatLevel

# --- Dangerous shell command patterns ---

_SHELL_COMMAND_PATTERNS = [
    re.compile(r"\brm\s+-[rR]?f\b"),
    re.compile(r"\brm\s+--no-preserve-root\b"),
    re.compile(r"\bdel\s+/[sS]\b"),
    re.compile(r"\bformat\s+[a-zA-Z]:"),
    re.compile(r"\bmkfs\b"),
    re.compile(r"\bdd\s+if=.*of=/dev/\b"),
    re.compile(r">\s*/dev/sd[a-z]"),
    re.compile(r"\b(?:shutdown|reboot|halt|poweroff)\s"),
    re.compile(r"\bchmod\s+777\s+/"),
    re.compile(r"\b(?:curl|wget)\s+.*\|\s*(?:bash|sh|zsh)\b"),
]

# --- Script / HTML injection ---

_SCRIPT_PATTERNS = [
    re.compile(r"<\s*script\b", re.IGNORECASE),
    re.compile(r"\bon\w+\s*=\s*[\"']", re.IGNORECASE),  # onclick= etc
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"<\s*iframe\b", re.IGNORECASE),
]

# --- Base64 encoded payloads ---

_BASE64_PAYLOAD = re.compile(r"[A-Za-z0-9+/]{40,}={0,2}")

# --- Suspicious URL patterns ---

_URL_INJECTION_PATTERNS = [
    re.compile(r"https?://(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?/", re.IGNORECASE),  # raw IP URLs
    re.compile(r"https?://.*@", re.IGNORECASE),  # credential-embedded URLs
    re.compile(r"data:(?:text|application)/[^;]+;base64,", re.IGNORECASE),  # data URIs
]

_ALL_OUTPUT_PATTERNS: list[tuple[str, list[re.Pattern]]] = [
    ("shell_command", _SHELL_COMMAND_PATTERNS),
    ("script_injection", _SCRIPT_PATTERNS),
    ("url_injection", _URL_INJECTION_PATTERNS),
]


def _has_suspicious_base64(text: str) -> bool:
    """Check if text contains base64-encoded payloads that decode to executable content."""
    for match in _BASE64_PAYLOAD.finditer(text):
        candidate = match.group()
        try:
            decoded = base64.b64decode(candidate, validate=True).decode("utf-8", errors="ignore")
        except Exception:
            continue
        # Check if decoded content looks like a command or script
        if any(kw in decoded.lower() for kw in ("rm ", "del ", "exec", "<script", "import os", "subprocess", "eval(")):
            return True
    return False


def scan_output(text: str) -> SanitizeResult:
    """Scan agent output for malicious commands and payloads.

    Returns a SanitizeResult indicating whether the output is safe,
    suspicious, or should be blocked.
    """
    if not text or not text.strip():
        return SanitizeResult(clean=True, threat_level=ThreatLevel.SAFE, sanitized_text=text)

    flagged: list[str] = []

    for category, patterns in _ALL_OUTPUT_PATTERNS:
        for pattern in patterns:
            if pattern.search(text):
                flagged.append(category)
                break

    if _has_suspicious_base64(text):
        flagged.append("base64_payload")

    if not flagged:
        return SanitizeResult(clean=True, threat_level=ThreatLevel.SAFE, sanitized_text=text)

    threat = ThreatLevel.BLOCKED if len(flagged) >= 2 else ThreatLevel.SUSPICIOUS
    return SanitizeResult(
        clean=False,
        threat_level=threat,
        flagged_patterns=flagged,
        sanitized_text=text,
    )
