"""
Claude verification module.

Schickt den Bon-Text + das profil-basierte Parse-Ergebnis an Claude und
fordert eine Bewertung an: was passt, was fehlt, was ist falsch? Optional
auch ein reiner Claude-Parse als Vergleichs-Baseline.

Hinweis: dieser Modul nutzt die Anthropic-API direkt. Im Prototyp ist
die API-Anbindung optional — wenn ANTHROPIC_API_KEY fehlt, gibt es eine
Mock-Antwort, damit Tests offline laufen.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VerificationResult:
    available: bool = False
    reason_unavailable: str | None = None
    agreement_score: float | None = None  # 0.0 - 1.0
    disagreements: list[dict[str, Any]] = field(default_factory=list)
    missed_by_parser: list[dict[str, Any]] = field(default_factory=list)
    missed_by_claude: list[dict[str, Any]] = field(default_factory=list)
    claude_raw_response: str | None = None


def _mock_verification() -> VerificationResult:
    return VerificationResult(
        available=False,
        reason_unavailable="ANTHROPIC_API_KEY not set or anthropic package not installed",
    )


def verify_with_claude(raw_text: str, parser_result: dict[str, Any]) -> VerificationResult:
    """
    Optional: Vergleich gegen Claude. Wenn API nicht verfügbar, gibt das eine
    'unavailable'-Antwort zurück, damit der CLI-Flow weiterläuft.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _mock_verification()

    try:
        import anthropic  # type: ignore[import-not-found]
    except ImportError:
        return VerificationResult(
            available=False,
            reason_unavailable="anthropic package not installed (pip install anthropic)",
        )

    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = (
        "Du bist ein deterministischer Bon-Verifizierer. Du erhältst einen Bon-Text "
        "und ein bestehendes Parse-Ergebnis. Deine Aufgabe: prüfe, ob das Parse-Ergebnis "
        "korrekt ist. Antworte AUSSCHLIESSLICH als JSON mit:\n"
        "{\n"
        '  "agreement_score": <float 0.0-1.0>,\n'
        '  "disagreements": [{"field": "...", "parser_value": "...", "your_value": "...", "reason": "..."}],\n'
        '  "missed_by_parser": [{"raw_text": "...", "kind": "item|pfand|...", "reason": "..."}],\n'
        '  "missed_by_claude": []\n'
        "}\n"
        "Erfinde KEINE Werte. Wenn alles passt: agreement_score=1.0, leere Listen."
    )

    user_prompt = (
        "BON-TEXT:\n```\n" + raw_text + "\n```\n\n"
        "PARSER-ERGEBNIS:\n```json\n" + json.dumps(parser_result, indent=2, default=str)
        + "\n```\n\nBewerte das Ergebnis. Antworte mit JSON, sonst nichts."
    )

    try:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2000,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as exc:
        return VerificationResult(
            available=False,
            reason_unavailable=f"API call failed: {exc}",
        )

    raw = response.content[0].text if response.content else ""

    # JSON aus Antwort extrahieren (manchmal in ```json-Blöcken)
    raw_clean = raw.strip()
    if raw_clean.startswith("```"):
        raw_clean = raw_clean.split("```")[1]
        if raw_clean.startswith("json"):
            raw_clean = raw_clean[4:].strip()

    try:
        parsed = json.loads(raw_clean)
    except json.JSONDecodeError:
        return VerificationResult(
            available=True,
            agreement_score=None,
            claude_raw_response=raw,
            disagreements=[{"field": "_response_parse", "reason": "claude returned non-JSON"}],
        )

    return VerificationResult(
        available=True,
        agreement_score=parsed.get("agreement_score"),
        disagreements=parsed.get("disagreements", []),
        missed_by_parser=parsed.get("missed_by_parser", []),
        missed_by_claude=parsed.get("missed_by_claude", []),
        claude_raw_response=raw,
    )
