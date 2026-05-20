# Bon-Validierung — Befunde gegen Konzept v0.2

**Datum:** 20. Mai 2026
**Test-Bons:**
- REWE Markt, Schulstraße 46-48, 21220 Maschen (PDF, 20.05.2026)
- Lidl, Heibensweg 3, 21220 Seevetal-Maschen (Foto, 19.05.2026)
- Knolles Markt OHG (Edeka), Ohlendorfer Str. 3, 21220 Seevetal (PDF, 09.05.2026)

---

## Was im Konzept v0.2 schon passt

| Aspekt | Status |
|---|---|
| Drei-Schicht-Lernmodell (Layout/Alias/Heuristik) | ✓ trägt |
| Versionierung via Git-Repo | ✓ trägt |
| `receipt_lines.raw_text` immer behalten | ✓ kritisch wichtig (verifiziert an Knolles' "Fisherm.Frien" OCR-Fehler) |
| Multi-Line-Items mit `primary`/`secondary` | ✓ trägt für REWE |
| Pfand als Kind-Position via `parent_line_id` | ✓ trägt für REWE-Stil |
| Idempotenz-Hash | ✓ Felder vorhanden, alle drei Bons hashbar |

---

## Was nachgezogen werden muss

### 1. Tax-Klassen sind nicht universell — pro Händler ins Profil

**Befund:**
- REWE-Bon: `B = 7%` (kein A im Beispiel sichtbar)
- Lidl-Bon: `A = 7%, B = 19%`
- Knolles-Bon: `A = 7%, B = 19%`

**Konsequenz:**
- `heuristics/mwst-categories.yaml` (Konzept Section 20.4) ist zu pauschal
- Stattdessen `tax_classes:` als Block **pro Händler** im `profile.yaml`
- Hinweis im Hauptdoku Section 20.5 ergänzen

**Profil-Snippet:**
```yaml
# REWE
tax_classes:
  A: { rate: 0.19, description: "19% Standard" }
  B: { rate: 0.07, description: "7% Lebensmittel" }

# Lidl
tax_classes:
  A: { rate: 0.07, description: "7% Lebensmittel" }
  B: { rate: 0.19, description: "19% Standard" }
```

### 2. Pfand hat drei Varianten, nicht eine

**Befund:**
- **REWE-Stil (Konzept-Annahme):** Item-Zeile + Pfand-Folgezeile
- **Lidl-Aggregat-Stil:** `Pfand 0,25 EM  0,25 x 24   6,00 B` — eine Zeile für 24× Pfand
- **Lidl-Rückgabe-Stil:** `Pfandrückgabe  -3,75 B` mit `-15 x  0,25` in Folgezeile — eigenständige negative Buchung
- **Knolles-Stil:** `Pfand  0,25*B` — das `*` bedeutet "nicht rabattberechtigt" (PAYBACK-relevant)

**Konsequenz:**
- `pfand:` im Profil-Schema unterstützt jetzt mehrere `detection:`-Patterns mit `kind:` und `attach_to:`
- Neue Buchungslogik in Section 20.10: Pfand-Aggregate werden in Grocy als separate Pfand-Position gebucht, *nicht* als Modifier der Item-Position
- Pfandrückgabe ist eigenständige Buchung mit negativem Vorzeichen — als Grocy-Stock-Reduction beim Pfand-Produkt

**Erweiterung Profil-Schema:**
```yaml
pfand:
  detection:
    - id: <unique-id>
      regex: <pattern>
      secondary_regex: <optional>        # für Pfandrückgabe-Folgezeilen
      kind: pfand_einweg | pfand_mehrweg | pfand_einweg_aggregate | pfand_return
      attach_to: previous_item | previous_item_group | none
      negate_amount: false               # für Rückgaben
      flags: [not_rebate_eligible, ...]
```

### 3. Wiegeartikel-Layout ist NICHT einheitlich zwischen Händlern

**Befund:**
- **REWE:** Gesamtsumme + Tax in Zeile 1, "kg x EUR/kg" in Zeile 2 — Zeile 2 ohne Tax-Marker
  ```
  ERDBEERE                          2,73 B
    0,490 kg x   5,58 EUR/kg
  ```
- **Lidl:** Name enthält "kg", Gesamtsumme + Tax in Zeile 1, "kg x EUR/kg" in Zeile 2
  ```
  Erdbeeren kg                      2,23 A
    0,448 kg x 4,98   EUR/kg
  ```

**Konsequenz:**
- Profil-Schema braucht `total_in_line: primary | secondary | both`
- Profil-Schema braucht `name_post_strip:` als Liste von Regexen, die vom Namen entfernt werden (z.B. "kg" am Ende bei Lidl)

### 4. Mengenartikel-Notation variiert stark

**Drei beobachtete Varianten:**

| Händler | Beispiel | Notation |
|---|---|---|
| REWE | `ESL MILCH 3,5%   1,90 B` + Folgezeile `2 Stk x 0,95` | zweizeilig, "Stk x Einzelpreis" |
| Lidl | `Milk/Schoko Bits  2,79 x  2   5,58 A` | einzeilig, "Einzelpreis x Stk Total" |
| Knolles | `G&G Multipack  2,55 € x  3   7,65 A` | einzeilig, "Einzelpreis € x Stk Total" |

**Konsequenz:**
- Profil-Schema braucht `single_line: true` als Flag
- Profil-Schema braucht in Mengen-Items optionales `currency_in_pattern: true | false`

### 5. Loyalty-Programme sind eigene Entität

**Befund:**
- REWE: REWE Bonus → Coupon für Folgeeinkauf
- Knolles: PAYBACK → Punkte-Gutschrift
- Lidl: Lidl Plus möglich, im Beispiel-Bon nicht aktiv

**Konsequenz:**
- Neuer Block `loyalty:` im Profil-Schema (verschiedene Programme)
- Neue Tabelle `receipt_loyalty_events` im Datenmodell:

```sql
CREATE TABLE receipt_loyalty_events (
    id              UUID PRIMARY KEY,
    receipt_id      UUID NOT NULL REFERENCES receipts(id),
    program         TEXT NOT NULL,       -- 'rewe_bonus', 'payback', 'lidl_plus'
    event_kind      TEXT NOT NULL,       -- 'earned_points', 'earned_coupon', 'redeemed', 'balance_info'
    amount          NUMERIC(10,2),       -- EUR oder Punkte
    points          INT,                  -- nur bei Punkte-Programmen
    target          TEXT,                 -- 'Tulip Fl' bei REWE-Coupon
    expires_at      DATE,
    metadata        JSONB
);
```

- Wichtig: Bei der Privacy-Bereinigung müssen masked card numbers (`******1373`) und Kundennummern (`630436172`) auf jeden Fall raus, **bevor** der Bon ins Forager-Merchants-Repo wandert. Aktuelle `privacy:` im Knolles-Profil deckt das ab.

### 6. Adresse/Filiale-Extraktion: kontextabhängig

**Befund:**
- REWE: Adresse direkt unter Logo, dann Telefon, dann UID
- Lidl: Adresse direkt unter Logo, dann **direkt** der Item-Block (kein Telefon im Header)
- Knolles: Adresse → Telefon → leere Zeile → Items

**Konsequenz:**
- `header_line_N`-Positionsangaben sind fragil
- Besser: pro Erkennung erlauben `from_section: header`, dann strukturierte Patterns mit Reihenfolge-Hinweis
- Mein Profil-Entwurf nutzt schon `position: header_line_2` — das sollte ich konsistenter als `section + ordering` modellieren

### 7. Cashier-Namen sind PII und müssen anonymisiert werden

**Befund:**
- Knolles: "Es bediente Sie: Frau Jürgens" — voller Name auf dem Bon
- REWE: Bedienernummer "Bed.:616161" — anonymer Code, ok
- Lidl: keine Bedienerangabe sichtbar

**Konsequenz:**
- Anonymisierungs-Helfer (Section 20.18) muss `cashier_name` als PII-Feld behandeln
- Profil-Schema hat jetzt `privacy.fields_to_anonymize:` mit `cashier_name`

### 8. Bon-Trailer-Felder mit Beleg-Metadaten

Alle drei Bons haben eine andere Struktur für Datum/Zeit/Beleg-Metadaten:

| Händler | Format |
|---|---|
| REWE | `Datum:` und `Uhrzeit:` als separate Zeilen im Kundenbeleg |
| Lidl | Inline-Trailer: `5417   023002/81              19.05.26 08:23` |
| Knolles | Tabellarisch mit Header-Zeile: `Datum Uhrzeit Filiale Pos Bed Bon` + Werte-Zeile darunter |

**Konsequenz:**
- `date_extraction.patterns:` muss eine **Liste mit Priorität** sein
- Erste passende Variante gewinnt
- Fallback immer: TSE-Timestamp (ISO 8601)

### 9. Edeka-Sub-Marken erfordern Profil-Vererbung

**Befund:**
- Knolles Markt OHG ist ein selbständiger Edeka-Markt
- Andere Edeka-Märkte (Edeka Center, Marktkauf, E neukauf) haben Variationen
- Eine flache `de.<chain>`-Struktur skaliert nicht

**Konsequenz:**
- Profil-Schema erweitern um `extends: <parent_profile_id>`
- Felder im Kind-Profil überschreiben die Eltern-Felder
- Beispiel: `de.knolles-markt` erbt von `de.edeka`, überschreibt `merchant.name`, `merchant.detection`, ergänzt `loyalty.program: PAYBACK`

**Repo-Struktur überarbeiten:**
```
merchants/
├── de/
│   ├── _base/
│   │   └── edeka.yaml              # gemeinsame Edeka-Konventionen
│   ├── edeka/
│   │   └── profile.yaml            # Edeka-eigene Filialen
│   ├── knolles-markt/
│   │   └── profile.yaml            # extends: de._base.edeka
│   ├── rewe/
│   ├── lidl/
│   ├── aldi-nord/
│   └── aldi-sued/
```

### 10. Konvention "OCR-Variationen"

**Befund Knolles-Bon:**
- "Fisherm.Friend" steht voll auf dem Bon, OCR liest "Fisherm.Frien" (letztes "d" verschluckt)
- Im Profil habe ich beide Varianten aufgenommen

**Konsequenz:**
- Profile sollten häufige OCR-Variationen tolerieren
- `abbreviations:` als regex-basiertes Fuzzy-Mapping erweitern
- Oder: `aliases:` als separater Block, der "wenn das im OCR steht, behandle es wie diesen kanonischen Namen"

---

## Anpassungen für Konzept v0.3

Folgende Sections des Hauptkonzepts brauchen Updates:

| Section | Änderung |
|---|---|
| **20.4** Repo-Struktur | `_base/`-Subdirs für Profil-Vererbung ergänzen |
| **20.5** Profil-Schema | `tax_classes:`, `extends:`, `name_post_strip:`, `total_in_line:`, `single_line:`, `privacy:` ergänzen |
| **20.6** Datenmodell | Tabelle `receipt_loyalty_events` ergänzen |
| **20.10** Pfand-Behandlung | Drei Pfand-Varianten beschreiben (Item-Kind, Aggregat, Rückgabe) |
| **20.18** CI & Community | Privacy-Anonymisierung um cashier_name, masked_card erweitern |

---

## Konkrete TODOs

- [ ] Konzept v0.3 mit obigen Anpassungen
- [ ] Sample-Bons (anonymisiert) als Fixtures im `forager-merchants`-Repo ablegen
- [ ] `parse_test.yaml` für Lidl und Knolles äquivalent zum REWE-Test schreiben
- [ ] Profil-Schema als JSON-Schema in `schema/merchant-profile.v1.json` formalisieren
- [ ] Vererbungs-Logik (`extends:`) als Parser-Feature entwerfen
