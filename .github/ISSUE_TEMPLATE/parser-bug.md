---
name: Parser bug — receipt parses incorrectly
about: A receipt is not parsed correctly by an existing profile
labels: [bug, triage]
---

<!-- Please read CONTRIBUTING.md first. If you can already prepare a PR with
     the fix and a test fixture, that's preferred. -->

## Affected merchant

- **Merchant ID:** `de.<slug>` (e.g. `de.rewe`)
- **Variant (if applicable):** `de.<slug>.<variant>`

## What was wrong

<!-- Describe what the parser did vs. what it should have done. Be specific
     about which line(s), which fields. -->

## Anonymized receipt (or excerpt)

<details>
<summary>Paste anonymized text here</summary>

```
[receipt text, with PII redacted per CONTRIBUTING.md anonymization rules]
```
</details>

## Parser output (if you ran it)

<details>
<summary>JSON output from `forager-parser parse`</summary>

```json
[paste output here]
```
</details>

## Expected behavior

<!-- What should `parsed_name` / `parsed_total` / `tax_class` / etc. have been? -->

## Environment

- forager-parser version: <!-- e.g. 0.1.0 -->
- Python version: <!-- e.g. 3.12 -->
- OS: <!-- e.g. Ubuntu 24.04 -->
