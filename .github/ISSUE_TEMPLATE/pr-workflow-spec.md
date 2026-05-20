# Forager Merchants — PR Workflow Specification

**Status:** Standard
**Version:** 1.0
**Pfad im Repo:** `CONTRIBUTING.md`

> Diese Spezifikation regelt, **wie** Änderungen am `forager-merchants`-Repo eingereicht werden. Ohne strukturierten Workflow wird das Repo unbrauchbar. Jeder PR muss reproduzierbar, evidenz-basiert und automatisch validierbar sein.

---

## Grundprinzip: PRs sind Daten, nicht Diskussionen

Ein PR im `forager-merchants`-Repo enthält **keine** Beschreibungen von "ich habe einen Bon, da steht es anders" — sondern **strukturierte Evidenz**, die automatisch verarbeitet werden kann:

1. Den **anonymisierten Bon-Text** als Fixture
2. Das **Assessment-Output** (Forager Receipt Assessment Schema v1) als JSON
3. Die **gewünschte Profil-Änderung** als YAML-Diff
4. Den **regenerierten Parse-Test**, der die Änderung absichert

Wenn diese vier Teile da sind, kann CI alleine entscheiden, ob die Änderung mergebar ist. Wenn nicht, kommt der Mensch ins Spiel — aber der Mensch arbeitet auf vorbereitetem Material, nicht auf einer freitext-Beschreibung.

---

## PR-Typen

Jeder PR muss genau **einen** Typ haben (Label im PR):

| Label | Bedeutung | Beispiel |
|---|---|---|
| `merchant:new` | Neuer Händler hinzufügen | Rossmann erstes Mal im Repo |
| `merchant:variant` | Regionale/Layout-Variante eines bestehenden Händlers | REWE Hamburg-Mitte hat anderes Layout als REWE Maschen |
| `merchant:layout-update` | Bestehender Händler hat Layout geändert | REWE Bonus-Block ersetzt PAYBACK-Block |
| `merchant:fix` | Bestehendes Profil hat einen Bug | Wiegeartikel-Regex matcht 3-stellige Gewichte nicht |
| `heuristic:new` | Neue händlerübergreifende Heuristik | Allgemeine Pfand-Erkennung erweitern |
| `heuristic:fix` | Heuristik-Bug | MwSt-Klasse falsch erkannt |
| `schema:proposal` | Schema-Erweiterung vorschlagen (RFC) | Neues Feld für Click-and-Collect-Bons |
| `docs` | Nur Dokumentation | Korrekturen, Erklärungen |

PRs ohne Label werden von CI mit "missing-label" geschlossen.

---

## Welche PR-Typen erlauben WAS?

| Typ | Erstellt PR automatisch? | Mensch-Review nötig? | Wer kann mergen? |
|---|---|---|---|
| `merchant:new` | ja, aus Forager-PWA via "unbekannter Händler" | ja | Maintainer |
| `merchant:variant` | ja, bei systematischer Drift erkannt | ja | Maintainer |
| `merchant:layout-update` | ja, bei drift_detection.severity=high | ja | Maintainer |
| `merchant:fix` | meist manuell | ja | Maintainer |
| `heuristic:*` | manuell | ja | Maintainer |
| `schema:proposal` | manuell | ja (RFC-Prozess) | Maintainer-Konsens |
| `docs` | manuell | leicht | jeder Contributor |

---

## Standard-PR-Struktur

Jeder PR (außer `docs`) folgt **exakt** dieser Datei-Struktur:

```
merchants/<country>/<merchant_id>/
├── profile.yaml                    # geänderte oder neue Datei
├── samples/
│   └── <date>-<layout-variant>.txt    # Anonymisierter Bon (Pflicht)
├── samples-meta/
│   └── <date>-<layout-variant>.assessment.json   # Receipt Assessment Schema v1 Output (Pflicht)
├── tests/
│   └── parse_test.yaml                # Erweitert um Test für diesen Sample (Pflicht)
└── CHANGELOG.md                       # Eintrag für diese Änderung (Pflicht)
```

CI verweigert den PR, wenn eine Pflicht-Datei fehlt.

---

## Was anonymisiert werden MUSS

Vor jedem Upload eines Sample-Bons MÜSSEN folgende Felder im `samples/`-Text ersetzt werden:

| Originaltyp | Ersetzen durch |
|---|---|
| Maskierte Kartennummer (`############6356`) | `############XXXX` |
| Vollständige Kartennummer | komplett entfernen |
| Kundennummer/Kunden-ID (PAYBACK, REWE-App, etc.) | `<CUSTOMER_ID>` |
| Vor-/Nachnamen (Kassierer, Käufer) | `<NAME>` |
| Personalnummer Kassierer (≥6 Stellen) | `<CASHIER_ID>` |
| Trace-/Beleg-Nummern, EMV-Daten | unverändert lassen (nicht-PII, aber relevant fürs Layout) |
| TSE-Signaturen, Prüfwerte | unverändert lassen |
| Adresse des Geschäfts | unverändert lassen (öffentlich) |
| Telefonnummer des Geschäfts | unverändert lassen (öffentlich) |
| UID-/Steuernummer | unverändert lassen (öffentlich) |

**Anonymisierungs-Helfer**: Die Forager-PWA hat einen Schritt "Profil-Problem melden", der das automatisch macht. Bei manuellen Beiträgen muss CI prüfen, dass keine offensichtlichen PII-Muster im Sample-Text vorkommen — ein Pattern wie `\d{4}\s*-\s*\d{4}\s*-\s*\d{4}\s*-\s*\d{4}` (Vollständige Kreditkartennummer) führt zum Auto-Reject.

---

## Workflow für `merchant:new`

### Auslöser
Forager-PWA erkennt einen Bon, dessen Händler nicht in `repo_known_merchants` ist.
Der User klickt im Assessment-Screen auf **"Diesen Händler dem Repo vorschlagen"**.

### Was Forager automatisch macht

1. Anonymisiert den OCR-Text gemäß Liste oben
2. Speichert ihn als `samples/<YYYY-MM-DD>-initial.txt`
3. Speichert das Receipt Assessment Output als `samples-meta/<YYYY-MM-DD>-initial.assessment.json`
4. Generiert aus `profile_assessment.profile_proposal.yaml` ein initiales `profile.yaml`
5. Generiert einen initialen `tests/parse_test.yaml`-Eintrag, dessen Erwartungswerte aus dem Assessment kommen
6. Erstellt CHANGELOG.md mit:
   ```
   ## [Initial] – YYYY-MM-DD
   ### Added
   - Profile for <Merchant Name> (<merchant_id>), based on receipt from <city>.
   - Sample: <date>-initial.txt
   - Initial confidence: <overall_confidence.overall>
   ```
7. Öffnet einen PR mit Label `merchant:new` und Titel `New merchant: <merchant_id>`

### Was die PR-Beschreibung enthält

Genau dieser Template-Block, **automatisch befüllt**:

```markdown
## Merchant
- ID: `de.rossmann`
- Name: Rossmann
- Country: DE
- Parent chain: (none)

## Sample
- Date: 2026-05-20
- Location: Rossmann, Beispielstraße 1, 21220 Maschen
- ZIP region: 212
- Federal state: Niedersachsen

## Coverage in Sample
- Items: 12
- Multi-line items: 0
- Weight items: 0
- Pfand entries: 2 (pfand_child)
- Loyalty: PAYBACK

## Assessment Quality
- Overall confidence: 0.94
- All lines covered: ✅
- Totals reconcile: ✅
- New patterns discovered: 0
- Novel observations: 0

## Profile Proposal
Generated from: `samples-meta/2026-05-20-initial.assessment.json`
See: `merchants/de/rossmann/profile.yaml`

## Tests
See: `merchants/de/rossmann/tests/parse_test.yaml`

---
🤖 Auto-generated by Forager PWA v<version> on behalf of contributor.
Anonymization performed: ✅ (see CONTRIBUTING.md § Anonymization)
```

### Maintainer-Review-Checkliste

Maintainer prüft:
- [ ] Sample ist tatsächlich anonymisiert (Stichprobe)
- [ ] `profile.yaml` folgt dem Standard-Schema (CI macht das, Maintainer verifiziert)
- [ ] Parse-Test deckt alle Item-Typen ab
- [ ] CHANGELOG ist sinnvoll formuliert
- [ ] Keine sensitiven Bilder hochgeladen (es dürfen nur `.txt` und strukturierte Files committet werden)

Wenn alles passt: Merge. Wenn nicht: Maintainer kommentiert konkret, Forager-PWA kann den Vorschlag re-generieren und der PR wird aktualisiert.

---

## Workflow für `merchant:variant` — Regionale Varianten

### Das Problem konkret

> "Ein REWE in 21220 verwendet anderes Format als ein REWE in Hamburg oder in Mitteldeutschland."

### Lösung: Variant-Profile mit `extends:`

Im Repo:

```
merchants/de/rewe/
├── profile.yaml                          # Basis-Profil, gilt für alle REWE-Bons
├── variants/
│   ├── 21220-niedersachsen.yaml          # Region-spezifische Überschreibungen
│   ├── 20-hamburg.yaml                   # PLZ 20xxx
│   └── 04-leipzig.yaml                   # PLZ 04xxx (Mitteldeutschland)
├── samples/
│   ├── 2026-05-20-maschen.txt
│   ├── 2026-04-15-hamburg-mitte.txt
│   └── 2026-03-10-leipzig.txt
├── samples-meta/
│   └── *.assessment.json
└── tests/
    ├── parse_test.base.yaml
    └── parse_test.variant-21220.yaml
```

Ein Variant-Profil enthält **nur die Unterschiede** zum Basis-Profil:

```yaml
# merchants/de/rewe/variants/21220-niedersachsen.yaml
schema_version: 1
extends: de.rewe
variant_id: de.rewe.region-212
applies_to:
  zip_regex: '^212\d{2}$'
  cities: ["Maschen", "Seevetal", "Buchholz", "Winsen"]

# Überschreibt nur die Felder, die regional anders sind:
layout:
  item_layout:
    primary_pattern: |
      ^(?P<name>[A-ZÄÖÜ][A-ZÄÖÜ0-9./\-,\s!]{1,29}?)\s{2,}(?P<total>\d+,\d{2})\s+(?P<tax_class>[AB])\s*$

# Z.B. wenn in 212xx REWE-Märkten der Bonus-Block anders formatiert ist:
loyalty:
  earned_coupons:
    coupon_pattern: '^\s+(?P<value>\d+,\d{2})EUR\s+auf\s+(?P<target>.+?)\s+(?P<face_value>\d+,\d{2})\s+EUR\s*$'
```

### Wann wird ein Variant-PR ausgelöst?

Automatisch, wenn:
- Ein Receipt Assessment für einen bekannten `merchant_id` läuft
- **UND** `drift_detection.drift_detected = true`
- **UND** `drift_detection.severity = high` für ≥3 Bons aus derselben PLZ-Region
- **UND** noch kein Variant-Profil für diese Region existiert

Die "≥3 Bons aus derselben Region" verhindern, dass ein einzelner Sonderfall ein Variant-Profil erzeugt. Forager sammelt Drift-Signale in einer eigenen Postgres-Tabelle:

```sql
CREATE TABLE drift_observations (
    id              UUID PRIMARY KEY,
    merchant_id     TEXT NOT NULL,
    zip_region      TEXT NOT NULL,
    receipt_id      UUID NOT NULL,
    drift_kind      TEXT NOT NULL,
    drift_detail    JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Sobald 3+ Einträge mit gleichem `(merchant_id, zip_region, drift_kind)` vorliegen, schlägt Forager dem User vor: "Soll ein Variant-Profil für diese Region eingereicht werden?"

### Variant-Profil aktivieren

Forager-Worker lädt beim Receipt-Processing:
1. Basis-Profil `de.rewe`
2. Alle Variant-Profile, deren `applies_to.zip_regex` zur Bon-PLZ passt
3. Merged sie (Variant überschreibt Basis), wendet das Resultat an

Bei mehrfacher Übereinstimmung gewinnt der spezifischere Regex (längeres Match), bei Gleichstand alphabetisch (deterministisch).

---

## Workflow für `merchant:layout-update`

### Auslöser

Ein bekannter Händler hat sein Layout geändert. Symptome:
- Mehrere Bons mit `failed_patterns` derselben Pattern-ID
- `drift_detection.drift_reasons` enthält `missing_expected_marker` ODER `alternative_marker_found`

### Verhalten

Forager schlägt dem User vor, einen PR mit Label `merchant:layout-update` einzureichen. Wichtig: ein Layout-Update darf das alte Layout NICHT brechen, falls noch Bestands-Bons aus dem alten Format vorliegen. Daher:

```
merchants/de/rewe/
├── profile.yaml                      # weiterhin Basis (alt)
├── profile.v2.yaml                   # NEU: zukünftiges Layout
├── samples/
│   ├── 2025-12-01-pre-bonus-system.txt    # für altes Layout
│   └── 2026-05-20-with-bonus-system.txt   # für neues Layout
└── tests/
    ├── parse_test.v1.yaml
    └── parse_test.v2.yaml
```

Der Profil-Header bekommt eine Gültigkeits-Spanne:

```yaml
schema_version: 1
merchant:
  id: de.rewe
profile_validity:
  valid_from: 2026-02-01     # Datum der Layout-Änderung
  supersedes: profile.yaml   # alte Version bleibt für Bons vor diesem Datum gültig
```

Forager-Worker wählt das Profil anhand des Bon-Datums:

```python
def select_profile(merchant_id: str, receipt_date: date) -> Profile:
    candidates = load_all_profiles(merchant_id)
    valid_candidates = [
        p for p in candidates
        if p.valid_from <= receipt_date <= (p.valid_until or date.max)
    ]
    return max(valid_candidates, key=lambda p: p.valid_from)
```

---

## Workflow für `merchant:fix`

### Auslöser

Ein User meldet via PWA: "Mein Bon parst falsch". Anders als bei Drift ist das hier ein Bug im Profil, nicht ein neues Layout. Symptome:
- `parse_confidence` einzelner Zeilen unter 0.5, obwohl der Bon visuell sauber ist
- `failed_patterns` mit `possible_reason` gefüllt

### Was Forager automatisch macht

1. Sammelt den anonymisierten Sample
2. Sammelt das Assessment, inkl. der `failed_patterns`-Liste
3. Erstellt PR-Vorschlag mit:
   - `profile.yaml` als Diff (das alte Pattern mit Markierung "❌" + Vorschlag "✅")
   - Erweiterter `parse_test.yaml`, der genau die Zeile testet, die zuvor fehlschlug

### Beispiel-Diff

```yaml
# merchants/de/rewe/profile.yaml
item_layout:
  multiline_patterns:
    - id: rewe_weight_item
      primary: '^(?P<name>[A-ZÄÖÜ][A-ZÄÖÜ0-9./\-,\s]{1,29}?)\s{2,}(?P<total>\d+,\d{2})\s+(?P<tax_class>[AB])\s*$'
      # ❌ alt: '^\s{4,}(?P<weight>\d+,\d{3})\s*kg\s*x\s+(?P<price_per_kg>\d+,\d{2})\s*EUR/kg\s*$'
      # ✅ neu: zusätzlich Toleranz für 1-2 Leerzeichen-Einrückung
      secondary: '^\s{2,}(?P<weight>\d+,\d{3})\s*kg\s*x\s+(?P<price_per_kg>\d+,\d{2})\s*EUR/kg\s*$'
```

---

## CI-Validierungs-Schritte (jeder PR)

GitLab-CI-Pipeline mit folgenden Jobs:

### 1. `schema-validation` (Pflicht)
Validiert jedes geänderte `profile.yaml` gegen `schema/merchant-profile.v1.json`.

### 2. `anonymization-check` (Pflicht)
Prüft `samples/`-Texte auf PII-Muster:
- Vollständige Kreditkartennummern (16 Ziffern)
- E-Mail-Adressen (außer denen, die in `CONTRIBUTING.md`-Whitelist stehen)
- Telefonnummern, die nicht der Händler-Telefonnummer entsprechen
- Personalnummern als 6+ ungeschützte Ziffern in Kassiererzeilen

### 3. `parse-test-execution` (Pflicht)
Führt alle `parse_test.yaml`-Cases aus. Jede einzelne Erwartung muss erfüllt sein.

### 4. `regression-suite` (Pflicht)
Führt alle parse-tests **aller anderen Profile** im Repo aus, um sicherzustellen, dass die Änderung keine bestehenden Profile bricht (z.B. wenn jemand eine Heuristik ändert).

### 5. `coverage-check` (Pflicht für `merchant:new` und `merchant:variant`)
Prüft, dass das Sample ALLE in `profile.yaml` definierten Patterns trifft (mindestens je 1 Treffer). Ein Pattern ohne Treffer im Sample ist ein Warnsignal — entweder ist das Pattern überflüssig oder das Sample unvollständig.

### 6. `cross-merchant-impact` (Pflicht für `heuristic:*`)
Bei Heuristik-Änderungen: führt alle Receipt-Assessments aller Sample-Bons im Repo aus und meldet, wenn sich für irgendeinen Bon das Output ändert. Das ist die Spürnase gegen unbeabsichtigte Nebeneffekte.

### 7. `changelog-required` (Pflicht außer für `docs`)
Prüft, dass `CHANGELOG.md` des betroffenen Profils einen neuen Eintrag hat.

### 8. `lint` (informativ)
- YAML-Lint
- Regex-Lint (alle Regexes werden compiliert, ungültige fallen auf)
- Markdown-Lint für CHANGELOG

---

## Issue-Workflow (vor dem PR)

Wenn ein User noch keinen PR vorbereiten kann (z.B. weil kein Forager-PWA-Lauf vorliegt), kann ein **strukturiertes Issue** geöffnet werden. Das Issue-Template `ISSUE_TEMPLATE/profile-problem.yaml`:

```markdown
---
name: Profil-Problem (kein PR möglich)
about: Strukturierte Meldung eines Profil-Problems ohne Code-Vorschlag
labels: ["triage", "profile-issue"]
---

## Händler
- ID (falls bekannt): `de.???`
- Name:
- Filiale/Adresse:

## Was passiert?
- [ ] Bon wird nicht erkannt
- [ ] Items werden falsch geparst
- [ ] Pfand/Rabatte falsch zugeordnet
- [ ] Datum/Filiale falsch extrahiert
- [ ] Neuer Händler, der noch fehlt
- [ ] Sonstiges (bitte beschreiben)

## Anonymisierter Bon-Text
<details>
<summary>Bon-Text (CTRL+K zum Anonymisieren?)</summary>

```
[Bon-Text hier einfügen, NUR ANONYMISIERT]
```
</details>

## Assessment Output (falls Forager-PWA verfügbar)
<details>
<summary>JSON</summary>

```json
[paste assessment hier]
```
</details>

## Was wäre die korrekte Erwartung?
[Beschreibung, was DEIN konkreter Bon RICHTIG erfasst hätte]
```

Maintainer triagiert: 
- Wenn das Issue ein Forager-Assessment enthält und sauber anonymisiert ist → konvertiert es selbst in einen PR
- Wenn nicht, fordert er die fehlenden Teile an oder schließt mit `wontfix-incomplete`

---

## Wer kann was?

| Rolle | Rechte |
|---|---|
| **Anonymous** | Kann Issues öffnen, kein PR ohne Account |
| **Contributor** | Kann PRs öffnen mit allen Labels außer `schema:proposal` |
| **Reviewer** | Kann PRs reviewen, +1/-1 geben, aber nicht mergen |
| **Maintainer** | Kann mergen, kann Labels setzen, kann `schema:proposal` reviewen |
| **Schema-Maintainer** | Untergruppe der Maintainer, darf Schema-Änderungen mergen |

Maintainer- und Schema-Maintainer-Rollen sind im Repo-CODEOWNERS-File definiert.

---

## Release-Mechanik

Profile sind nicht "deployed" — sie werden nach Merge automatisch vom Forager-Updater eingelesen. Aber für reproduzierbare Bezugsstellen gibt es **Tagged Releases**:

```
v2026.05.20  - tagged auf master, monatlich
```

Forager-Instanzen pinnen typischerweise einen Tag, nicht `master`. Das gibt Stabilität und erlaubt Roll-Back, wenn ein Release-Tag einen Bug enthält.

Tag-Erstellung passiert automatisch via CI, wenn auf `master` gemergt wird UND der letzte Tag älter als 7 Tage ist UND die Pipeline grün ist.

---

## Zusammenfassung

Das Ganze hat ein klares Ziel: **kein freitext-Diskurs, sondern strukturierte Evidenz**. Wenn jeder PR mit (Sample, Assessment, Profil-Diff, Test) kommt, kann CI 90% der Arbeit machen und der Mensch reviewt die letzten 10% — Anonymisierung, sinnvolle CHANGELOG-Einträge, Plausibilität.

Das fügt sich nahtlos in deine bestehenden GitLab-Self-Managed-Workflows ein und ist dieselbe Philosophie wie deine MSP-Toolchain: deklarative Profile, Tests vor Deployment, Audit-Trail über Git-History.
