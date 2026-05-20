# Forager — Konzept v0.3

**Version:** 0.3 (Delta zu v0.2)
**Datum:** 20. Mai 2026
**Autor:** Björn Strausmann
**Status:** Draft für Review
**Verhältnis zu v0.2:** Dieses Dokument ergänzt und korrigiert v0.2. Sektionen, die hier nicht erwähnt sind, gelten unverändert weiter. Sektionen, die hier "(ersetzt §X aus v0.2)" tragen, ersetzen die alte Fassung vollständig.

---

## Änderungslog v0.2 → v0.3

| # | Änderung | Auslöser | Sektion |
|---|---|---|---|
| 1 | Profile-Vererbung mit `extends:` und regionalen Varianten | Drift-Analyse: REWE Hamburg vs Neu Wulmstorf vs Maschen | §2 |
| 2 | DSFinV-K / EKaBS / DFKA-Taxonomie als externe Referenz-Standards eingearbeitet | Recherche-Befund: offizieller deutscher Standard existiert bereits | §3 |
| 3 | Tax-Klassen-Buchstaben-Tabelle als Heuristik | Recherche: A/B sind händlerabhängig | §4 |
| 4 | Neue Pattern-Klassen aus realen Bons | 4 neue REWE-Bons aus 3 Filialen geparst | §5 |
| 5 | `discount_patterns` als Top-Level-Block im Profil-Schema | Frischerabatt-Pattern nötig | §5 |
| 6 | Drei-Schicht-Lernmodell um regionale Diskriminatoren erweitert | Befund: Sub-Marken (Knolles), selbständige (Piclum oHG), Filial-Layouts | §6 |
| 7 | Marktanalyse — existierende Lösungen, was Forager unterscheidet | Recherche-Befund: 5+ ähnliche Projekte existieren | §7 |
| 7b | **Strategie-Korrektur:** Keinen Outreach in Grocy-Issues — Code statt Konzept-Lobby | Realitäts-Check: Grocy-Maintainer hat Receipt-Scanning bewusst seit Issue #404 draußen; #2831 sieht KI-generiert aus und ist Teil eines Musters, das Maintainer frustriert | §7.2 |
| 8 | Live-Befunde aus 7-Bon-Lauf, was funktioniert, was nicht | Prototyp-Tests | §8 |
| 9 | Roadmap-Update | Realität nach Prototyp-Phase | §9 |
| 10 | **Selbstdisziplin-Regel:** Kein Konzept-Update v0.4 ohne Code-Fortschritt | KI-Konzept-Inflation in Open-Source-Issues vermeiden | §11 |

---

## 1. Erkenntnis-Übersicht aus der Recherche

Wir sind nicht allein. Aber wir sind **anders** — was sich bei näherem Hinschauen als Marktlücke entpuppt.

**Was existiert bereits:**

| Projekt | Stand | Was es macht | Was es nicht macht |
|---|---|---|---|
| [knipknap/receiptparser](https://github.com/knipknap/receiptparser) | 18 Commits, 23 Stars, schlafend | Tesseract + YAML-Configs, Deutschland-Fokus | Nur Company/Postal/Date/Sum — keine Positionen, kein Pfand, kein MwSt-Breakdown, kein PR-Workflow |
| [erinalbers/grocy-receipt-ocr](https://github.com/erinalbers/grocy-receipt-ocr) | Aktiv | Docker, Grocy-Integration, JSON-Config mit Regex-Processors pro Händler, Barcode-Matching | Keine Profil-Vererbung, kein strukturierter PR-Workflow, kein Drift-Detection |
| [Grocy Issue #2831](https://github.com/grocy/grocy/issues/2831) | Offen (Nov 2025) | Feature-Request "AI Receipt Scanning and Barcode Linking" — fast identische Architektur (JSON-Schema, learn-over-time, manual mapping einmalig, dann automatisch) | Bisher kein Code, nur Issue |
| [manuel-rw/grocy-scanner](https://github.com/manuel-rw/grocy-scanner) | Aktiv, .NET | EAN-only Barcode, Schweiz-Fokus, automatisches Anlegen ohne Mapping | Keine Bon-Verarbeitung |
| [Barcode Buddy](https://barcodebuddy-documentation.readthedocs.io/) | Aktiv, PHP | Barcode-Scanner-Integration für Grocy | Keine Bons, scanner-zentriert |
| [apocha.app](https://apocha.app/) | Kommerziell | "Expense tracker with ML-trained item categorization" — beste deutsche/österreichische Receipt-Erkennung | Closed-Source, eigenes Vendor-Lock-in, keine Grocy/Snipe-IT-Integration |
| [Asprise Receipt OCR](https://asprise.com/receipt-ocr/) | Kommerziell, API | Cloud-OCR-API, JSON-Output | Daten verlassen Haushalt, kostenpflichtig, kein Self-Hosting |

**Was Forager differenziert** (auch nach Realitätscheck):
1. **Explizite YAML-Profile pro Händler/Region/Layout-Ära** mit Vererbung (`extends:`) und Versionierung (`valid_from`/`valid_until`).
2. **Strukturierter PR-Workflow mit reproduzierbarer Evidenz** statt Freitext-Issues — siehe `pr-workflow-spec.md`.
3. **Drei-Schicht-Lernmodell**: globale Layout-Profile + nutzerlokale Produkt-Aliase + globale Heuristiken, sauber getrennt.
4. **Plugin-Architektur** geteilt mit Hangar (Creator/DepResolver/TaxonomyProvider) — Forager ist nicht "noch eine Receipt-App", sondern der Onboarding-Vorbau für ein Multi-Backend-Ökosystem (Snipe-IT + Grocy + Spoolman + ...).
5. **Auf DSFinV-K / EKaBS / DFKA-Taxonomie aufbauend** statt davon getrennt — siehe §3.

**Was wir übernehmen können:**
- knipknap's **YAML-Profile-Idee** (haben wir schon implementiert, aber sein Set an Patterns für `company/postal/date` ist eine sinnvolle Negativ-Liste: "weniger ist nicht genug")
- erinalbers' **JSON-Config-Schema für Regex-Processors** als Vergleichsbasis
- apocha's **per-User-Aliase-Modell** ("link item name to product once, future matches automatic") — das ist genau unsere Schicht 2

---

## 2. Profile-Vererbung und regionale Varianten (ersetzt §10.2 aus v0.2)

### 2.1 Befund aus den realen Bons

Die vier neuen REWE-Bons stammen aus drei verschiedenen Filialen mit drei unterschiedlichen Layout-Eigenheiten:

| Filiale | PLZ | Header | Markt-Typ | Adresse-Format | Besonderheiten |
|---|---|---|---|---|---|
| Maschen | 21220 | `REWE MARKT` | Eigenbetrieb (REWE Markt GmbH) | `Schulstraße 46-48` | Bekanntes Baseline-Layout |
| Hamburg-Überseequartier | 20457 | `REWE` + `REWE Jens Piclum oHG` | **Selbständig (oHG)** | `Überseeboulevard 7` (Westfield-Anhang) | Andere UID: `DE369701276` statt `DE812706034` |
| Neu Wulmstorf | 21629 | `R E W E` (spaced) | Eigenbetrieb | `Bahnhofstraße 65` | Frischerabatt-Position, mehrere PFAND-EURO-Marker |

Drei Erkenntnisse:

1. **REWE ist nicht REWE.** Es gibt selbständige Märkte (oHG mit eigener UID) und Eigenbetrieb-Märkte (REWE Markt GmbH). Beide drucken den Bon nach demselben Software-Layout, aber Header und UID weichen ab.
2. **Filial-Variationen sind real.** Was auf einem Bon vorkommt und auf einem anderen nicht (Frischerabatt, mehrfache PFAND-EURO-Positionen, Handeingabe-Wiegeartikel), ist nicht "Bug" sondern "anderer Filial-Workflow".
3. **PLZ ist nicht zwingend der Diskriminator.** Hamburg-Überseequartier (20457) und Neu Wulmstorf (21629) verhalten sich layout-technisch identisch — der relevante Diskriminator ist hier **Markt-Typ** (oHG vs GmbH-Eigenbetrieb), nicht PLZ. PLZ ist relevant für *andere* Drifts (siehe Edeka-Sub-Marken).

### 2.2 Profile-Vererbungsmodell

```
merchants/de/rewe/
├── profile.yaml                      # Basis-Profil (gilt für alle REWE-Bons, sofern kein Variant matcht)
├── variants/
│   ├── ohg-piclum.yaml              # extends: de.rewe; applies_to.merchant_legal_form: oHG
│   ├── region-20-hamburg.yaml       # extends: de.rewe; applies_to.zip_regex: '^20\d{3}$'  (falls nötig)
│   └── era-pre-bonus-2025.yaml      # extends: de.rewe; profile_validity.valid_until: 2026-02-01
├── samples/
│   ├── 2026-05-20-maschen.txt
│   ├── 2026-03-21-hamburg-ueberseequartier.txt
│   ├── 2026-04-25-neu-wulmstorf.txt
│   ├── 2026-04-29-maschen-euroelv.txt
│   └── 2026-05-02-maschen.txt
└── tests/
    ├── parse_test.yaml
    ├── parse_test_hamburg.yaml
    ├── parse_test_neu_wulmstorf.yaml
    ├── parse_test_maschen_euroelv.yaml
    └── parse_test_maschen_0502.yaml
```

**Variant-Selektoren** (in der `applies_to`-Sektion eines Variant-Profils, alle als AND verknüpft):

| Selektor | Beispiel | Wann passend |
|---|---|---|
| `zip_regex` | `^212\d{2}$` | Regional begrenztes Layout (Niedersachsen-Süd) |
| `merchant_legal_form` | `oHG` | Selbständige Märkte vs Eigenbetrieb |
| `uid_regex` | `^DE369\d{6}$` | Spezifische UID-Range (selten) |
| `cities` | `["Hamburg", "Bremen"]` | Stadtspezifisch |
| `store_id_regex` | `^7\d{3}$` | Filial-Cluster |
| `header_marker` | `REWE Markt GmbH` | Header-Variante als Diskriminator |

**Resolution-Reihenfolge:**
1. Lade Basis-Profil (`de.rewe`)
2. Filtere alle Variants, deren `applies_to`-Bedingungen alle erfüllt sind
3. Wende sie in Reihenfolge der Spezifität an (mehr matched Selektoren → später angewendet → höhere Priorität)
4. Bei Gleichstand: alphabetisch nach `variant_id` (deterministisch)
5. Profile-Validity-Check: `valid_from <= receipt_date <= (valid_until or ∞)`

**Wichtig:** Variant überschreibt nur die Felder, die er explizit nennt. Alles andere wird vom Parent geerbt. Das vermeidet duplizierten Wartungsaufwand.

### 2.3 Drift-getriebener Variant-PR-Auslöser (ersetzt §10.3 aus v0.2)

Forager öffnet **automatisch** einen `merchant:variant`-PR, wenn:

1. ≥ 3 Bons aus derselben PLZ-Region (oder vom selben `merchant_legal_form`, je nach Drift-Signal)
2. **alle drei** zeigen identische `failed_patterns` ODER identische `novel_observations`
3. die Bons stammen aus einem Fenster von ≤ 90 Tagen (verhindert "Layout-Drift aus 2023" als falschen Variant-Auslöser)
4. noch kein Variant für diese Kombination existiert

Forager-DB-Tabelle `drift_observations` (aus PR-Workflow-Spec) sammelt die Signale; ein nächtlicher Job aggregiert und löst PRs aus.

---

## 3. DSFinV-K, EKaBS und DFKA-Taxonomie als Referenz (neu in v0.3)

### 3.1 Was es gibt

Es existiert ein **offizieller deutscher Datenstandard** für Kassendaten, der unser Receipt Assessment Schema v1 *eigentlich* schon parallel definiert:

- **DSFinV-K** (Digitale Schnittstelle der Finanzverwaltung für Kassensysteme), Pflicht seit § 146a AO und KassenSichV ab 01.01.2020. Aktuelle Version: 2.3. Format: CSV mit `index.xml` für Außenprüfung.
- **DFKA-Taxonomie Kassendaten** (Deutscher Fachverband für Kassen- und Abrechnungssystemtechnik e.V.). JSON-basiert, Pilot 2018, freigegeben Februar 2019. Inhaltsgleich zur DSFinV-K, aber im JSON-Format. [PDF-Dokumentation](https://www.dfka.net/wp-content/uploads/2018/08/Dokumentation_DFKA-Taxonomie-Kassendaten_V1-Pilot-1.pdf)
- **EKaBS** (Elektronischer Kassen-Beleg-Standard) Version 1.0.0, April 2021. Baut auf DFKA-Taxonomie auf, mit Vereinfachungen und Erweiterungen, JSON-basiert, **automatische Signaturprüfung möglich**. [PDF](https://dfka.net/wp-content/uploads/2021/04/EKaBS-Elektronischer-Kassen-Beleg-Standard_1.0.0_Stand_14.04.2021.pdf)

### 3.2 Wie Forager sich dazu positioniert

Forager **bildet nicht** DSFinV-K nach — das ist ein Standard für **Kassensysteme**, die ihre eigenen Daten exportieren (Innensicht der Kasse). Forager arbeitet aus der **Außensicht** (gedruckter Bon, OCR-Rekonstruktion). Wir haben nie alle Felder, die DSFinV-K hat (z.B. interne `Z_NR`, `TSE_Transaktion-Pfad`).

Aber: **wir leihen uns die Feldbezeichnungen und Strukturen aus DFKA-Taxonomie**, soweit sie auf gedruckten Bons sichtbar sind. Das gibt uns:
- Kompatibilität zu bestehenden Tools (gastro-mis, ready2order, kassensichv.com)
- Eine offizielle Quelle für Wertelisten (z.B. `processType: Kassenbeleg | AVTransfer | AVSonstige`)
- Argumentationsgrundlage gegenüber Buchhaltern/Steuerberatern bei MSP-Kunden

**Konkret heißt das:** Receipt Assessment Schema v1 bleibt Forager-eigen, aber **v2 wird Feldnamen aus DFKA-Taxonomie übernehmen**, wo es sinnvoll ist:

| Forager v1 | DFKA-Taxonomie äquivalent | Übernahme in v2? |
|---|---|---|
| `merchant.merchant_id` | `cash_register.id` + `cash_point_closing.head` | nein (DFKA-ID ist Kassen-spezifisch, nicht Brand-spezifisch) |
| `purchase_datetime.primary` | `bonkopf.start_transaction` / `end_transaction` | ja, beide Zeiten optional übernehmen |
| `tax_breakdown[].class_code` + `rate` | `bonpos_ust.ust_schluessel` (1=19%, 2=7%, ...) | ja, plus eigenes Feld `printed_class_code` (A/B/...) für die *Anzeige* auf dem Bon |
| `tax_breakdown[].net`/`tax`/`gross` | gleich | direkt übernehmen |
| `payment.method` | `bonkopf_zahlarten.zahlart_typ` (Bar, Karte, ...) | ja, mit Werteliste übernehmen |
| `lines[].line_kind` | `bonpos.gv_typ` (Umsatz, Pfand, Rabatt, ...) | ja, mit Werteliste angleichen |

→ **Action**: Receipt Assessment Schema v2 wird vor Release auf DFKA-Felder gemappt, Mapping-Tabelle als Anhang. Schema v1 bleibt für Bestands-Assessments gültig.

### 3.3 Kann ein Händler uns DSFinV-K-Daten geben?

In der Theorie: ja, der Steuerpflichtige muss DSFinV-K-Daten bei Außenprüfung bereitstellen. In der Praxis für Forager: irrelevant — wir sind **kein Steuerprüfer**, wir sind **Endkunden** mit Papier-Bons. Selbst E-Bons (QR-Code-PDFs) sind in der Regel nur visuelle Repräsentationen, nicht DSFinV-K-Exports. Einzige Ausnahme: **EKaBS-signierte PDFs** könnten wir direkt verifizieren — aber die sind heute (2026) noch keine Standard-Praxis im deutschen Einzelhandel.

→ Forager bleibt OCR/PDF-Parsing-zentriert, mit EKaBS-Verifikation als optionalem Anhang ("wenn der Händler so etwas in den E-Bon einbettet, prüfen wir die Signatur und verlassen uns dann darauf — sonst Parsing wie bisher").

---

## 4. Tax-Klassen-Heuristik (neu in v0.3)

### 4.1 Befund

Aus der Recherche und den realen Bons: **die Buchstaben A/B sind händlerabhängig**, nicht standardisiert.

| Händler | A | B | C | weitere | Quelle |
|---|---|---|---|---|---|
| **REWE** | 19% | **7%** | — | — | unsere Bons |
| **Lidl** | **7%** | 19% | — | — | unser Lidl-Bon |
| **Knolles (Edeka)** | **7%** | 19% | — | — | unser Knolles-Bon |
| Aldi | 7% | 19% | — | — | Foren-Recherche |
| **Libro** (AT) | 10% | 20%-ermäßigt | **20% (Standard)** | — | wiesoso.com |
| **MediaMarkt** | — | **`b` (klein!) = 20%** | — | — | wiesoso.com |
| **Conrad** | — | — | — | **`(1)` = 20%** | wiesoso.com |
| **Edeka** (manche Filialen) | 7% | 19% | — | **`AW` = 19%** (statt B) | wiesoso.com |

**Konsequenz für Forager:** Die Tax-Klasse-Codes (A/B/C/1/2/AW/...) sind **immer profil-spezifisch zu definieren**. Eine globale Heuristik "A = 7%" wäre falsch und gefährlich (für REWE wäre A=19%).

### 4.2 Heuristik-Fallback (wenn Profil fehlt)

Wenn ein **neuer** Händler-Bon ohne Profil ankommt, kann Claude im Receipt Assessment den Tax-Breakdown-Block am Bon-Ende auslesen und daraus das Mapping rückwärts ableiten:

```
Steuer  %        Netto    Steuer    Brutto
A=  7,0%         12,37     0,87     13,24    →  derives: A → 0.07
B= 19,0%         11,48     2,18     13,66    →  derives: B → 0.19
```

Dieses Mapping wandert ins Profile-Proposal (Sektion `tax_classes:`) und wird dort persistiert. **Keine Annahme aus dem Code heraus, nie.**

### 4.3 Sonderfall: Mehrere Tax-Klassen, gleicher Rate

Manche Bons haben `A=7%` und `B=7%` parallel (z.B. wenn die Kasse pfandfähige vs nicht-pfandfähige Lebensmittel separat verbucht). In dem Fall ist `tax_class_mapping` keine Funktion (Code → Rate), sondern eine Relation (mehrere Codes können denselben Rate haben). Das Schema v1-Feld `tax_class_mapping` ist bereits als Dict definiert, das mehrere Codes mit jeweiliger Rate erlaubt — keine Änderung nötig, aber Dokumentation ergänzen.

---

## 5. Neue Pattern-Klassen aus realen Bons (neu in v0.3)

Aus 4 zusätzlichen REWE-Bons (Hamburg, Neu Wulmstorf, Maschen 29.04, Maschen 02.05) sind folgende Pattern-Klassen als wiederkehrend identifiziert und in das Profil-Schema aufgenommen:

| Pattern-ID | Klasse | Anwendung | Beispiel (Roh) |
|---|---|---|---|
| `*_handeingabe_weight_item` | weight_item-Variante | Wiegeartikel ohne `kg x EUR/kg`-Detailzeile | `HA-BRUSTFILET  17,90 B` + `Handeingabe E-Bon  0,947 kg` |
| `*_pfand_eur_marker` | pfand_einweg | Pfand-Zeile mit "0,25 EURO"-Wortmarker + `*` | `PFAND 0,25 EURO  0,25 A *` |
| `*_leergut_einweg` | pfand_return | Pfandrückgabe-Sammelposten mit Sekundärzeile | `LEERGUT EINWEG  -2,00 A *` + `8 Stk x 0,25` |
| `*_frischerabatt` | discount | Item-bezogener Rabatt direkt nach Item | `1 x Frischerabatt  -0,69 B` |
| `*_items_with_leading_digit` | item-Variante (Pattern-Anpassung) | Item-Name beginnt mit Ziffer | `9 BAG.BROETCHEN  2,29 B` |
| `*_items_with_ampersand` | item-Variante (Pattern-Anpassung) | Item-Name enthält `&` | `S&F ERDBEERE  1,29 B` |

**Action im Profil-Schema:**

Top-Level-Block `discount_patterns:` wird neu eingeführt, mit derselben Struktur wie `pfand_patterns:`:

```yaml
discount_patterns:
  - id: rewe_frischerabatt
    kind: discount
    regex: '^\s+(?P<qty>\d+)\s+x\s+(?P<name>Frischerabatt|Rabatt|Aktionsrabatt)\s+(?P<total>-\d+,\d{2})\s+(?P<tax_class>[AB])\s*$'
    attach_to: previous_item
```

`pfand_patterns` und `discount_patterns` werden vor Item-Patterns geprüft, um Verwechslungen zu vermeiden (`Frischerabatt -0,69 B` darf nicht als Item interpretiert werden).

---

## 6. Drei-Schicht-Lernmodell mit Diskriminatoren (ersetzt §20.3 aus v0.2)

| Schicht | Was lebt da | Wo gespeichert | Diskriminatoren | Beispiel |
|---|---|---|---|---|
| **1. Layout-Profile (global)** | Wie REWE einen Bon druckt | `forager-merchants`-Git-Repo, MIT-Lizenz | merchant_id, **variant_id** (region/era/legal_form/store_cluster) | "REWE-Pfand kommt als 'PFAND EINWEG' direkt unter Item" |
| **2. Produkt-Aliase (per User)** | Wie "ESL MILCH 3,5%" → "Milch Vollmilch 3.5%" im Grocy heißt | Forager-Postgres pro User | merchant_id (für Match-Disambiguation) | `ESL MILCH 3,5% @ de.rewe → grocy:product:42` |
| **3. Heuristiken (global)** | Generische Regeln, händlerunabhängig | `forager-heuristics`-Git-Repo, MIT-Lizenz | — | "Ein Item mit `*` nach der Tax-Klasse ist nicht-rabattfähig (REWE/Knolles-Konvention)" |

**Neu in v0.3:** Schicht 1 hat jetzt **expliziten Diskriminator-Stack** statt nur `merchant_id`:

```
merchant_id        + variant_selectors        + profile_validity
   ↓                       ↓                          ↓
de.rewe          + region=212 / legal=oHG  +  valid_from=2026-02-01
                 + store_cluster=Westfield     valid_until=∞
```

Der Worker resolved den Profil-Stack aus diesen Diskriminatoren bei jedem Receipt-Lauf — siehe §2.2.

---

## 7. Marktanalyse-Konsequenzen (neu in v0.3)

### 7.1 Forager als "fehlende Mitte"

Das Marktbild:

```
[Asprise / Apocha]                                         [knipknap / receiptparser]
Closed-source, OCR + ML,                                   YAML-Profile, OCR,
proprietär, kommerziell                                    nur Company/Date/Sum

      ↑                                                                ↑
      ├──────────────────────  ABDECKUNGSLÜCKE  ───────────────────────┤
      ↓                                                                ↓

[Forager]                                                  [erinalbers/grocy-receipt-ocr]
Profil-basiert mit Vererbung,                              Docker, Grocy-Integration,
PR-Workflow, Drift-Detection,                              Regex-Configs pro Händler,
Multi-Backend (Snipe-IT/Grocy/Spoolman),                   nur USA-orientiert,
DFKA-konform, EKaBS-ready                                  kein Drift-Detection
```

Forager schließt diese Lücke: **strukturierte Wissensbasis** (wie knipknap, aber tief) + **Community-getriebene Pflege** (wie offene Standards) + **Multi-Backend-Plugin-Architektur** (wie Hangar) + **Drift-/Variant-Bewusstsein** (das bisher niemand explizit macht).

### 7.2 Strategische Empfehlungen — und was wir bewusst NICHT tun

#### Was wir tun

1. **Open-Source ab Tag 1.** `forager-merchants`-Repo MIT-lizenziert, `forager-parser` und `forager-worker` ebenfalls MIT. Wir gewinnen nur durch breite Profil-Datenbank — Closed-Source würde uns auf 1-Person-Coverage limitieren.
2. **Code zuerst, Konzept zweit, Outreach nie als erstes.** Forager geht erst dann an die Öffentlichkeit, wenn ein End-to-End-Flow (Bon rein, Grocy-Eintrag raus) für mindestens zwei Händler funktioniert. Konzepte ohne Code sind 2026 wertlos — die Welt ist voll davon.
3. **Standalone-Service, der die Grocy-API nutzt.** Genau die Architektur, die Berrnd (Grocy-Maintainer) in [Issue #404](https://github.com/grocy/grocy/issues/404) selbst als richtigen Weg skizziert hat: *"Maybe it would be better to run this as a standalone service and just use the grocy API like the barcode scanner app does."* Das ist exakt Forager. Wir setzen seine Empfehlung um.
4. **Kollaboration mit `erinalbers/grocy-receipt-ocr` über die Tool-Ebene, nicht über Repos.** Wenn überhaupt Outreach: ein freundlicher Mail-Austausch über Profil-Format-Standardisierung, sodass beide Tools dasselbe YAML lesen können. Keine Issue-Kommentare in fremden Repos, die "schaut mal, was wir bauen" lesen.

#### Was wir bewusst NICHT tun

1. **Keine Kommentare in Grocy-Issues #404, #1533, #2831 oder ähnlichen.** Issue #404 zeigt, dass Berrnd das Thema seit Jahren bewusst aus Grocy heraushält — und Issue #2831 (November 2025) liest sich wie ein KI-generierter Feature-Wunsch mit überdetaillierter Architektur-Skizze ohne Code, der Maintainer aktuell zu Recht frustriert. Forager würde mit dieser Welle in einen Topf geworfen, sobald wir uns dort einmischen.
2. **Keine "Forager könnte das lösen"-Posts in fremden Communities.** Stattdessen: Forager-Repo verfügbar machen, dokumentieren, mit echten Use-Cases laufen lassen. Wer es findet, findet es. Pull statt Push.
3. **Kein direkter Wettbewerb mit Apocha.** Apocha ist kommerziell und löst ein anderes Problem (Privatperson + Finanz-Tracking). Forager-Use-Case: **MSP-Mehrnutzer / Self-Hoster / HomeLab + Grocy/Snipe-IT-Integration**. Andere Persona.
4. **Keine Vermarktung vor MVP.** Konzepte/PR-Workflows/Schemas sind günstig zu produzieren — auch und gerade mit KI-Assistenz. Was zählt, ist ein funktionierender Bon→Backend-Flow. Bis dahin: still arbeiten.

#### Lessons aus dem Grocy-Issue-Tracker

Issue #404 (geöffnet vor Jahren, bewusst nicht implementiert), #1533 ("schaut mal, Apocha löst das"), #2831 (sieht KI-generiert aus): das gleiche Feature wurde wieder und wieder vorgeschlagen — von Leuten, die das Problem haben, aber nicht selbst lösen. Forager beweist nur dann seine Existenzberechtigung, wenn es das, was die Issue-Schreiber wollen, *baut*, statt es zu **fordern**. Das ist ein wichtiger Disziplin-Anker für die nächsten Monate.

---

## 8. Befunde aus dem Prototyp-Lauf (neu in v0.3)

Sieben Bons aus vier Filialen wurden mit dem Python-Prototyp `forager-parser` gegen die Profile geparst:

| Bon | Filiale | Confidence | Totals match | Notes |
|---|---|---|---|---|
| Knolles Seevetal 09.05 | Knolles (Edeka) | 0.98 | ✅ | PAYBACK erkannt, `*`-Pfand erkannt |
| Lidl Seevetal 19.05 | Lidl | 0.98 | ✅ | Pfand-Aggregat (24× 0,25), Pfandrückgabe |
| REWE Maschen 20.05 | REWE Eigenbetrieb | 0.98 | ✅ | REWE Bonus + Coupon "Tulip Fl" |
| REWE Hamburg 21.03 | REWE oHG Piclum | 0.95 | ✅ | Selbständig, andere UID, Leergut, Handeingabe |
| REWE Neu Wulmstorf 25.04 | REWE Eigenbetrieb | 0.98 | ✅ | Frischerabatt, 3× PFAND-EURO, 32 Lines |
| REWE Maschen 29.04 | REWE Eigenbetrieb | 0.98 | ✅ | EuroELV-Zahlung, "9 BAG.BROETCHEN", "S&F ERDBEERE" |
| REWE Maschen 02.05 | REWE Eigenbetrieb | 0.98 | ✅ | Standard-Layout |

**Lessons Learned, die ins Schema einflossen:**

1. **`^` und `$` mit `search()` auf raw_text matcht nicht zeilenweise.** Alle Patterns müssen entweder zeilenweise iteriert oder mit `re.MULTILINE` kompiliert werden. → Profil-Schema dokumentiert das jetzt explizit.
2. **`item_count_declared` ist mehrdeutig.** Knolles' "Posten: 10" ist ein **Stück**-Zähler (alle Verkaufseinheiten inkl. Pfand), nicht ein **Bon-Position**-Zähler. → Feld umbenennen in Schema v2: `unit_count_declared` mit `count_semantics: "lines" | "units"`.
3. **Pfand-Codes brauchen explizite Whitelist.** `line_kind in {item, pfand}` ignoriert `pfand_einweg`/`pfand_mehrweg` — beide haben unterschiedliche steuerliche Implikationen. → Profile YAML standardisiert die Kind-Werte: `{item, pfand_einweg, pfand_mehrweg, pfand_aggregate, pfand_return, discount, coupon}`.
4. **Variant-Adressen brauchen permissive Patterns.** Statt `(?P<street>Schulstra[ßs]e...)` lieber `(?P<street>...(?:straße|weg|allee|boulevard|platz|gasse|ring|damm|chaussee)\s+\d+...)`. → Empfehlung als Heuristik dokumentiert.
5. **Confidence-Aggregation ist robust.** Trotz drei verschiedenen Filialen mit drei Layouts ergab sich Confidence ≥ 0.94 für alle Bons, sobald die Patterns griffen.

---

## 9. Roadmap-Update (ersetzt §17 aus v0.2)

### Phase 0 — Prototyp-Validierung — **DONE (Mai 2026)**
- ✅ Standardisierter Bewertungs-Prompt v1.0
- ✅ Receipt Assessment Schema v1
- ✅ PR-Workflow-Spec + GitLab-Templates
- ✅ Python-Parser-Prototyp (`forager-parser`) mit CLI
- ✅ Drei initiale Profile (REWE, Lidl, Knolles)
- ✅ 7 realistische Bon-Tests grün

### Phase 1 — MVP-Hardening (Juni–Juli 2026)
- [ ] **Schema-Datei `schema/merchant-profile.v1.json`** formal als JSON-Schema schreiben (im Konzept beschrieben, noch nicht codiert)
- [ ] **Profile-Vererbung implementieren** im `forager-parser` (`extends:`, `applies_to`, Merging-Algorithmus)
- [ ] **`forager-merchants` Repo-Skelett** auf GitLab self-hosted anlegen + CI-Pipeline (8 Jobs aus PR-Workflow-Spec)
- [ ] **OCR-Pipeline** (PaddleOCR + Tesseract-Fallback) als Docker-Service
- [ ] **Mock-Forager-Worker** als FastAPI mit Mock-Queue (Redis), gegen den die PWA entwickelt werden kann
- [ ] **PWA-Skelett** (React + Vite + Tailwind), Scanner-Screen, Pending-Liste, Assessment-Review

### Phase 2 — DFKA-Angleichung + Real-Use (August–September 2026)
- [ ] **Receipt Assessment Schema v2** mit DFKA-Feldnamen-Mapping (Anhang dokumentiert die v1↔v2-Migration)
- [ ] **Snipe-IT-Plugin** als erstes Backend-Plugin
- [ ] **Grocy-Plugin** als zweites Backend-Plugin — Standalone-Service via Grocy-API (genau wie Berrnd in Issue #404 als richtige Architektur skizziert hat)
- [ ] **Anthropic-API-Anbindung** im Worker für Modus A (Claude-API direkt)
- [ ] **Drift-Detection** in Postgres-Tabelle, mit Aggregations-Job
- [ ] **Auto-PR-Generierung** für `merchant:new`-Fälle aus der PWA heraus

### Phase 3 — Community + Federation (Oktober 2026+)
- [ ] **Public `forager-merchants` Mirror** auf GitHub (read-only Mirror von GitLab self-hosted)
- [ ] **Spoolman-Plugin** für 3D-Druck-Materialien (Bambu H2D Use-Case)
- [ ] **EKaBS-Verifikation** für signierte E-Bons
- [ ] **Documentation Site** (MkDocs Material) öffentlich
- [ ] **Forager-Heuristics Repo** ausgegliedert vom merchants-Repo

### Phase 4 — Optional (2027)
- [ ] Mobile-native Wrapper (Capacitor/Tauri) für Offline-Scanning
- [ ] Multi-User-Sync (für Familien-Haushalte)
- [ ] Föderation: `forager-merchants`-Mirrors verschiedener Communities (Apotheken-Coverage, Baumarkt-Coverage, ...)

---

## 10. Risiken und Updates (Ergänzung zu §18 aus v0.2)

| ID | Risiko | Status v0.3 | Mitigation |
|---|---|---|---|
| R-Drift | Layouts ändern sich häufiger als Profile gepflegt werden | **Bestätigt** durch reale Bons | Variant-System, automatischer Drift-Aggregator, Auto-PRs |
| R-False-Positive | Falsche Drift-Detection erzeugt PR-Spam | Risiko gestiegen durch Auto-PRs | "≥3 Bons in 90 Tagen aus derselben Region" als Hürde |
| R-Standard-Konflikt | DSFinV-K/EKaBS könnten unser Schema obsolet machen | **Niedriger als gedacht** — sie lösen ein anderes Problem (Innensicht der Kasse) | DFKA-Feldnamen-Angleichung in Schema v2 |
| R-Konkurrenz | Apocha, knipknap, erinalbers etc. | **Niedrig** — andere Persona / unvollständig / schlafend | Differenzierung nach §7 |
| R-Tax-Class-Mapping | Globale Annahme über A/B = 7%/19% wäre falsch | **Identifiziert**, gefixt | Tax-Klassen sind im Profil deklariert, niemals im Code |
| R-PR-Overhead | Strukturierter PR-Workflow ist Hürde für Contributoren | **Bewahrt**, mit Mitigation | PWA generiert PR-Material automatisch, manueller Weg dokumentiert aber sekundär |

---

## 11. Offene Fragen für die nächste Iteration

1. **Profile-Vererbung im Parser-Code:** Wann ist es Zeit, das im `forager-parser` zu implementieren? Bisher haben wir nur einzelne `profile.yaml`-Files. Ein Variant würde unseren Loader erweitern müssen.
2. **PWA-Frontend:** React + Vite + Tailwind ist gesetzt — aber: Capacitor-Wrapper oder pure PWA? Pure PWA ist einfacher zu deployen, aber Capacitor gibt native Camera-API-Vorteile auf iOS.
3. **OCR-Pipeline:** PaddleOCR ist erste Wahl. Aber: läuft das im HomeLab auf einem alten DL380 Gen9 ausreichend schnell, oder brauchen wir GPU? Test im HomeLab-Container empfohlen.
4. **Erste externe Bon-Sample-Lieferanten:** Nicht durch Outreach in fremden Repos akquirieren — eher im persönlichen Umfeld, sobald ein End-to-End-Flow steht. Hochpriorisierte Erstziele: Aldi, Rossmann, Edeka-Eigenmarkt, dm. (Keine kalten Bittstellungen, kein Cross-Posting.)
5. **Validation-Frage für uns selbst:** Bauen wir gerade noch ein weiteres Konzept-Dokument, das nie Code wird? Antwort heute: nein — der Parser läuft auf 7 realen Bons mit korrekten Totals. Aber: ab jetzt **gilt die Regel "Code vor Konzept-Update"**. Konzept v0.4 entsteht nur, wenn vorher mindestens eines passiert: Variant-Vererbung implementiert, Snipe-IT-Plugin geschrieben, OCR-Pipeline integriert. Konzept-Schreiben ohne Code-Fortschritt ist Selbstbeschäftigung.

---

**Ende v0.3.**

Nächster Schritt: **Profile-Vererbungs-Implementierung im `forager-parser`** als Phase-1-Auftakt — das ist das eine Stück Code, ohne das Hamburg/oHG-Bons nicht sauber in ihr eigenes Variant-Profil migrieren können. Konzept-Updates folgen erst wieder, wenn Code vorangekommen ist.
