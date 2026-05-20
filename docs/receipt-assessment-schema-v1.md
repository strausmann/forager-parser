# Forager Receipt Assessment Schema v1

**Status:** Standard
**Version:** 1.0
**Pfad im Repo:** `schema/receipt-assessment.v1.yaml` (Source) und `schema/receipt-assessment.v1.json` (kompiliert für Validatoren)

> Das ist das **kanonische Output-Format** des Bewertungs-Prompts. Jeder Bon, der durch Forager läuft, produziert eine Datenstruktur nach exakt diesem Schema. Strukturelle Konstanz ist hier wichtiger als Felder-Reichtum — neue Beobachtungen wandern in `novel_observations`, niemals in ad-hoc-Felder.

---

## Struktur

```yaml
# schema/receipt-assessment.v1.yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
$id: "https://forager.strausmann.cloud/schema/receipt-assessment.v1.json"
title: "Forager Receipt Assessment"
type: object
required:
  - schema_version
  - assessment_metadata
  - status
properties:

  schema_version:
    const: "1"
  
  status:
    enum: ["ok", "partial", "failed"]
    description: |
      - ok: Bon vollständig erfasst, keine offenen Punkte
      - partial: Bon erfasst, aber mit Warnungen/unsicheren Zeilen
      - failed: Bon konnte nicht erfasst werden (siehe failure_reason)
  
  failure_reason:
    type: [string, "null"]
    description: "Bei status=failed: kurze Begründung (z.B. 'image_unreadable')"

  assessment_metadata:
    type: object
    required: [assessor_version, prompt_version, model, evaluated_at]
    properties:
      assessor_version: { type: string }
      prompt_version: { type: string, examples: ["v1.0"] }
      model: { type: string, examples: ["claude-opus-4-7"] }
      evaluated_at: { type: string, format: date-time }
      ocr_engine: { type: [string, "null"] }
      ocr_engine_version: { type: [string, "null"] }
      input_kinds: 
        type: array
        items: { enum: ["image", "ocr_text", "ocr_tokens", "pdf"] }
      known_profile_used:
        type: [string, "null"]
        description: "merchant_id des verwendeten Profils, falls eines vorgegeben war"
      profile_version_used:
        type: [string, "null"]
        description: "Git-SHA des Profils, falls eines verwendet wurde"

  # === IDENTIFIKATION ===
  merchant:
    type: object
    required: [identified, confidence]
    properties:
      identified: { type: boolean }
      merchant_id: 
        type: [string, "null"]
        pattern: "^[a-z]{2,3}\\.[a-z0-9_-]+$"
        description: "z.B. 'de.rewe', 'de.knolles-markt'"
      name: { type: [string, "null"] }
      country: { type: [string, "null"], pattern: "^[A-Z]{2}$" }
      confidence: { type: number, minimum: 0.0, maximum: 1.0 }
      is_known_in_repo: { type: boolean }
      parent_chain:
        type: [string, "null"]
        description: "Bei Sub-Marken: übergeordnete Kette (z.B. 'de.edeka' für 'de.knolles-markt')"
      
      proposal:
        type: [object, "null"]
        description: "Wenn nicht bekannt: Vorschlag für neue merchant_id"
        properties:
          suggested_id: { type: string }
          suggested_name: { type: string }
          suggested_parent_chain: { type: [string, "null"] }
          rationale: { type: string }

  store:
    type: object
    properties:
      street: { type: [string, "null"] }
      zip: { type: [string, "null"] }
      city: { type: [string, "null"] }
      phone: { type: [string, "null"] }
      store_id: { type: [string, "null"], description: "Filialnummer wie vom Händler vergeben" }
      uid_number: { type: [string, "null"], description: "USt-IdNr." }
      tax_number: { type: [string, "null"] }
      cashier_id: { type: [string, "null"], description: "Anonyme Bedienernummer" }

  # === ZEITPUNKT ===
  purchase_datetime:
    type: object
    properties:
      primary:
        type: [string, "null"]
        format: date-time
        description: "Beleg-Datum/Uhrzeit, RFC 3339 mit Zeitzone falls bekannt"
      date_only:
        type: [string, "null"]
        format: date
      time_only:
        type: [string, "null"]
        format: time
      alternative_datetimes:
        type: array
        items:
          type: object
          properties:
            source: { type: string, examples: ["tse_start", "tse_stop", "payment_terminal"] }
            value: { type: string, format: date-time }
            confidence: { type: number }
      timezone_inferred: { type: [string, "null"], examples: ["Europe/Berlin"] }

  # === GELD-TOTALS ===
  totals:
    type: object
    properties:
      grand_total: { type: [number, "null"] }
      currency: { type: string, default: "EUR" }
      computed_total:
        type: [number, "null"]
        description: "Aus Positionen berechnete Summe (für Plausibilitätscheck)"
      totals_match: 
        type: [boolean, "null"]
        description: "true wenn computed_total ≈ grand_total (Toleranz 0,02)"
      item_count_declared:
        type: [integer, "null"]
        description: "Falls auf dem Bon vermerkt (z.B. 'Posten: 10')"
      item_count_observed:
        type: integer
        description: "Aus lines[] gezählt (line_kind=item)"

  tax_breakdown:
    type: array
    items:
      type: object
      required: [class_code, rate, net, tax, gross]
      properties:
        class_code: { type: string, examples: ["A", "B", "1", "2"] }
        rate: 
          type: number
          description: "MwSt-Satz als Dezimalzahl (0.07 = 7%)"
        net: { type: number }
        tax: { type: number }
        gross: { type: number }
        sum_of_items_matches:
          type: [boolean, "null"]
          description: "Plausibilitätscheck pro Klasse"

  tax_class_mapping:
    type: object
    description: |
      Zuordnung der vorgefundenen Class-Codes zu MwSt-Sätzen. WICHTIG: das ist
      händlerabhängig — bei REWE oft B=7%, bei Lidl A=7%.
    additionalProperties:
      type: object
      properties:
        rate: { type: number }
        rate_known: { type: boolean }
        derived_from: { enum: ["tax_breakdown_table", "profile_hint", "guess"] }

  # === ZAHLUNG ===
  payment:
    type: object
    properties:
      method: 
        type: [string, "null"]
        examples: ["Mastercard", "Visa", "EC-Cash", "Bargeld", "Maestro", "Girocard"]
      amount: { type: [number, "null"] }
      contactless: { type: [boolean, "null"] }
      pii_fields_detected:
        type: array
        items:
          type: object
          properties:
            field: { type: string, examples: ["masked_card_pan", "terminal_id", "trace_id"] }
            value_present: { type: boolean }
            should_redact: { type: boolean }

  # === POSITIONEN ===
  lines:
    type: array
    items:
      type: object
      required: [line_number, raw_text, line_kind, parse_confidence]
      properties:
        line_number: { type: integer, minimum: 1 }
        raw_text: 
          type: string
          description: "EXAKT wie auf dem Bon, bei Multi-Line alle Zeilen mit \\n verbunden"
        raw_text_lines:
          type: array
          items: { type: string }
          description: "Bei Multi-Line: einzelne Original-Zeilen"
        
        line_kind:
          enum: 
            - item
            - pfand
            - pfand_aggregate
            - pfand_return
            - discount
            - coupon
            - loyalty_info
            - subtotal
            - separator
            - unknown
        
        # Geparste Felder
        parsed_name: { type: [string, "null"] }
        parsed_quantity: { type: [number, "null"] }
        parsed_unit: 
          type: [string, "null"]
          examples: ["Stk", "kg", "g", "l", "ml"]
        parsed_unit_price: { type: [number, "null"] }
        parsed_total: { type: [number, "null"] }
        parsed_tax_class: { type: [string, "null"] }
        
        # Metadaten
        parse_confidence: { type: number, minimum: 0.0, maximum: 1.0 }
        parent_line_number:
          type: [integer, "null"]
          description: "Bei Kind-Positionen (z.B. Pfand zu Item): line_number des Parents"
        
        flags:
          type: array
          items:
            enum:
              - weight_item
              - quantity_inline
              - quantity_multiline
              - multi_line_raw
              - not_rebate_eligible    # '*'-Markierung bei manchen Händlern
              - returned_deposit
              - negative_amount
              - currency_symbol_inline
              - has_brand_prefix
        
        observed_symbols:
          type: array
          items:
            type: object
            properties:
              symbol: { type: string, examples: ["*", "€", "°P"] }
              position: { enum: ["before_price", "after_price", "after_tax", "inline"] }
              meaning_assumed: { type: [string, "null"] }
        
        matched_pattern_id:
          type: [string, "null"]
          description: "ID des Profil-Patterns, das diese Zeile erfasste"

  # === LOYALTY ===
  loyalty:
    type: [object, "null"]
    properties:
      program: 
        type: string
        examples: ["PAYBACK", "REWE Bonus", "Lidl Plus", "DeutschlandCard"]
      
      events:
        type: array
        items:
          type: object
          required: [event_kind]
          properties:
            event_kind:
              enum:
                - earned_points
                - earned_coupon
                - earned_cashback
                - redeemed_coupon
                - balance_info
                - eligible_amount
            
            # je nach event_kind:
            points: { type: [integer, "null"] }
            amount_eur: { type: [number, "null"] }
            coupon_target: { type: [string, "null"], description: "z.B. 'Tulip Fl' bei REWE-Coupon" }
            coupon_value: { type: [number, "null"] }
            balance_points: { type: [integer, "null"] }
            balance_eur: { type: [number, "null"] }
            expires_at: { type: [string, "null"], format: date }
            
            raw_text: { type: string }

  # === PROFIL-BEFUND ===
  profile_assessment:
    type: object
    description: "Selbst-Bewertung gegen ein bekanntes Profil ODER Vorschlag für ein neues"
    properties:
      mode:
        enum: ["validated_against_known", "no_profile_available", "novel_merchant"]
      
      # Wenn validiert:
      matched_patterns:
        type: array
        description: "Patterns aus dem Profil, die griffen"
        items:
          type: object
          properties:
            pattern_id: { type: string }
            match_count: { type: integer }
            line_numbers: { type: array, items: { type: integer } }
      
      failed_patterns:
        type: array
        description: |
          Patterns, die laut Profil greifen sollten, aber nicht griffen.
          Das ist das wichtigste Signal für Profil-Drift.
        items:
          type: object
          required: [pattern_id, expected_for, observed_in_line]
          properties:
            pattern_id: { type: string }
            expected_for: { type: string, description: "Erwarteter Anwendungsfall" }
            observed_in_line: { type: integer, description: "Welche Bon-Zeile hätte matchen sollen" }
            example_line_text: { type: string }
            possible_reason: 
              type: [string, "null"]
              examples: 
                - "Regex erwartet 2+ Whitespace zwischen Name und Total, fand nur 1"
                - "Tax-Klasse-Marker fehlt am Zeilenende"
      
      uncovered_lines:
        type: array
        description: "Bon-Zeilen, die kein Profil-Pattern erfasste"
        items:
          type: object
          properties:
            line_number: { type: integer }
            raw_text: { type: string }
            guessed_kind: { type: string }
            suggested_pattern_addition: { type: [string, "null"] }
      
      # Wenn novel:
      profile_proposal:
        type: [object, "null"]
        description: "YAML-Profil-Stub als JSON-Repräsentation"
        properties:
          yaml: { type: string, description: "Vorgeschlagenes profile.yaml als String" }
          rationale: { type: string }
          test_fixtures_suggested:
            type: array
            items: { type: string }
  
  # === DRIFT ===
  drift_detection:
    type: object
    properties:
      drift_detected: { type: boolean }
      drift_reasons:
        type: array
        items:
          type: object
          properties:
            kind:
              enum: 
                - missing_expected_marker
                - alternative_marker_found
                - tax_class_inconsistency
                - new_line_kind_observed
                - layout_signature_changed
            detail: { type: string }
            severity: { enum: ["low", "medium", "high"] }
            suggested_action:
              enum:
                - update_profile_minor
                - update_profile_major
                - new_layout_variant
                - human_review_required

  # === NEUE BEOBACHTUNGEN ===
  novel_observations:
    type: array
    description: |
      Anything that doesn't fit into existing schema fields. This is the
      "growth path" — what's recurring here will get its own field in v2.
    items:
      type: object
      required: [kind, description]
      properties:
        kind: 
          type: string
          examples: 
            - "new_symbol"
            - "new_pattern_variant"
            - "new_loyalty_program"
            - "new_section_kind"
            - "new_tax_class"
        description: { type: string }
        line_numbers: { type: array, items: { type: integer } }
        suggested_schema_extension: { type: [string, "null"] }

  # === WARNUNGEN ===
  warnings:
    type: array
    items:
      type: object
      required: [code, message]
      properties:
        code:
          enum:
            - totals_mismatch
            - tax_breakdown_mismatch
            - line_count_mismatch
            - missing_datetime
            - missing_merchant_id
            - low_overall_confidence
            - pii_in_raw_text
            - ocr_quality_low
        message: { type: string }
        severity: { enum: ["info", "warning", "error"] }
        affected_lines: { type: array, items: { type: integer } }

  # === GESAMT-KONFIDENZ ===
  overall_confidence:
    type: object
    properties:
      merchant_identification: { type: number }
      datetime_extraction: { type: number }
      item_parsing: { type: number }
      totals_reconciliation: { type: number }
      overall: { type: number }

  # === REGIONALE INFO ===
  regional_hint:
    type: object
    description: |
      Hilfreich für die "ein REWE in 21220 vs. ein REWE in Hamburg-Mitte"-Erkennung.
      Erlaubt der Profil-Bibliothek, regionale Sub-Varianten zu sammeln.
    properties:
      zip_region: 
        type: [string, "null"]
        description: "Erste 2-3 Ziffern der PLZ, z.B. '212' für Norddeutschland"
      federal_state: 
        type: [string, "null"]
        examples: ["Niedersachsen", "Hamburg", "Bayern"]
      observed_format_quirks:
        type: array
        items: { type: string }
        description: |
          Auffälligkeiten, die regional bedingt sein KÖNNTEN:
          'name_uses_lowercase', 'comma_as_decimal_separator', 'date_format_dd_mm_yy', etc.
```

---

## Beispiel-Output (REWE Maschen, 20.05.2026, hochgeladener Bon)

```json
{
  "schema_version": "1",
  "status": "ok",
  "assessment_metadata": {
    "assessor_version": "1.0",
    "prompt_version": "v1.0",
    "model": "claude-opus-4-7",
    "evaluated_at": "2026-05-20T15:42:00Z",
    "ocr_engine": "paddleocr",
    "ocr_engine_version": "2.7.0",
    "input_kinds": ["image", "ocr_text"],
    "known_profile_used": "de.rewe",
    "profile_version_used": "abc123def"
  },
  "merchant": {
    "identified": true,
    "merchant_id": "de.rewe",
    "name": "REWE",
    "country": "DE",
    "confidence": 0.98,
    "is_known_in_repo": true,
    "parent_chain": null
  },
  "store": {
    "street": "Schulstraße 46-48",
    "zip": "21220",
    "city": "Maschen",
    "phone": "0 41 05 / 15 56 08",
    "store_id": "0803",
    "uid_number": "DE812706034",
    "cashier_id": "616161"
  },
  "purchase_datetime": {
    "primary": "2026-05-20T14:22:48+02:00",
    "date_only": "2026-05-20",
    "time_only": "14:22:48",
    "alternative_datetimes": [
      {
        "source": "tse_start",
        "value": "2026-05-20T14:21:34+02:00",
        "confidence": 0.95
      }
    ],
    "timezone_inferred": "Europe/Berlin"
  },
  "totals": {
    "grand_total": 32.84,
    "currency": "EUR",
    "computed_total": 32.84,
    "totals_match": true,
    "item_count_declared": null,
    "item_count_observed": 16
  },
  "tax_breakdown": [
    {
      "class_code": "B",
      "rate": 0.07,
      "net": 30.69,
      "tax": 2.15,
      "gross": 32.84,
      "sum_of_items_matches": true
    }
  ],
  "tax_class_mapping": {
    "B": {
      "rate": 0.07,
      "rate_known": true,
      "derived_from": "tax_breakdown_table"
    }
  },
  "payment": {
    "method": "Mastercard",
    "amount": 32.84,
    "contactless": true,
    "pii_fields_detected": [
      {
        "field": "masked_card_pan",
        "value_present": true,
        "should_redact": true
      },
      {
        "field": "trace_id",
        "value_present": true,
        "should_redact": false
      }
    ]
  },
  "lines": [
    {
      "line_number": 1,
      "raw_text": "MINI SALAMI 4ER                   0,99 B",
      "line_kind": "item",
      "parsed_name": "MINI SALAMI 4ER",
      "parsed_total": 0.99,
      "parsed_tax_class": "B",
      "parse_confidence": 0.98,
      "flags": [],
      "matched_pattern_id": "rewe.primary_pattern"
    },
    {
      "line_number": 4,
      "raw_text": "ERDBEERE                          2,73 B\n  0,490 kg x   5,58 EUR/kg",
      "raw_text_lines": [
        "ERDBEERE                          2,73 B",
        "  0,490 kg x   5,58 EUR/kg"
      ],
      "line_kind": "item",
      "parsed_name": "ERDBEERE",
      "parsed_quantity": 0.490,
      "parsed_unit": "kg",
      "parsed_unit_price": 5.58,
      "parsed_total": 2.73,
      "parsed_tax_class": "B",
      "parse_confidence": 0.96,
      "flags": ["weight_item", "multi_line_raw"],
      "matched_pattern_id": "rewe.rewe_weight_item"
    }
  ],
  "loyalty": {
    "program": "REWE Bonus",
    "events": [
      {
        "event_kind": "earned_cashback",
        "amount_eur": 0.35,
        "raw_text": "Mit diesem Einkauf hast du 0,35 EUR REWE Bonus-Guthaben gesammelt"
      },
      {
        "event_kind": "earned_coupon",
        "coupon_target": "Tulip Fl",
        "coupon_value": 0.35,
        "raw_text": "0,35EUR auf Tulip Fl                0,35 EUR"
      },
      {
        "event_kind": "balance_info",
        "balance_eur": 36.95,
        "raw_text": "Aktuelles Bonus-Guthaben: 36,95 EUR"
      }
    ]
  },
  "profile_assessment": {
    "mode": "validated_against_known",
    "matched_patterns": [
      {"pattern_id": "rewe.primary_pattern", "match_count": 14, "line_numbers": [1,2,3,5,6,7,9,11,12,13,14,15,16]},
      {"pattern_id": "rewe.rewe_weight_item", "match_count": 2, "line_numbers": [4,8]},
      {"pattern_id": "rewe.rewe_quantity_item", "match_count": 1, "line_numbers": [10]}
    ],
    "failed_patterns": [],
    "uncovered_lines": []
  },
  "drift_detection": {
    "drift_detected": false,
    "drift_reasons": []
  },
  "novel_observations": [],
  "warnings": [],
  "overall_confidence": {
    "merchant_identification": 0.98,
    "datetime_extraction": 0.99,
    "item_parsing": 0.97,
    "totals_reconciliation": 1.00,
    "overall": 0.98
  },
  "regional_hint": {
    "zip_region": "212",
    "federal_state": "Niedersachsen",
    "observed_format_quirks": ["uppercase_item_names", "comma_decimal_separator"]
  }
}
```

---

## Verwendung: Drei Modi

### Modus A — bekannter Händler, validierender Lauf

```python
result = receipt_assessor.run(
    receipt=receipt,
    known_profile_id="de.rewe",
    known_profile_yaml=load("merchants/de/rewe/profile.yaml")
)

if result.profile_assessment.failed_patterns:
    # Profil-Update nötig → automatischer Issue im forager-merchants Repo
    open_issue(...)
```

### Modus B — bekannter Händler ohne Profil-Cache (Fresh Detection)

```python
result = receipt_assessor.run(
    receipt=receipt,
    repo_known_merchants=load_merchant_list()
)
# result.merchant.merchant_id wird vom Modell gesetzt, ohne YAML als Hilfe
```

### Modus C — unbekannter Händler

```python
result = receipt_assessor.run(receipt=receipt)
# result.merchant.identified = false
# result.merchant.proposal enthält suggested_id
# result.profile_assessment.profile_proposal enthält YAML-Stub
```

In Modus C produziert Forager automatisch einen PR-Vorschlag (siehe nächstes Dokument).
