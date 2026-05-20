"""
Pytest suite that loads parse_test.yaml fixtures and validates parser output.

Pro Testcase prüfen wir:
- Merchant-Identifikation
- Store-Felder (subset)
- Datum/Uhrzeit
- Totals
- Tax-Breakdown (subset)
- Lines: für jede expected line muss eine parsed line existieren, deren Felder
  alle erfüllt sind. Die Reihenfolge muss stimmen. Zusätzliche parsed-Zeilen
  sind erlaubt (Toleranz für Loyalty-Info-Zeilen u.ä.), aber wenn expected
  16 items definiert, müssen mindestens 16 item-line_kind-Zeilen vorkommen.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import yaml

from forager_parser.parser import parse
from forager_parser.profile import load_all_profiles

REPO_ROOT = Path(__file__).resolve().parents[2]
MERCHANTS_DIR = REPO_ROOT / "merchants"


def _find_test_files() -> list[Path]:
    files = []
    for p in MERCHANTS_DIR.rglob("tests/parse_test*.yaml"):
        files.append(p)
    return sorted(files)


def _load_test(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data["_test_path"] = path
    return data


def _resolve_sample(test: dict[str, Any]) -> Path:
    return (test["_test_path"].parent / test["sample"]).resolve()


@pytest.fixture(scope="module")
def bundles():
    return load_all_profiles(MERCHANTS_DIR)


def _find_profile(bundles, profile_id):
    """Find a profile by base merchant_id or variant_id."""
    for mid, bundle in bundles.items():
        if mid == profile_id:
            return bundle.base
        for variant in bundle.variants:
            if variant.variant_id == profile_id:
                return variant
    return None


@pytest.mark.parametrize("test", [_load_test(p) for p in _find_test_files()],
                         ids=lambda t: t["test_id"])
def test_parse_receipt(test, bundles):
    profile_id = test["profile"]
    profile = _find_profile(bundles, profile_id)
    assert profile is not None, f"profile {profile_id} not loaded"

    sample_path = _resolve_sample(test)
    raw_text = sample_path.read_text(encoding="utf-8")

    result = parse(raw_text, profile)
    expected = test["expected"]

    # Merchant
    if "merchant" in expected:
        for key, val in expected["merchant"].items():
            actual = getattr(result.merchant, key)
            assert actual == val, f"merchant.{key}: expected {val!r}, got {actual!r}"

    # Store
    if "store" in expected:
        for key, val in expected["store"].items():
            actual = getattr(result.store, key)
            assert actual == val, f"store.{key}: expected {val!r}, got {actual!r}"

    # Datetime
    if "purchase_datetime" in expected:
        for key, val in expected["purchase_datetime"].items():
            actual = getattr(result.purchase_datetime, key)
            if actual is not None:
                actual_str = actual.isoformat()
                assert actual_str.startswith(val), \
                    f"datetime.{key}: expected starts-with {val!r}, got {actual_str!r}"
            else:
                pytest.fail(f"datetime.{key}: expected {val!r}, got None")

    # Totals
    if "totals" in expected:
        for key, val in expected["totals"].items():
            actual = getattr(result.totals, key)
            if isinstance(val, str) and val.replace(".", "").replace("-", "").isdigit():
                assert actual == Decimal(val), \
                    f"totals.{key}: expected {val!r}, got {actual!r}"
            else:
                assert actual == val, f"totals.{key}: expected {val!r}, got {actual!r}"

    # Payment
    if "payment" in expected:
        for key, val in expected["payment"].items():
            actual = getattr(result.payment, key)
            if isinstance(val, str) and val.replace(".", "").isdigit():
                assert actual == Decimal(val), \
                    f"payment.{key}: expected {val!r}, got {actual!r}"
            else:
                assert actual == val, f"payment.{key}: expected {val!r}, got {actual!r}"

    # Tax breakdown
    if "tax_breakdown" in expected:
        actual_classes = {row.class_code: row for row in result.tax_breakdown}
        for exp_row in expected["tax_breakdown"]:
            cls = exp_row["class_code"]
            assert cls in actual_classes, f"tax_breakdown: class {cls} missing"
            actual_row = actual_classes[cls]
            for key, val in exp_row.items():
                actual = getattr(actual_row, key)
                # class_code ist immer String, rate ist Float, alles andere Decimal
                if key == "class_code":
                    assert actual == val, \
                        f"tax_breakdown[{cls}].{key}: expected {val!r}, got {actual!r}"
                elif key == "rate":
                    assert actual == val, \
                        f"tax_breakdown[{cls}].{key}: expected {val!r}, got {actual!r}"
                elif isinstance(val, str) and val.replace(".", "").isdigit():
                    assert actual == Decimal(val), \
                        f"tax_breakdown[{cls}].{key}: expected {val!r}, got {actual!r}"
                else:
                    assert actual == val, \
                        f"tax_breakdown[{cls}].{key}: expected {val!r}, got {actual!r}"

    # Lines — wir matchen sequenziell, expected lines müssen in dieser
    # Reihenfolge auftauchen, dürfen aber durch andere lines getrennt sein
    if "lines" in expected:
        actual_lines = result.lines
        cursor = 0
        for exp_idx, exp_line in enumerate(expected["lines"]):
            # finde die nächste actual line ab cursor, die alle expected-Felder erfüllt
            matched = False
            for ai in range(cursor, len(actual_lines)):
                actual = actual_lines[ai]
                ok = True
                for key, val in exp_line.items():
                    if key == "flags_contain":
                        if not all(f in actual.flags for f in val):
                            ok = False
                            break
                    elif key in ("parsed_total", "parsed_unit_price", "parsed_quantity"):
                        a = getattr(actual, key)
                        if a is None or a != Decimal(val):
                            ok = False
                            break
                    else:
                        a = getattr(actual, key)
                        if a != val:
                            ok = False
                            break
                if ok:
                    matched = True
                    cursor = ai + 1
                    break
            assert matched, (
                f"expected line[{exp_idx}] not found after cursor {cursor}: {exp_line}\n"
                f"available remaining lines:\n" +
                "\n".join(f"  {ln.line_kind} {ln.parsed_name!r} {ln.parsed_total!r} {ln.flags}"
                         for ln in actual_lines[cursor:])
            )

    # Loyalty
    if "loyalty" in expected:
        exp_loy = expected["loyalty"]
        assert result.loyalty is not None, "expected loyalty, got None"
        assert result.loyalty.program == exp_loy["program"]
        event_kinds = {ev.event_kind for ev in result.loyalty.events}

        if exp_loy.get("has_earned_cashback"):
            assert "earned_cashback" in event_kinds
            if "earned_cashback_amount" in exp_loy:
                ev = next(e for e in result.loyalty.events if e.event_kind == "earned_cashback")
                assert ev.amount_eur == Decimal(exp_loy["earned_cashback_amount"])

        if exp_loy.get("has_earned_points"):
            assert "earned_points" in event_kinds
            if "earned_points" in exp_loy:
                ev = next(e for e in result.loyalty.events if e.event_kind == "earned_points")
                assert ev.points == exp_loy["earned_points"]

        if exp_loy.get("has_balance_info"):
            assert "balance_info" in event_kinds
            ev = next(e for e in result.loyalty.events if e.event_kind == "balance_info")
            if "balance_eur" in exp_loy:
                assert ev.balance_eur == Decimal(exp_loy["balance_eur"])
            if "balance_points" in exp_loy:
                assert ev.balance_points == exp_loy["balance_points"]

    # Warnings
    if "warnings_count_max" in expected:
        assert len(result.warnings) <= expected["warnings_count_max"], \
            f"too many warnings: {[w.code for w in result.warnings]}"
