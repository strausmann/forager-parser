# Contributing to Forager Parser

Welcome — and thanks for considering a contribution. This document covers the
practical "how", from sample receipts to pull requests.

## tl;dr

1. Fork & clone
2. `pip install -e ".[dev]"`
3. `pytest` — must be green before you start
4. Make changes (profile, code, or both)
5. Add tests (real anonymized receipt as fixture)
6. `pytest` — must still be green
7. Open a PR using the relevant template

---

## Types of contributions

| Type | Label | Difficulty | Owner |
|---|---|---|---|
| Add a new merchant profile | `merchant:new` | Beginner | You |
| Add a regional/legal variant | `merchant:variant` | Intermediate | You |
| Fix an existing profile bug | `merchant:fix` | Beginner | You |
| Update profile for layout change | `merchant:layout-update` | Intermediate | You |
| Improve parser engine | `parser:enhance` | Advanced | Discuss in issue first |
| Schema change | `schema:proposal` | Advanced | RFC required |
| Documentation | `docs` | Beginner | You |

---

## Anonymization Rules

**This is non-negotiable.** Every sample receipt committed must be anonymized.
The CI pipeline will reject commits with detected PII.

### MUST replace

| What | Replace with |
|---|---|
| Full 16-digit card numbers | `############XXXX` |
| Last 4 digits of card after `############` masking | keep `XXXX` |
| Customer / loyalty card numbers (PAYBACK, store apps) | `<CUSTOMER_ID>` |
| Cashier / staff full names | `<NAME>` |
| 6+ digit cashier personnel numbers | `<CASHIER_ID>` |
| Email addresses (unless explicitly the merchant's public email) | `<EMAIL>` |
| Personal phone numbers (not the store's) | `<PHONE>` |

### MAY keep (these are NOT PII)

- Store address, ZIP, city
- Store telephone number (public)
- UID-Nummer / Steuernummer (public business data)
- TSE signatures, signature counters, transaction IDs
- Trace numbers, terminal IDs, transaction reference numbers
- Beleg-Nummer, Pos-Info, AS-Codes
- Authorization numbers (these are not card numbers)

### Why this matters

A profile is only as useful as the receipts it's tested against. We want real
receipts in fixtures, not synthetic ones — that's the only way the parser stays
honest. But "real receipts" means PII discipline. If in doubt, leave the field
out — an under-anonymized commit is worse than an over-anonymized one.

---

## Adding a new merchant profile

### Step-by-step

```bash
# 1. Create the directory structure
mkdir -p merchants/de/<merchant-slug>/{samples,tests}

# 2. Drop an anonymized sample receipt as plain text
# Naming: <YYYY-MM-DD>-<short-location-slug>.txt
$EDITOR merchants/de/<merchant-slug>/samples/2026-01-15-hamburg.txt

# 3. Write a profile.yaml
$EDITOR merchants/de/<merchant-slug>/profile.yaml

# 4. Test detection
forager-parser detect merchants/de/<merchant-slug>/samples/2026-01-15-hamburg.txt
# Expected: 'Top-Kandidat: de.<slug>'

# 5. Test parsing
forager-parser parse merchants/de/<merchant-slug>/samples/2026-01-15-hamburg.txt | jq .
# Inspect: are all items parsed? does grand_total match computed_total?

# 6. Write the test fixture
$EDITOR merchants/de/<merchant-slug>/tests/parse_test.yaml

# 7. Run the full test suite
pytest
```

### Profile YAML structure

See [merchants/de/dm/profile.yaml](merchants/de/dm/profile.yaml) for a minimal,
well-commented example. The full schema is at
[schema/merchant-profile.v1.json](schema/merchant-profile.v1.json) and is
enforced by CI.

Canonical hosted URL:
https://strausmann.github.io/forager-parser/schema/merchant-profile.v1.json

Required blocks:
- `schema_version: 1`
- `merchant:` (id, name, country)
- `detection:` (header_patterns + minimum_score)
- `tax_classes:` (mapping printed class codes to VAT rates)
- `item_patterns:` (at least one)
- `date_extraction:` (at least one)
- `totals:` (grand_total + payment)

Optional but commonly needed:
- `pfand_patterns:` for deposit lines
- `discount_patterns:` for rebate lines
- `tax_breakdown:` for the per-class summary table
- `loyalty:` if the receipt has a loyalty program block
- `store_extraction:` for address/city/store_id parsing

### Tax class declaration is mandatory and merchant-specific

The letters A/B mean different things at different merchants. There is no
global default. Always declare:

```yaml
tax_classes:
  A:
    rate: 0.19          # REWE convention: A=19%
    description: "19% MwSt (Standard)"
  B:
    rate: 0.07          # REWE convention: B=7%
    description: "7% MwSt (Lebensmittel)"
```

Compare with dm (digits instead of letters):

```yaml
tax_classes:
  "1":
    rate: 0.19
  "2":
    rate: 0.07
```

---

## Adding a variant

Use a variant when the same `merchant_id` has different layouts that depend on
a structural discriminator: legal form (oHG vs. GmbH-Eigenbetrieb), region,
store cluster, or time era.

```yaml
# merchants/de/rewe/variants/ohg-piclum.yaml
schema_version: 1
extends: de.rewe
variant_id: de.rewe.ohg-piclum

applies_to:
  uid_regex: 'DE369701276'                 # unique UID of this merchant
  header_marker_regex: '(?i)REWE\s+[^\n]+?\s+oHG'

merchant:
  brand_variants:
    - "REWE Jens Piclum oHG"
```

Resolution rules:
- All conditions in `applies_to` are AND-combined
- The variant with the most matching conditions wins
- If no variant matches, the base profile is used

---

## Fixing an existing profile

If you find a receipt that doesn't parse correctly, the smallest useful PR is:

1. Add the problematic receipt as a new sample under
  `merchants/<merchant>/samples/<YYYY-MM-DD>-<location>.txt`
2. Run the parser against it; observe what fails
3. Adjust the relevant pattern in `profile.yaml` (most often a regex)
4. Re-run; confirm it now parses correctly
5. **Critically:** run `pytest` — ensure no other merchant's tests broke
6. Add a test fixture documenting the new expected behavior

---

## Pull Request guidelines

### Title

Use Conventional Commits format:

```
feat(merchants): add de.rossmann based on Hamburg sample
fix(merchants/rewe): handle items with leading digit '9 BAG.BROETCHEN'
feat(parser): add discount_patterns block
docs(contributing): clarify anonymization rules
```

### Body

For profile changes, include:
- What merchant / variant
- Which sample receipt(s) you tested against
- A short summary of what changed in the profile (which patterns added/modified)
- Confirmation that `pytest` passes locally

For code changes, include:
- The motivation (why)
- The change (what)
- Affected merchants / variants
- Test coverage strategy

### Required files

- [ ] Anonymized sample under `samples/`
- [ ] Updated `profile.yaml` (or new one)
- [ ] Test fixture under `tests/parse_test*.yaml`
- [ ] `pytest` passes locally
- [ ] No PII detected (CI will double-check)

---

## CI Pipeline (what gets checked)

Every PR triggers:

1. **Schema validation** — all profile YAMLs validate against
   `schema/merchant-profile.v1.json`
2. **PII detection** — scan sample files for credit card patterns, etc.
3. **Pytest suite** — all `parse_test*.yaml` and `test_variants.py` must pass
4. **Regression check** — no previously-passing test may regress
5. **Lint** — YAML lint, regex compile check, markdown lint

CI failures must be fixed before merge.

---

## Questions?

Open a discussion (not an issue) — issues are for bug reports and concrete
feature requests. For "how do I…" or "should we…" questions, discussions are
better.
