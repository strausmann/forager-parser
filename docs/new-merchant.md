---
name: New merchant request
about: Suggest adding support for a merchant not yet in the repo
labels: [merchant-request, triage]
---

<!-- If you can prepare a PR with the profile + sample + test, that's
     much preferred over an issue. See CONTRIBUTING.md. -->

## Merchant

- **Name:** (e.g. Rossmann)
- **Country:** DE / AT / CH
- **Proposed ID:** `de.<slug>`
- **Parent chain (if a sub-brand):** (e.g. `de.edeka`)

## Public references

- Website:
- Filial-Finder:
- One sample store address:

## Anonymized sample receipt

<details>
<summary>Paste anonymized text here</summary>

```
[anonymized text per CONTRIBUTING.md rules]
```
</details>

## Notable features

- [ ] Has loyalty program — which:
- [ ] Has multi-line items (kg-weight or quantity)
- [ ] Has Pfand — type: einweg / mehrweg / both
- [ ] Has discounts at item level
- [ ] Has discounts at total level (coupons)
- [ ] Uses unusual tax-class markers — describe:
- [ ] Multi-language receipts
- [ ] Other:

## Practical path: image/PDF to new sample

The parser in this repository does not run OCR itself. It expects plain text.
Use this workflow to turn a receipt photo or PDF into a sample fixture.

### 1) Create merchant folder layout

```bash
mkdir -p merchants/<country>/<slug>/{samples,tests,variants}
```

Example:

```bash
mkdir -p merchants/de/rossmann/{samples,tests,variants}
```

### 2) Convert PDF/image to OCR text

Pick one method that works in your environment:

- Existing OCR pipeline in your Forager worker (preferred if already set up)
- Local OCR (for example PaddleOCR or Tesseract)

Target output: one UTF-8 text file containing the full receipt text in print order.

## Create merchant via Claude prompt

Use the canonical receipt-assessment prompt to bootstrap a new merchant profile.

Prompt source:

- `prompt/receipt/assessment/v1/prompt.md`

Expected behavior from the prompt:

- If no `known_profile_yaml` is provided, Claude should return a `profile_proposal`
     with a YAML stub for a new merchant profile.

### Required inputs for this mode

- `ocr_text` (required if no image input)
- `repo_known_merchants` (recommended)
- `forager_schema_version: "1"`
- Do NOT pass `known_profile_yaml` when you want a new profile proposal.

### Minimal flow

1. Run OCR on receipt PDF/image.
2. Execute prompt `prompt/receipt/assessment/v1/prompt.md` with OCR text.
3. Extract `profile_proposal.yaml` from the JSON response.
4. Save it as `merchants/<country>/<slug>/profile.yaml`.
5. Manually review regex quality and tax class mapping.
6. Run detect/parse locally and refine.
7. Add `tests/parse_test.yaml` and run `make test`.

### Important notes

- Claude output is a starting point, not production-ready truth.
- Always validate against real anonymized receipts.
- Prefer small regex adjustments over broad character class expansion.

### 3) Save sample text file

Use naming convention:

`<YYYY-MM-DD>-<location>.txt`

Example:

```bash
$EDITOR merchants/de/rossmann/samples/2026-05-20-hamburg.txt
```

### 4) Anonymize before commit

Must replace:

- 16-digit card numbers -> `############XXXX`
- customer/loyalty IDs -> `<CUSTOMER_ID>`
- cashier names -> `<NAME>`
- cashier personnel IDs (6+ digits) -> `<CASHIER_ID>`
- private email addresses -> `<EMAIL>`

Keep store public data (address, ZIP, city, UID, store phone).

### 5) Build minimal profile and validate detection

```bash
$EDITOR merchants/<country>/<slug>/profile.yaml
python -m forager_parser.cli detect merchants/<country>/<slug>/samples/<sample>.txt --profiles-dir merchants
```

### 6) Parse and inspect uncovered lines

```bash
python -m forager_parser.cli parse merchants/<country>/<slug>/samples/<sample>.txt --profiles-dir merchants | jq .
```

Iterate profile patterns until critical fields and totals are stable.

### 7) Add fixture test

```bash
$EDITOR merchants/<country>/<slug>/tests/parse_test.yaml
```

### 8) Run full validation

```bash
make test
```

`make test` executes parser tests and parses all sample text files under `merchants/*/*/samples/`.

## Definition of done for new merchant

- [ ] at least one anonymized sample text in `merchants/<country>/<slug>/samples/`
- [ ] `profile.yaml` added under `merchants/<country>/<slug>/`
- [ ] parse fixture under `merchants/<country>/<slug>/tests/`
- [ ] `make test` passes
- [ ] no PII found in committed samples
