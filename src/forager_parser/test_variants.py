"""
Test variant detection and resolution.
"""
from pathlib import Path

from forager_parser.detector import detect_merchant
from forager_parser.profile import load_all_profiles

REPO_ROOT = Path(__file__).resolve().parents[2]
MERCHANTS_DIR = REPO_ROOT / "merchants"


def test_variant_selected_for_ohg_bon():
    """Hamburg-Überseequartier-Bon (REWE Jens Piclum oHG) → must resolve to variant."""
    bundles = load_all_profiles(MERCHANTS_DIR)
    text = (MERCHANTS_DIR / "de/rewe/samples/2026-03-21-hamburg-ueberseequartier.txt").read_text()
    result = detect_merchant(text, bundles)
    assert result.profile is not None
    assert result.profile.merchant_id == "de.rewe"
    assert result.profile.is_variant
    assert result.profile.variant_id == "de.rewe.ohg-piclum"
    assert result.variant_match_count == 2  # uid + header_marker matched


def test_base_selected_for_regular_rewe_bon():
    """Maschen-Bon (REWE Markt GmbH, normale UID) → must stay on base."""
    bundles = load_all_profiles(MERCHANTS_DIR)
    text = (MERCHANTS_DIR / "de/rewe/samples/2026-05-20-maschen.txt").read_text()
    result = detect_merchant(text, bundles)
    assert result.profile is not None
    assert result.profile.merchant_id == "de.rewe"
    assert not result.profile.is_variant
    assert result.variant_selected is None


def test_brand_variant_inherited_correctly():
    """Variant inherits all base fields but adds its own brand_variants."""
    bundles = load_all_profiles(MERCHANTS_DIR)
    bundle = bundles["de.rewe"]

    base = bundle.base
    assert "REWE Markt" in base.brand_variants
    assert len(bundle.variants) == 1
    variant = bundle.variants[0]

    # Variant inherits item_patterns from base
    assert len(variant.item_patterns) == len(base.item_patterns)
    # Variant has its own brand_variants
    assert "REWE Jens Piclum oHG" in variant.brand_variants


def test_other_merchants_have_no_variants():
    """dm, lidl, knolles haben aktuell keine Variants."""
    bundles = load_all_profiles(MERCHANTS_DIR)
    for mid in ("de.dm", "de.lidl", "de.knolles-markt"):
        assert len(bundles[mid].variants) == 0
