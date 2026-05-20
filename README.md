# forager-parser

Profile-driven receipt parser. Reads anonymized supermarket / drugstore receipts
and produces structured JSON, validated against a public schema.

**Status:** Early — works on real receipts from REWE, Lidl, dm, and Edeka
sub-brand Knolles. Built as part of the Forager / Hangar ecosystem.

```bash
pip install forager-parser
forager-parser parse my-receipt.txt
```

## What it does

Given an OCR'd receipt text and a profile, it extracts:

- Merchant (with regional/legal-form variant resolution)
- Store address, ZIP, city, store ID
- Date and time of purchase
- All line items, with quantity, unit price, tax class, totals
- Deposits (Pfand) — including returns and aggregates
- Discounts and coupons
- Tax breakdown
- Payment method and amount
- Loyalty program data (PAYBACK, REWE Bonus, etc.)
- Drift signals: which profile patterns matched vs. didn't, uncovered lines

It does **not** do OCR itself — feed it text. The full Forager pipeline does
the OCR upstream.

## Why this exists

Several existing receipt parsers are good for one of these things, none for all:

- Most can find the merchant name and the total — not the line items.
- Most don't survive layout variations across stores of the same chain.
- None have a community-PR workflow that turns reality drift into structured
  pull requests.

This one tries to. The technical core: YAML profiles per merchant, stored
under `merchants/<country>/<merchant>/`, with inheritance for regional/
store-format variants. The community core: every contribution comes with an
anonymized real sample and a test fixture.

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add merchants.

## Quickstart

```bash
# Install
pip install -e ".[dev]"

# List loaded profiles
forager-parser list-profiles

# Detect which merchant a receipt comes from
forager-parser detect path/to/receipt.txt

# Parse a receipt
forager-parser parse path/to/receipt.txt | jq .

# Parse with explicit profile (skip auto-detection)
forager-parser parse path/to/receipt.txt --profile de.dm
```

## Supported merchants (current)

| ID | Brand | Country | Variants |
|---|---|---|---|
| `de.dm` | dm-drogerie markt | DE | — |
| `de.knolles-markt` | Knolles Markt OHG (Edeka sub-brand) | DE | — |
| `de.lidl` | Lidl | DE | — |
| `de.rewe` | REWE | DE | `de.rewe.ohg-piclum` (self-employed oHG markets) |

More to come — see CONTRIBUTING.md to add yours.

## Project layout

```
forager-parser/
├── src/forager_parser/   # parser engine
├── merchants/            # merchant profile YAML files
│   └── de/<merchant>/
│       ├── profile.yaml      # base profile
│       ├── variants/         # optional regional/legal-form variants
│       ├── samples/          # anonymized real receipts
│       └── tests/            # pytest fixtures
├── schema/               # JSON Schema for profile validation
├── tests/                # parser test suite
└── docs/                 # architecture & design notes
```

## Documentation

- [CLAUDE.md](CLAUDE.md) — instructions for AI assistants working in this repo
- [CONTRIBUTING.md](CONTRIBUTING.md) — how to add merchants, variants, fixes
- [docs/](docs/) — architecture and design notes, including the Forager
  concept docs

## License

See [LICENSE](LICENSE).

## A note on AI-assisted development

Significant parts of this project were drafted with AI assistance. Each
commit was reviewed and run-tested by a human. Profiles are verified against
real receipts. If you find anything that looks like cargo-cult or hallucination,
open an issue — that's exactly the failure mode we're trying to avoid.
