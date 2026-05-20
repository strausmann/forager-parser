# Forager Merchants — PR & Issue Templates

**Pfad im Repo:** `.github/` (GitHub) bzw. `.gitlab/` (GitLab) — beides parallel pflegen.

---

## GitLab Merge Request Templates

### `.gitlab/merge_request_templates/merchant-new.md`

```markdown
<!--
🤖 Dieses Template wird typischerweise von der Forager-PWA automatisch befüllt.
Bei manueller Befüllung: jeder leere Block ist eine Frage an den Contributor.
-->

## 📍 Merchant
- **ID:** `<country>.<slug>`         <!-- z.B. de.rossmann -->
- **Name:**
- **Country:**                        <!-- DE, AT, CH -->
- **Parent chain:**                   <!-- (none) bei Markenhändlern, sonst z.B. de.edeka -->

## 🧾 Sample Evidence
- **Sample date:**                    <!-- YYYY-MM-DD des Bons -->
- **Sample location:**                <!-- Stadt, Straße -->
- **ZIP region:**                     <!-- erste 3 Ziffern, z.B. 212 -->
- **Federal state:**                  <!-- Niedersachsen, Hamburg, ... -->
- **Sample path:** `merchants/<country>/<merchant_id>/samples/<YYYY-MM-DD>-initial.txt`

## 📊 Coverage Statistics
| Metric | Value |
|---|---|
| Items in bon | |
| Multi-line items | |
| Weight items | |
| Pfand entries | |
| Discount entries | |
| Loyalty program | |

## ✅ Assessment Quality
- **Overall confidence:**             <!-- aus assessment.overall_confidence.overall -->
- **All lines covered:**              <!-- ✅ / ⚠ -->
- **Totals reconcile:**               <!-- ✅ / ⚠ -->
- **Novel observations:**             <!-- Anzahl -->
- **PII detected and redacted:**      <!-- ✅ -->

## 🔍 Anonymization Verification
- [ ] No full credit card numbers
- [ ] No customer IDs (PAYBACK, store loyalty)
- [ ] No cashier full names
- [ ] No email addresses (other than the merchant's public email)
- [ ] No phone numbers other than the merchant's public number

## 📁 Files Added
- [ ] `merchants/<country>/<merchant_id>/profile.yaml`
- [ ] `merchants/<country>/<merchant_id>/samples/<YYYY-MM-DD>-initial.txt`
- [ ] `merchants/<country>/<merchant_id>/samples-meta/<YYYY-MM-DD>-initial.assessment.json`
- [ ] `merchants/<country>/<merchant_id>/tests/parse_test.yaml`
- [ ] `merchants/<country>/<merchant_id>/CHANGELOG.md`

## 🧪 Test Coverage
Each line kind from the sample has at least one expectation in `parse_test.yaml`:
- [ ] simple_item
- [ ] inline_quantity (falls vorhanden)
- [ ] multiline_quantity (falls vorhanden)
- [ ] inline_weight (falls vorhanden)
- [ ] multiline_weight (falls vorhanden)
- [ ] pfand_* (falls vorhanden)
- [ ] discount/coupon (falls vorhanden)

## 📝 Notes for Reviewers
<!-- Auffälligkeiten, die der Maintainer wissen sollte. Z.B.: -->
<!-- "Dieser Händler nutzt ein Sub-Layout, das von de.edeka erbt." -->
<!-- "Der Sample-Bon hat eine ungewöhnliche Position 7 (Sonderaktion)." -->

---
/label ~"merchant:new"
```

### `.gitlab/merge_request_templates/merchant-variant.md`

```markdown
## 📍 Variant
- **Base merchant:** `<base_merchant_id>`     <!-- z.B. de.rewe -->
- **Variant ID:** `<base>.<region-slug>`      <!-- z.B. de.rewe.region-212 -->
- **Variant kind:**
  - [ ] Regional (different ZIP/state)
  - [ ] Layout era (timeframe-based)
  - [ ] Store format (Express, City, Center, ...)

## 🗺️ Applicability
- **ZIP regex:** `^\d{5}$`                     <!-- z.B. ^212\d{2}$ -->
- **Cities:**                                  <!-- Liste, falls eng begrenzt -->
- **Valid from:**                              <!-- YYYY-MM-DD -->
- **Valid until:**                             <!-- (open) oder YYYY-MM-DD -->

## 🔬 Evidence for Variant
**This variant is justified because at least 3 independent receipts show
the same drift signal from the base profile in the same region.**

| Sample File | Date | Location | Drift Signal |
|---|---|---|---|
| `samples/2026-05-20-...txt` | 2026-05-20 | Maschen | failed_pattern: rewe_weight_item |
| `samples/2026-04-15-...txt` | 2026-04-15 | Seevetal | failed_pattern: rewe_weight_item |
| `samples/2026-03-10-...txt` | 2026-03-10 | Buchholz | failed_pattern: rewe_weight_item |

(Drift-Observations aus Forager-DB als Quelle, siehe PR-Workflow §Drift)

## 🧬 What Differs from Base
<!-- Konkrete Felder, die der Variant überschreibt. -->
- `layout.item_layout.primary_pattern` — Toleranz für 1 statt 2 Leerzeichen
- `loyalty.earned_coupons.coupon_pattern` — anderes Coupon-Format

## 📁 Files Added
- [ ] `merchants/<country>/<base_merchant_id>/variants/<variant-slug>.yaml`
- [ ] `merchants/<country>/<base_merchant_id>/samples/<dates>-...txt` (3+ neue Samples)
- [ ] `merchants/<country>/<base_merchant_id>/samples-meta/*.assessment.json`
- [ ] `merchants/<country>/<base_merchant_id>/tests/parse_test.variant-<slug>.yaml`
- [ ] CHANGELOG update

---
/label ~"merchant:variant"
```

### `.gitlab/merge_request_templates/merchant-layout-update.md`

```markdown
## 📅 Layout Change Detection
- **Merchant:** `<merchant_id>`
- **Existing profile version:** `<git-sha-or-tag>`
- **First observed change date:** <!-- wann tauchte das neue Layout das erste Mal in einem Bon auf? -->
- **Number of receipts with new layout:** <!-- Drift-Observations aus Forager-DB -->

## 🔄 What Changed
<!-- Klare Beschreibung, was am Layout anders ist: -->
<!-- "Der PAYBACK-Block wurde durch einen REWE-Bonus-Block ersetzt." -->
<!-- "Wiegeartikel-Format hat sich von 'X,XXX kg x Y,YY EUR/kg' zu 'X,XXXkg × Y,YY' geändert." -->

## 🧓 Backward Compatibility
- **Old profile name:** `profile.yaml` (wird zu `profile.v1.yaml` umbenannt)
- **New profile name:** `profile.v2.yaml` (oder weiterhin `profile.yaml`, abhängig von Strategie)
- **Cutover date in profile_validity.valid_from:** `<YYYY-MM-DD>`
- **Old samples still parseable by old profile:** [ ]

## 🧪 Test Evidence
- [ ] Old samples (pre-cutover) work with old profile
- [ ] New samples (post-cutover) work with new profile
- [ ] No mixed samples (a single bon must clearly belong to one era)

## 📁 Files Modified
- [ ] `merchants/<country>/<merchant_id>/profile.v2.yaml` (new)
- [ ] `merchants/<country>/<merchant_id>/profile.yaml` → `profile.v1.yaml` (rename)
- [ ] `merchants/<country>/<merchant_id>/samples/` (new post-cutover samples)
- [ ] `merchants/<country>/<merchant_id>/tests/parse_test.v2.yaml` (new)
- [ ] CHANGELOG update with cutover rationale

---
/label ~"merchant:layout-update"
```

### `.gitlab/merge_request_templates/merchant-fix.md`

```markdown
## 🐛 Bug Description
**What went wrong:**
<!-- Konkrete Zeile aus einem Bon, die nicht korrekt geparst wurde. -->

**Expected behavior:**
<!-- Was hätte das Forager-Assessment liefern sollen? -->

**Actual behavior:**
<!-- Was hat es geliefert? Verweis auf assessment.json. -->

## 🔬 Reproduction
- **Sample with bug:** `merchants/<country>/<merchant_id>/samples/<file>.txt`
- **Assessment showing bug:** `merchants/<country>/<merchant_id>/samples-meta/<file>.assessment.json`
- **Line(s) affected:** `parse_test.yaml` line numbers <X> through <Y>

## 🔧 Fix Applied
**Field changed:** `<yaml-path>`
**Before:**
```yaml
[old value]
```
**After:**
```yaml
[new value]
```

**Why this fix works:**
<!-- Erklärung — warum löst die Regex-Änderung den Bug? -->

## 🧪 Regression Coverage
- [ ] Existing tests still pass (CI checks `regression-suite`)
- [ ] New test added that would have caught this bug:
  - `tests/parse_test.yaml` includes a case for the previously-failing line

## 📁 Files Modified
- [ ] `merchants/<country>/<merchant_id>/profile.yaml` (the fix)
- [ ] `merchants/<country>/<merchant_id>/tests/parse_test.yaml` (regression test)
- [ ] (optional) New sample if existing ones didn't cover this case
- [ ] CHANGELOG update

---
/label ~"merchant:fix"
```

### `.gitlab/merge_request_templates/heuristic.md`

```markdown
## 🧠 Heuristic
- **Type:** [ ] new  [ ] fix  [ ] enhancement
- **File:** `heuristics/<name>.yaml`
- **Applies cross-merchant:** [ ] all merchants  [ ] specific list

## 🎯 What Pattern Does It Address?
<!-- Z.B.: "Pfand-Erkennung erkennt bisher nicht EU-PFAND, das in einigen REWE-Bons vorkommt." -->

## 📋 Cross-Merchant Impact
**Affected merchants (verified):**
- [ ] de.rewe — Tests pass: [ ]
- [ ] de.lidl — Tests pass: [ ]
- [ ] de.knolles-markt — Tests pass: [ ]
- [ ] ...

**Affected merchants (untested but theoretically affected):**
<!-- Liste -->

## 🧪 Test Evidence
CI runs `cross-merchant-impact` job:
- [ ] No existing sample's assessment output changes UNexpectedly
- [ ] Where output changes, the change is intentional and verified

## 📁 Files Modified
- [ ] `heuristics/<name>.yaml`
- [ ] Affected merchant profiles' `parse_test.yaml` (if needed)
- [ ] CHANGELOG in repo root

---
/label ~"heuristic:new" ~"heuristic:fix" ~"heuristic:enhancement"
```

### `.gitlab/merge_request_templates/schema-proposal.md`

```markdown
## 📜 Schema Change RFC
**Schema affected:** [ ] `merchant-profile.v1.json`  [ ] `receipt-assessment.v1.json`  [ ] both

**Change type:**
- [ ] Add optional field (minor version bump)
- [ ] Add required field (major version bump)
- [ ] Modify existing field semantics (major bump)
- [ ] Deprecate field (major bump)

## 🎯 Motivation
**Problem statement:**
<!-- Was lässt sich heute nicht ausdrücken, das ausgedrückt werden müsste? -->

**Number of receipts that demonstrate the gap:**
<!-- Konkrete Sample-Bons aus dem Repo als Evidenz -->

## 📐 Proposed Change
```yaml
# Vorher
[old schema fragment]

# Nachher
[new schema fragment]
```

## 🤝 Migration Path
- **Existing profiles:** Wie müssen sie aktualisiert werden?
- **Existing assessments:** Bleiben sie valide? Falls nein, wie migrieren?
- **Existing tests:** Welche müssen aktualisiert werden?

## 🌍 Impact Analysis
- **Forager-Worker:** Welche Code-Änderungen sind nötig?
- **Forager-API:** Schema-Endpoints, ggf. Versions-Routing
- **Forager-PWA:** UI-Änderungen?

## ⏳ Rollout Plan
- [ ] Schema v<new> als Proposal in `schema/<name>.v<new>.draft.yaml`
- [ ] 14 Tage Diskussion-Phase
- [ ] Implementation in Worker hinter Feature-Flag
- [ ] Stichprobe von 10 Profilen migriert
- [ ] Schema-Bump als finaler PR

---
/label ~"schema:proposal" ~"rfc"
```

---

## GitLab Issue Templates

### `.gitlab/issue_templates/profile-problem.md`

```markdown
<!--
Wenn du einen Forager-PWA-Lauf für deinen Bon hast: bitte sende stattdessen
direkt einen PR. Templates dafür sind in den Merge-Request-Optionen.

Dieses Issue-Template ist für Fälle, in denen ein PR (noch) nicht möglich ist.
-->

## 🔍 Was war das Problem?
- [ ] Bon-Header (Händler) wurde nicht erkannt
- [ ] Items wurden falsch geparst (welche Zeilen?)
- [ ] Pfand wurde falsch zugeordnet
- [ ] Rabatt/Coupon wurde nicht erkannt
- [ ] Datum/Filiale falsch extrahiert
- [ ] Loyalty-Programm-Block ignoriert
- [ ] Steuerklassen-Zuordnung falsch
- [ ] Komplett neuer Händler, noch nicht im Repo
- [ ] Anderes (bitte beschreiben)

## 🏪 Händler
- **Name:**
- **Bekannte ID im Repo:** (z.B. `de.rewe`, oder "unbekannt")
- **Filiale:**

## 📝 Anonymisierter Bon-Text

⚠ **WICHTIG:** Bitte ALLES Folgende vor dem Einfügen ersetzen:
- Kartennummern → `############XXXX`
- Kunden-/PAYBACK-Nummern → `<CUSTOMER_ID>`
- Kassiererinnen-Namen → `<NAME>`

<details>
<summary>Bon-Text</summary>

```
[hier einfügen, NUR anonymisiert]
```
</details>

## 📊 Forager Assessment (falls verfügbar)

<details>
<summary>JSON</summary>

```json
[paste from Forager PWA]
```
</details>

## 🎯 Was wäre korrekt?
<!--
Beschreibe konkret, wie das Assessment aussehen sollte.
NICHT: "Da fehlt was."
SONDERN: "Zeile 7 ('PFAND EINWEG 0,25') ist eine Pfand-Position
zu Zeile 6 (Coca-Cola 1,5L), nicht ein eigenständiges Item."
-->

## 🌐 Region & Layout-Hinweise
- **PLZ-Region:**
- **Bundesland:**
- **Bon-Datum:**

---
/label ~"triage" ~"profile-issue"
```

### `.gitlab/issue_templates/new-merchant-request.md`

```markdown
## 🏪 Händler, der ins Repo soll
- **Name:**
- **Land:** DE / AT / CH
- **Ist eine Kette?** ja/nein
- **Parent-Chain (falls Sub-Marke):** z.B. de.edeka

## 🔗 Öffentliche Referenzen
- Website:
- Filial-Finder:
- Beispiel-Adresse einer Filiale:

## 🧾 Bon-Sample
<!-- Wie beim profile-problem-Template: anonymisierter Text. -->

<details>
<summary>Bon-Text</summary>

```
[hier]
```
</details>

## 📊 Forager Assessment (empfohlen)
<details>
<summary>JSON</summary>

```json
[paste]
```
</details>

## 🎁 Besonderheiten
- [ ] Eigenes Loyalty-Programm:
- [ ] Multi-Line-Items:
- [ ] Pfand-System: einweg/mehrweg/beides
- [ ] Wiegeartikel:
- [ ] Sonderzeichen mit Bedeutung:
- [ ] Mehrsprachige Bons:
- [ ] Sonstiges:

---
/label ~"triage" ~"merchant-request"
```

### `.gitlab/issue_templates/drift-report.md`

```markdown
## 📉 Drift Beobachtung
Wenn Forager-PWA wiederholt drift_detection meldet für denselben Händler.

**Merchant ID:** `<id>`
**Anzahl betroffener Bons:** 
**Zeitraum der ersten Beobachtung:** YYYY-MM-DD bis YYYY-MM-DD
**ZIP-Regionen betroffen:**

## 🔍 Drift-Signale aus Forager-Assessments
| Bon Date | Location | Drift Kind | Detail |
|---|---|---|---|
| | | | |

## 💭 Vermutete Ursache
- [ ] Saisonale Layout-Variante (Aktionswochen, Feiertage)
- [ ] Permanente Layout-Änderung (z.B. neues Kassen-System)
- [ ] Regionale Sub-Variante
- [ ] Kassen-Software-Update mit anderem Druck-Format
- [ ] Unklar

## 🛣️ Vorgeschlagener Weg
- [ ] `merchant:layout-update` PR (permanenter Wechsel)
- [ ] `merchant:variant` PR (regional/zeitlich begrenzt)
- [ ] `merchant:fix` PR (Bug im bestehenden Profil)
- [ ] Weiter beobachten (zu wenig Datenpunkte)

---
/label ~"triage" ~"drift"
```

---

## CODEOWNERS

`.gitlab/CODEOWNERS` (oder GitHub-Äquivalent):

```
# Alle Profile brauchen Maintainer-Review
/merchants/                 @maintainers

# Schema-Änderungen brauchen Schema-Maintainer
/schema/                    @schema-maintainers
/prompts/                   @schema-maintainers

# Heuristiken brauchen besondere Sorgfalt wegen cross-merchant impact
/heuristics/                @maintainers @schema-maintainers

# Docs offen für alle Maintainer
/CONTRIBUTING.md            @maintainers
/README.md                  @maintainers
*.md                        @maintainers

# Tests von jedem Maintainer reviewbar
/**/tests/                  @maintainers
```

---

## Naming-Conventions

| Element | Convention | Beispiel |
|---|---|---|
| Merchant ID | `<country>.<lowercase-slug>` | `de.knolles-markt` |
| Variant ID | `<merchant-id>.<region-slug>` | `de.rewe.region-212` |
| Sample filename | `<YYYY-MM-DD>-<short-descriptor>.txt` | `2026-05-20-maschen-default.txt` |
| Assessment filename | `<sample-filename>.assessment.json` | `2026-05-20-maschen-default.assessment.json` |
| Variant filename | `<descriptor>.yaml` | `region-212.yaml` |
| Profile version filename | `profile.v<N>.yaml` | `profile.v2.yaml` |
| Test filename | `parse_test.yaml` oder `parse_test.<descriptor>.yaml` | `parse_test.variant-212.yaml` |
| Pattern ID (in YAML) | `<merchant-short>.<pattern-purpose>` | `rewe.weight_item` |

---

## Quick-Start für Contributor

> "Ich möchte einen neuen Händler einreichen, was muss ich tun?"

### Variante A: über Forager-PWA (empfohlen)

1. Bon scannen oder PDF hochladen
2. Im Assessment-Screen "Diesen Händler ins Repo vorschlagen" klicken
3. PWA generiert anonymisierten Sample, Assessment, Profil-Stub, Test, CHANGELOG
4. PWA öffnet PR im `forager-merchants`-Repo (via GitLab-API oder lokales Git-Clone)
5. Maintainer reviewt und merged

### Variante B: manuell

1. Repo forken
2. `merchants/<country>/<merchant_id>/` anlegen
3. Sample-Bon anonymisieren und unter `samples/` ablegen
4. Forager-PWA gegen den Sample laufen lassen → `samples-meta/<file>.assessment.json` erzeugen
5. `profile.yaml` aus `profile_assessment.profile_proposal.yaml` ableiten
6. `tests/parse_test.yaml` schreiben (mindestens jede Item-Klasse hat 1 Erwartung)
7. CHANGELOG.md anlegen
8. PR mit Template `merchant:new` öffnen

In beiden Varianten gilt: ohne Assessment-JSON wird der PR von CI abgelehnt — das ist die Garantie für Strukturkonstanz.
