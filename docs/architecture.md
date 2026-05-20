# Architecture

This document explains how forager-parser works internally. For "how to add a
merchant" see [CONTRIBUTING.md](../CONTRIBUTING.md). For broader Forager
context, see the project concept documents.

## Three-step parse flow

```
            ┌───────────────┐
   text ───►│  detect       │── identifies merchant + selects variant
            └───────┬───────┘
                    │
                    ▼
            ┌───────────────┐
            │  load profile │── merges base + variant YAMLs at load time
            └───────┬───────┘
                    │
                    ▼
            ┌───────────────┐
            │  parse        │── extracts lines, totals, loyalty
            └───────┬───────┘
                    │
                    ▼
              ParseResult JSON
```

## Profile bundles

A `ProfileBundle` groups a base profile with all its variants:

```python
@dataclass
class ProfileBundle:
    base: Profile
    variants: list[Profile]
```

Variants are detected, loaded, and pre-merged with their parent at startup time
(`load_all_profiles`). At parse time, no merging happens — the variant Profile
object is fully self-contained.

## Variant resolution

The `detect_merchant()` function does two passes:

1. **Base detection.** Score every base profile's `detection.header_patterns`
   against the receipt text. Highest score above `minimum_score` wins.
2. **Variant selection.** For the winning base, iterate its variants. Each
   `applies_to` block is evaluated:
   - All conditions are AND-combined
   - A variant matches if **all** its specified conditions are satisfied
   - The variant with the highest `condition_count` (most specific) wins
   - If no variant matches, the base profile is used

## Parser internals

The actual parser in `parser.py` is a line-oriented state machine. For each
line in the receipt text, it tries:

1. **Discount patterns** first (most specific — e.g. "1 x Frischerabatt -0,69 B")
2. **Pfand patterns** next (e.g. "PFAND 0,25 EURO 0,25 A *")
3. **Item patterns** last, in profile order

Each pattern can have a `secondary` regex for multi-line items (e.g. the
"0,490 kg x 5,58 EUR/kg" detail line following a weight item). When a
secondary matches, the parser advances the index and marks the consumed line.

## Tax-class semantics

Tax-class codes (`A`, `B`, `1`, `2`, `(1)`, `b`, ...) are merchant-specific.
There is no global mapping. Each profile declares its own:

```yaml
tax_classes:
  A: { rate: 0.19 }    # REWE: A = 19%
  B: { rate: 0.07 }    # REWE: B = 7%
```

vs.

```yaml
tax_classes:
  "1": { rate: 0.19 }  # dm: 1 = 19%
  "2": { rate: 0.07 }  # dm: 2 = 7%
```

This is intentional. There is no "default tax class". See `CLAUDE.md` Rule 5.

## Why YAML profiles, not Python?

- Profile changes need to be reviewable by non-Python developers
- They need to be schema-validated automatically
- They need to be diff-able cleanly
- A profile change should never require a parser code release

The parser engine is small (~600 lines). The interesting design surface lives
in the YAML files.

## Why "extends" with list-overwrite, not list-merge?

If variants could extend the parent's `item_patterns` list, two problems arise:

1. Pattern IDs would collide
2. Precedence between base patterns and variant patterns would need to be
   explicitly specified, complicating the YAML format

By overwriting lists, the variant author makes a clear decision: include the
base patterns explicitly (copy them) or use a different set entirely.

If patterns commonly need to be shared, a future `_base.yaml` convention can
provide a third level — but that's not yet needed.

## Drift detection

The parser produces a `profile_assessment` block in its output:

```json
{
  "profile_assessment": {
    "matched_patterns": [...],
    "failed_patterns": [...],
    "uncovered_lines": [...]
  }
}
```

`uncovered_lines` is the key drift signal: it lists receipt lines that none of
the profile's patterns matched. In a healthy parse, this should be empty (or
contain only meta-lines like the tax breakdown header).

When a downstream system (Forager worker) sees a non-empty `uncovered_lines`
list across multiple receipts of the same merchant, it raises a drift alert
that can be turned into a `merchant:layout-update` or `merchant:variant` PR.

## What's not in this parser

- **OCR.** Receipts come in as text. The OCR pipeline (PaddleOCR + Tesseract
  fallback) lives in the Forager worker, not here.
- **Backend integration.** Snipe-IT / Grocy / Spoolman writes happen
  downstream. This parser is a pure function: text + profile → JSON.
- **PII redaction.** Receipts going INTO the parser are assumed already
  anonymized. Sample files in the repo MUST be anonymized.
