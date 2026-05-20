"""
Merchant detection mit Variant-Resolution.

Zwei-Stufen-Prozess:
1. Detect base profile by scoring header_patterns of all bases
2. Select most-specific variant of the winning base whose applies_to conditions match
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .profile import Profile, ProfileBundle


@dataclass
class DetectionResult:
    profile: Profile | None
    score: float
    candidates: list[tuple[str, float]] = field(default_factory=list)
    variant_selected: Profile | None = None
    variant_match_count: int = 0


def _score_base(text: str, profile: Profile) -> float:
    score = 0.0
    for pattern, confidence in profile.detection_patterns:
        if pattern.search(text):
            score += confidence
    return score


def _variant_matches(text: str, variant: Profile) -> tuple[bool, int]:
    """
    Returns (matches, condition_count). Returns (False, 0) if any condition fails.
    """
    at = variant.applies_to
    if at is None:
        return False, 0

    # Each condition that's set MUST match.
    if at.zip_regex is not None and not at.zip_regex.search(text):
        return False, 0
    if at.uid_regex is not None and not at.uid_regex.search(text):
        return False, 0
    if at.header_marker_regex is not None and not at.header_marker_regex.search(text):
        return False, 0
    if at.store_id_regex is not None and not at.store_id_regex.search(text):
        return False, 0
    if at.cities:
        # any city-name appears in text
        if not any(c in text for c in at.cities):
            return False, 0

    # valid_from / valid_until — purchase_date check would need to come from parser.
    # For variant SELECTION at detect-time, we cannot enforce date constraints yet.
    # We mark them as part of condition_count but don't reject here.

    return True, at.condition_count


def detect_merchant(text: str,
                    bundles: dict[str, ProfileBundle]) -> DetectionResult:
    """
    1. Score all base profiles, pick winner if score >= minimum.
    2. Among winner's variants, pick the most-specific one whose applies_to matches.
    3. Return base if no variant matches, otherwise the resolved variant.
    """
    candidates: list[tuple[str, float]] = []
    for merchant_id, bundle in bundles.items():
        score = _score_base(text, bundle.base)
        candidates.append((merchant_id, score))

    candidates.sort(key=lambda x: x[1], reverse=True)

    if not candidates:
        return DetectionResult(profile=None, score=0.0, candidates=[])

    best_id, best_score = candidates[0]
    best_bundle = bundles[best_id]

    if best_score < best_bundle.base.detection_minimum_score:
        return DetectionResult(profile=None, score=best_score, candidates=candidates)

    # Resolve variant
    best_variant: Profile | None = None
    best_variant_specificity = 0
    for variant in best_bundle.variants:
        matches, specificity = _variant_matches(text, variant)
        if matches and specificity > best_variant_specificity:
            best_variant = variant
            best_variant_specificity = specificity

    selected = best_variant if best_variant is not None else best_bundle.base

    return DetectionResult(
        profile=selected,
        score=best_score,
        candidates=candidates,
        variant_selected=best_variant,
        variant_match_count=best_variant_specificity,
    )
