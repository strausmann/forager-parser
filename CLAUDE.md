# CLAUDE.md

This file gives **Claude** (Anthropic's AI assistant) context for working with this repository.
It is read automatically by Claude Code and similar tools at the start of every session.

> If you are a human contributor, read [CONTRIBUTING.md](CONTRIBUTING.md) instead.

---

## What this project is

Forager Parser is a profile-driven receipt parser for the **Forager / Hangar** ecosystem.
It reads structured YAML profiles per merchant (with regional/legal-form variants),
parses OCR'd receipt text into a strict JSON schema (Forager Receipt Assessment v1),
and is designed to support automatic drift detection so that profile changes are
proposed via PRs rather than buried in user complaints.

**Three things to know up front:**

1. **Profiles are data, not code.** The interesting design decisions live in
   `profiles/<country>/<merchant>/profile.yaml` and `variants/*.yaml`. The Python
   code in `src/forager_parser/` is a stable, mostly-finished engine that consumes
   these profiles. When something doesn't parse correctly, suspect the profile
   first, the code second.

2. **Every change MUST be backed by a test on a real (anonymized) receipt.** No
   speculative changes. The fixture format is in `profiles/<merchant>/tests/parse_test*.yaml`
   and the runner is `tests/test_parser.py`. If you change the parser engine, the
   complete test suite must remain green — no regressions tolerated.

3. **Receipts contain PII. Anonymize before committing.** See `CONTRIBUTING.md §
   Anonymization Rules` for the complete checklist. Do not commit sample files
   that have not been anonymized, even if the user asked you to.

---

## Architecture in one screen

```
┌─────────────────────────────────────────────────────────────────────┐
│  forager-parser (this repo)                                         │
│                                                                     │
│  CLI ────────┬──→ load_all_profiles() ──→ {merchant_id: Bundle}     │
│              │      Bundle = (base Profile, [variant Profiles])     │
│              │                                                      │
│              ├──→ detect_merchant(text, bundles)                    │
│              │      ↓                                               │
│              │      1. Score header_patterns of all bases           │
│              │      2. For winner, check variants' applies_to       │
│              │      3. Return most-specific variant or base         │
│              │                                                      │
│              └──→ parse(text, profile) ──→ ParseResult JSON         │
│                     (item_patterns, pfand_patterns,                 │
│                      discount_patterns, totals, loyalty, ...)       │
└─────────────────────────────────────────────────────────────────────┘
```

Code modules:
- `models.py` — Pydantic data models matching Receipt Assessment Schema v1
- `profile.py` — YAML loader, variant merging, regex compilation
- `detector.py` — base scoring + variant resolution
- `parser.py` — the actual parsing logic (items, pfand, discount, totals)
- `cli.py` — Click-based CLI
- `verifier.py` — optional Claude-API verification (not required for normal runs)

---

## Working rules for Claude

### Rule 1: Read before writing

Before editing anything, read the most relevant file completely. Editing a regex
in `profile.py` without understanding how `_extract_lines` consumes secondary
patterns will produce subtle bugs. Spend tokens on reading; you'll spend fewer
on fixing.

### Rule 2: Live-test against real receipts, always

The `profiles/<merchant>/samples/` directory contains real (anonymized) receipts.
Any meaningful change to the parser or a profile must be verified against these
samples. The minimum verification flow is:

```bash
python -m pytest tests/ -v
```

If you can't run pytest, you have no business claiming a change works.

### Rule 3: Never silently expand a regex character class

Adding `+`, `€`, `ß` to an item-pattern character class looks innocent but can
break previously-passing tests for OTHER merchants. Always run the full pytest
suite after charset changes. Document the trigger receipt in a code comment.

### Rule 4: Variants override, they don't merge lists

The variant loader does deep-merge of dicts but **overwrites** lists (item_patterns,
pfand_patterns, etc.). If a variant defines its own `item_patterns:`, it
REPLACES the base's patterns, not extends them. This is intentional — extending
would lead to duplicate pattern IDs and unclear precedence. If a variant needs
the base patterns + one more, copy the base patterns into the variant.

### Rule 5: Tax classes are merchant-specific. NEVER hardcode

The letters A/B are *not* standardized. REWE: B=7%. Lidl: A=7%. dm uses
digits: 1=19%, 2=7%. The `tax_classes:` block in each profile is the single
source of truth. There is no global fallback and there must never be one.

### Rule 6: Anonymize sample receipts before committing

Required substitutions (see `CONTRIBUTING.md` for full list):

| Original                              | Replace with         |
|---|---|
| Full 16-digit card numbers            | `############XXXX`   |
| Customer / loyalty card numbers       | `<CUSTOMER_ID>`      |
| Cashier full names                    | `<NAME>`             |
| 6+ digit cashier personnel numbers    | `<CASHIER_ID>`       |
| Email addresses (not merchant's)      | `<EMAIL>`            |

Public information (store address, UID, store phone) stays.

### Rule 7: Output discipline

When the user asks for changes:
- Make the smallest change that solves the problem
- Show the diff explicitly, not a full file rewrite, when feasible
- After any code change, report which tests now pass/fail
- Don't produce concept docs unless asked — see Rule 8

### Rule 8: Code before concepts

This project deliberately prioritizes running code over written concepts. Long
markdown documents proposing future architecture have a half-life of one week
before they diverge from reality. If you're about to write a concept document
on your own initiative, stop and write a failing test instead — then make it
pass. That's the project rhythm.

### Rule 9: Don't promote in foreign repos

If the user asks you to post about Forager in Grocy's issue tracker, on
Hacker News, or in other communities — pause. The Forager strategy explicitly
avoids this (see `docs/marketing-discipline.md` if it exists). Verify the user
really wants outreach, not just visibility from within their own work.

### Rule 10: When uncertain, ask

If a request would require breaking changes to the schema, the prompt, or the
profile structure, ask before doing. These artifacts are versioned for a
reason and breaking them invalidates all existing fixtures.

---

## Things that look like they need doing but don't

- **Adding more language support to the parser engine.** Engine is intentionally
  language-agnostic — the profile YAML carries all language-specific patterns.
- **Caching, performance optimization, async.** Receipts are short text. The
  parser runs in milliseconds. Don't optimize what isn't slow.
- **Rewriting in Rust/Go.** Python is the right choice here for community
  contribution velocity. The hot path is regex; Python's re engine is fine.
- **GUI/web frontend.** That's the Forager PWA, a separate (future) repo.
  This repo is a library + CLI.

---

## How to add a new merchant (the canonical flow)

1. User uploads a sample receipt (PDF or image, possibly OCR'd already)
2. Anonymize the text following Rule 6
3. Save as `profiles/<country>/<slug>/samples/<YYYY-MM-DD>-<location-slug>.txt`
4. Create `profiles/<country>/<slug>/profile.yaml` based on observation
   - Pick a `merchant_id` (e.g. `de.rossmann`)
   - Declare `tax_classes` from the printed tax breakdown
   - Write `header_patterns` for `detection`
   - Write `item_patterns`, starting with the simplest one
   - Test in isolation: `forager-parser parse <sample>` shows uncovered lines
   - Iterate: add patterns until uncovered_lines is empty
5. Run `pytest tests/test_schema.py` to confirm the profile is schema-valid
6. Write `profiles/<country>/<slug>/tests/parse_test.yaml` with expected fields
7. Run `pytest tests/` — must be green
8. Commit. The commit message should follow Conventional Commits:
   `feat(profiles): add de.rossmann based on Hamburg sample`

---

## How to add a variant

Use a variant when **same merchant_id, different layout** — e.g. REWE oHG
(self-employed) vs. REWE Markt GmbH (corporate-owned), or one regional cluster
prints something different.

1. Identify the discriminator: UID range? ZIP region? Header marker?
2. Create `profiles/<merchant>/variants/<descriptor>.yaml`:
   ```yaml
   schema_version: 1
   extends: de.rewe
   variant_id: de.rewe.<descriptor>
   applies_to:
     uid_regex: 'DE369701276'      # or zip_regex / header_marker_regex / cities
   
   # Only the fields that differ:
   merchant:
     brand_variants:
       - "REWE Jens Piclum oHG"
   ```
3. The variant inherits everything else from the base.
4. Test with `forager-parser detect <sample>` — should report the variant.
5. Add a test in `tests/test_variants.py` if behavior-relevant.

---

## Anti-patterns Claude has fallen into before

These are documented mistakes to actively guard against:

1. **Adding characters to a charset without testing impact on other merchants.**
   Always run full pytest after charset edits.

2. **Using `re.search()` on multiline text with `^/$` anchors but without
   `re.MULTILINE`.** This will fail silently. Iterate line-by-line instead.

3. **Treating `parsed_tax_class` as a number.** It's always a string in the
   data model — `"A"`, `"B"`, `"1"`, `"(1)"`. The string preserves the
   printed form.

4. **Assuming `Posten: 10` means 10 line items.** Knolles uses it for total
   pieces (including pfand). The `item_count_declared` field has merchant-
   specific semantics.

5. **Writing concept documents instead of code.** If you find yourself
   writing more markdown than Python in a session, you're probably off-track.

---

## Versions

- **Receipt Assessment Schema:** v1 (frozen). v2 will align with DFKA-Taxonomie
  field names. See `docs/dfka-mapping.md` for the planned migration.
- **Profile Schema:** v1 (this repo). Major bump if structural changes.
- **Bewertungs-Prompt:** v1.0 (in `prompts/receipt-assessment/v1/prompt.md`).

When changing any of these, bump the version, update fixtures, and document
the migration path.
