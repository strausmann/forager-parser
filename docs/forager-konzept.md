# Forager — Asset Onboarding Accelerator für Hangar

> **Codename-Vorschlag:** *Forager* (Sammler) — passt zur Hangar-/Lager-Metaphorik.
> Alternativen: *Scout*, *Picker*, *Quartermaster*, *Procure*.

**Version:** 0.1 (Konzept)
**Datum:** 20. Mai 2026
**Autor:** Björn Strausmann
**Status:** Draft für Review

---

## 1. Vision in einem Satz

> Eine PWA, in die ein Mitarbeiter per Smartphone-Kamera, Bluetooth-Scanner oder URL-Paste einen Artikel "wirft" — und nach einem asynchronen, Claude-gestützten Anreicherungs- und Approval-Prozess landet das Item korrekt eingestuft, kategorisiert und verknüpft in Snipe-IT, Grocy oder Spoolman.

---

## 2. Problem & Motivation

Das Onboarding neuer Items in Snipe-IT (und perspektivisch Grocy / Spoolman) ist heute der Flaschenhals:

- **Manuelle Datenerfassung** — Hersteller, Modellnummer, Kategorie, Lieferant, Preis, Bild müssen pro Asset abgetippt werden.
- **Stammdaten-Inkonsistenz** — neue Anlegerinnen erzeugen Dubletten von Herstellern ("Dell", "Dell Inc.", "DELL"), Kategorien und Lieferanten.
- **Bildbeschaffung** — Produktfotos müssen separat gesucht und hochgeladen werden.
- **Kontextverlust** — beim Empfang einer Lieferung weiß man zwar, *was* es ist, aber nicht wie man es im System "richtig" anlegt.

Die Konsequenz: Items landen entweder gar nicht im System oder mit minimalen Daten, die später aufwendig nachgepflegt werden müssen. In der Praxis im HomeLab Maschen und in MSP-Mandanten-Setups führt das dazu, dass Snipe-IT als Inventarsystem nicht das volle Potenzial entfaltet.

**Forager** löst das, indem es den menschlichen Aufwand auf zwei Aktionen reduziert:

1. **Aufnehmen** — Scan oder URL-Paste + 1 Satz Kontext (Lagerort, Kommentar).
2. **Freigeben** — Sichtprüfung der von Claude angereicherten Daten, ggf. Korrektur, dann Approve.

Den Rest erledigen ein Headless-Browser, Claude und die jeweilige Backend-API.

---

## 3. Designprinzipien

| # | Prinzip | Konsequenz |
|---|---|---|
| **P1** | **Hangar-First** | Forager ist kein Solitär, sondern lebt im Hangar-Ökosystem. Plugins, Tag-Konventionen und Capability-Interfaces werden geteilt. |
| **P2** | **Async by default** | Scan → Auftrag → Worker → Approval. Niemand wartet auf Claude. |
| **P3** | **Human-in-the-Loop** | Jedes neu angelegte Item *und jede neue Dependency* (Hersteller, Kategorie, Lieferant) durchläuft Approval. Keine stillen Schreibvorgänge. |
| **P4** | **Idempotenz** | Wiederholter Scan einer EAN erzeugt keinen Duplikat-Auftrag — sondern wird auf existierenden Auftrag bzw. existierendes Backend-Item gemappt. |
| **P5** | **Provider-Pluralität** | EAN-Auflösung, Webscraping, Bildbeschaffung sind je drei austauschbare Provider. Keine Single Source of Truth. |
| **P6** | **Self-hostable** | Komplettes Stack läuft offline-fähig im HomeLab. Keine zwingenden Cloud-Abhängigkeiten außer Anthropic-API (austauschbar). |
| **P7** | **Audit-Trail** | Jeder Auftrag dokumentiert Quelle, Provider, Claude-Prompt, Approvals und Backend-Response — KRITIS/NIS2-kompatibel. |
| **P8** | **Mobile-First** | Primärgerät ist Smartphone in der Hand des Annehmenden. Desktop ist Sekundärfläche für Approver. |

---

## 4. High-Level-Architektur

```
┌─────────────────────────────────────────────────────────────────────┐
│  CLIENT (PWA)                                                       │
│  ─────────────────────────────────────────────────────────────────  │
│  React + Vite + Tailwind   •  ZXing/QuaggaJS Scanner                │
│  Camera API  •  Web Bluetooth (HID Scanner)  •  Service Worker      │
└────────────────┬────────────────────────────────────────────────────┘
                 │  REST / SSE
                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FORAGER-API (Go 1.25 + chi + Bun)                                  │
│  ─────────────────────────────────────────────────────────────────  │
│  /jobs     /approve     /backends     /search                       │
│  AuthN: OIDC (Authelia/Authentik) oder Hangar-Session-Share         │
└────────────────┬────────────────────────────────────────────────────┘
                 │
        ┌────────┴─────────┐
        │                  │
        ▼                  ▼
┌──────────────┐    ┌──────────────────────────────────────────────┐
│  POSTGRES    │    │  REDIS (Job-Queue + Pub/Sub für SSE)         │
│  - jobs      │    │  - forager:queue:enrich                      │
│  - artifacts │    │  - forager:queue:approve                     │
│  - audits    │    │  - forager:events:<job_id>                   │
└──────────────┘    └──────────────────┬───────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ENRICHMENT-WORKER (Python 3.13 + Claude Code SDK)                  │
│  ─────────────────────────────────────────────────────────────────  │
│  Provider-Chain:                                                    │
│    1. EAN-Resolver  →  OpenFoodFacts, OpenProductsFacts, SpoolmanDB │
│    2. URL-Scraper   →  Playwright (headless Chromium)               │
│    3. Claude        →  Strukturierung, Klassifizierung, Bildwahl    │
│    4. Image-Fetcher →  Download, EXIF-Strip, Resize, Hash           │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  BACKEND-PLUGINS (gemeinsam mit Hangar)                             │
│  ─────────────────────────────────────────────────────────────────  │
│  Snipe-IT   •   Grocy   •   Spoolman   •   <custom>                 │
│  Capabilities:  Creator, DepResolver, Searcher, ImageUploader       │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.1 Komponenten im Detail

**PWA-Client** — installierbar auf iOS/Android-Homescreen, funktioniert offline für die Scan-Erfassung (lokaler IndexedDB-Cache, Sync bei Verbindung). Kamera über `getUserMedia`, Barcode-Decoding über ZXing-JS. Bluetooth-HID-Scanner werden als Tastatur erkannt — ein zweiter Modus über Web Bluetooth (BLE-GATT) ermöglicht direkte Kommunikation mit Scannern wie dem Eyoyo MJ-1860 oder Inateck BCST-70.

**Forager-API** — Go-Service nach Hangar-Konvention (chi-Router, Bun-ORM, SQLite/Postgres). Stellt REST-Endpunkte bereit, schreibt Jobs in Postgres und gibt Notifications per Server-Sent-Events an die PWA. Auth wahlweise über geteilte Hangar-Session oder OIDC.

**Postgres** — persistente Job-Historie, Approval-Trail, Audit-Log. Postgres ist Pflicht für Forager (anders als bei Hangar, wo SQLite ausreicht), weil mehrere Worker parallel arbeiten und SSE-Subscriptions stabil bleiben müssen.

**Redis** — Job-Queue für den Enrichment-Worker (BRPOPLPUSH) und Pub/Sub für SSE-Fanout. Bewusst klein gehalten — Redis ist Transport, nicht State.

**Enrichment-Worker** — Python statt Go, weil das Python-Ökosystem hier deutlich stärker ist: `playwright`, `openfoodfacts-python`, `anthropic` SDK, `Pillow` für Bildverarbeitung. Worker holt Jobs aus Redis, durchläuft Provider-Chain, schreibt Artefakte (JSON + Bilder) zurück nach Postgres/S3-kompatibles Storage (MinIO oder Synology Object Storage).

**Backend-Plugins** — wiederverwendbare Go-Pakete, die *sowohl Hangar als auch Forager* nutzen. Genau hier liegt der strategische Hebel: ein Snipe-IT-Plugin, das Hangar zum *Suchen/Bewegen* nutzt und Forager zum *Anlegen*.

---

## 5. Daten- und Zustandsmodell

### 5.1 Job-Lebenszyklus

```
   ┌─────────┐   submit    ┌──────────┐
   │  draft  │ ──────────► │  queued  │
   └─────────┘             └─────┬────┘
                                 │ worker picks up
                                 ▼
                          ┌──────────────┐
                          │  enriching   │
                          └─────┬────────┘
                                │
                  ┌─────────────┼─────────────┐
                  │ success     │ partial     │ error
                  ▼             ▼             ▼
            ┌─────────────┐ ┌─────────┐ ┌─────────┐
            │ review_ready│ │ review_ │ │ failed  │
            └──────┬──────┘ │ partial │ └────┬────┘
                   │        └────┬────┘      │
                   │             │      retry│
                   │             │      ─────┘
                   │             │
       ┌───────────┴─────┬───────┘
       │                 │
   approve            reject / re-enrich
       │                 │
       ▼                 ▼
   ┌──────────┐    ┌──────────┐
   │ creating │    │ rejected │
   └────┬─────┘    └──────────┘
        │
   ┌────┴─────┐
   │ success  │ failure
   ▼          ▼
┌──────┐   ┌──────────┐
│ done │   │create_err│
└──────┘   └──────────┘
```

**Wichtig:** Der Zustand `review_partial` entsteht, wenn Claude unsicher ist — z.B. mehrere Kandidaten-Kategorien oder konkurrierende Produktbilder. Der Approver entscheidet dann nicht nur Ja/Nein, sondern wählt aus Alternativen.

### 5.2 Postgres-Schema (Auszug)

```sql
CREATE TABLE jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      TEXT NOT NULL,             -- User-ID aus OIDC
    target_backend  TEXT NOT NULL,             -- 'snipeit', 'grocy', 'spoolman'
    target_location TEXT,                       -- Hangar-Tag, z.B. 'HH-AK-KX10-F0203'
    input_type      TEXT NOT NULL,             -- 'ean', 'url', 'manual'
    input_value     TEXT NOT NULL,             -- 4337256064880 oder https://...
    user_comment    TEXT,
    status          TEXT NOT NULL,             -- siehe Lifecycle
    error_message   TEXT,
    retry_count     INT NOT NULL DEFAULT 0,
    enriched_data   JSONB,                     -- siehe Section 6
    approved_data   JSONB,                     -- nach Approver-Änderungen
    backend_result  JSONB,                     -- {asset_id, url, ...} nach Anlegen
    backend_item_id TEXT,                       -- Snipe-IT Asset Tag etc.
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_jobs_status     ON jobs (status) WHERE status NOT IN ('done','rejected');
CREATE INDEX idx_jobs_dedupe     ON jobs (input_type, input_value, target_backend);
CREATE INDEX idx_jobs_created_by ON jobs (created_by, created_at DESC);

CREATE TABLE artifacts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id      UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    kind        TEXT NOT NULL,                 -- 'image', 'html', 'json', 'pdf'
    source      TEXT NOT NULL,                 -- 'openfoodfacts', 'amazon', 'claude'
    storage_url TEXT NOT NULL,                 -- s3://forager/...
    sha256      TEXT NOT NULL,
    selected    BOOLEAN NOT NULL DEFAULT FALSE,  -- für Bildauswahl
    metadata    JSONB,                          -- dimensions, mime, etc.
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_log (
    id          BIGSERIAL PRIMARY KEY,
    job_id      UUID REFERENCES jobs(id),
    actor       TEXT NOT NULL,                 -- 'user:bjoern', 'worker:enricher-1', 'system'
    action      TEXT NOT NULL,                 -- 'submit', 'enrich_start', 'approve', ...
    detail      JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE dependency_proposals (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id        UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    backend       TEXT NOT NULL,
    dep_type      TEXT NOT NULL,               -- 'manufacturer','category','supplier','model','location','product_group','quantity_unit'
    proposed_name TEXT NOT NULL,
    proposed_data JSONB,
    resolution    TEXT,                          -- 'use_existing:42', 'create_new', 'edit', 'reject'
    resolved_id   TEXT,                          -- Backend-ID nach Anlegen
    decided_at    TIMESTAMPTZ,
    decided_by    TEXT
);
```

### 5.3 Deduplizierung (P4)

Bevor ein neuer Job angelegt wird, prüft die API:

1. **Exakte Übereinstimmung** auf `(input_type, input_value, target_backend)` in nicht-abgeschlossenen Jobs → bestehenden Job zurückgeben.
2. **Existenz im Backend** über Plugin-Capability `LookupByExternalKey(ean | url_hash)` → vorhandenes Item zurückgeben mit "schon vorhanden"-Hinweis.
3. Erst dann neuer Job.

---

## 6. Das kanonische Enrichment-JSON

Das ist das Herzstück. Egal welche Quelle Claude füttert (Amazon, Lidl, OpenFoodFacts, Hersteller-Seite), das Ergebnis ist immer dasselbe Schema. Backend-Plugins picken sich, was sie brauchen.

```jsonc
{
  "schema_version": "1.0",
  "extraction": {
    "timestamp": "2026-05-20T11:30:00Z",
    "primary_source": "https://www.amazon.de/dp/B0DHC8SP54",
    "claude_model": "claude-opus-4-7",
    "providers_used": ["playwright_amazon", "openfoodfacts"],
    "confidence_overall": 0.92
  },
  "identification": {
    "ean": "4337256064880",
    "manufacturer_part_number": null,
    "name": "Alpen JodSalz",
    "name_long": "Rewe Beste Wahl Alpen JodSalz mit Fluorid und Folsäure",
    "manufacturer": "Rewe",
    "brand": "Rewe Beste Wahl",
    "model": null
  },
  "classification": {
    "snipeit": {
      "asset_kind": "consumable",          // hardware | accessory | consumable | component | license
      "category_suggestion": "Verbrauchsmaterial > Küche",
      "confidence": 0.85
    },
    "grocy": {
      "product_group_suggestion": "Konserven",
      "default_quantity_unit": "Gramm",
      "purchase_quantity_unit": "Packung",
      "stock_quantity_unit": "Gramm"
    },
    "spoolman": null                        // nur wenn relevant
  },
  "commerce": {
    "supplier": "Rewe",
    "supplier_url": "https://www.rewe.de/...",
    "price": { "amount": 0.69, "currency": "EUR", "unit": "Packung" },
    "price_history": [],
    "offer_active": false
  },
  "physical": {
    "weight_g": 500,
    "dimensions_mm": { "w": 70, "h": 130, "d": 40 },
    "package_unit": "Packung",
    "package_contents_unit": "Gramm",
    "package_contents_amount": 500,
    "best_before_days": 1500
  },
  "media": {
    "images": [
      {
        "id": "img-1",
        "url": "s3://forager/jobs/abc/img-1.jpg",
        "source": "openfoodfacts",
        "type": "product",                 // product | nutrition | back | packaging | hero
        "width": 1024,
        "height": 1024,
        "selected": true
      },
      {
        "id": "img-2",
        "url": "s3://forager/jobs/abc/img-2.jpg",
        "source": "amazon_main",
        "type": "hero",
        "selected": false
      }
    ],
    "description_html": "<p>Jodiertes Speisesalz mit Zusatz von Fluorid und Folsäure</p>",
    "description_plain": "Jodiertes Speisesalz mit Zusatz von Fluorid und Folsäure"
  },
  "dependencies": {
    "manufacturer": {
      "proposed_name": "Rewe",
      "lookup_result": null,               // wird von Plugin gefüllt
      "action": null                        // 'use_existing' | 'create' | 'manual'
    },
    "category": {
      "proposed_name": "Verbrauchsmaterial > Küche",
      "lookup_result": null,
      "action": null
    },
    "supplier": {
      "proposed_name": "Rewe",
      "lookup_result": null,
      "action": null
    }
  },
  "raw_excerpts": [
    {
      "source": "openfoodfacts:4337256064880",
      "url": "https://world.openfoodfacts.org/api/v2/product/4337256064880.json",
      "excerpt_path": "s3://forager/jobs/abc/raw/off.json"
    }
  ]
}
```

Das Schema ist **versioniert** (`schema_version`), damit alte Jobs nach Schema-Erweiterungen lesbar bleiben.

---

## 7. Provider-Chain im Enrichment-Worker

Der Worker arbeitet **opportunistisch**: er sammelt aus möglichst vielen Quellen Daten ein, übergibt das Sammelsurium Claude und lässt das LLM normalisieren. Claude ist hier *nicht* der Scraper, sondern der **Schiedsrichter und Strukturierer**.

### 7.1 Reihenfolge

```python
async def enrich(job: Job) -> EnrichedData:
    bag = ProviderBag()

    # Phase 1: EAN-Resolver (falls EAN vorhanden)
    if job.has_ean():
        bag += await openfoodfacts.lookup(job.ean)
        bag += await openproductsfacts.lookup(job.ean)
        bag += await spoolmandb.lookup(job.ean)            # für Filament-EAN
        bag += await geekhack_eanlookup.lookup(job.ean)    # für Hardware-EAN
        bag += await google_shopping_eanlookup(job.ean)    # via Playwright

    # Phase 2: URL-Scraper (falls URL vorhanden ODER aus EAN-Suche entstanden)
    for url in bag.discovered_urls() + ([job.url] if job.url else []):
        domain = urlparse(url).netloc
        scraper = scrapers.for_domain(domain)             # amazon, lidl, rewe, obi, mediamarkt, generic
        bag += await scraper.scrape(url)

    # Phase 3: Claude-Strukturierung
    enriched = await claude.structure(
        bag=bag,
        target_backend=job.target_backend,
        target_location=job.target_location,
        user_comment=job.user_comment,
        backend_taxonomies=await load_backend_taxonomies(job.target_backend)
    )

    # Phase 4: Bild-Download + Hashing + Storage
    enriched.media.images = await image_processor.process(enriched.media.images)

    # Phase 5: Dependency-Resolution (Vorschlag, nicht Schreiben!)
    enriched.dependencies = await resolve_dependencies(
        enriched, job.target_backend
    )

    return enriched
```

### 7.2 Scraper-Strategie pro Domain

Domain-spezifische Scraper sind klein und deterministisch — sie liefern strukturierte Daten ohne LLM-Aufruf:

| Domain | Strategie | Besonderheit |
|---|---|---|
| **amazon.de** | Playwright + DOM-Selektoren | Captcha-Risiko → Retry-Logic, ggf. Residential-Proxy |
| **lidl.de** | JSON-LD aus `<script type="application/ld+json">` | Sauber strukturiert, kein Captcha |
| **rewe.de** | Marktguru-API als Datenanreicherung | Du hast hier bereits Vorarbeit (Marktguru-Harvester) |
| **obi.de** | Playwright + JSON-LD | Produktdetails meist sauber im `Product`-Schema |
| **mediamarkt.de** | Playwright | Manchmal Bot-Schutz, fallback auf cache.google |
| **dell.com** | Spezielles Plugin — Service-Tag/Order-ID-Auflösung möglich | Wertvoll für deine MSP-Workflows |
| **\<generic\>** | Playwright + Readability.js + JSON-LD-Sniffer + Claude-Fallback | Letzte Resort |

**Generic-Scraper** ist der Fallback: Playwright lädt die Seite, extrahiert JSON-LD wenn vorhanden, sonst Mozilla-Readability-Text. Das Ergebnis wandert in den ProviderBag, und Claude entscheidet, was relevant ist.

### 7.3 EAN-Datenquellen — kombinierter Ansatz

| Quelle | Abdeckung | Datenqualität | Lizenz | Strategie |
|---|---|---|---|---|
| **OpenFoodFacts** | Lebensmittel global, ~4M Produkte | Hoch (Nutriscore, Allergene, Bilder) | ODbL | Direkt API mit Custom User-Agent (AppName/Version (Email)), optional täglicher Snapshot |
| **OpenProductsFacts** | Non-Food (Kosmetik, Haushalt, etc.) | Mittel | ODbL | Wie OpenFoodFacts |
| **SpoolmanDB** | 3D-Filament | Hoch (für Filament) | MIT | Spiegel als Git-Submodule, täglicher Pull |
| **3dfilamentprofiles.com** | 3D-Filament-Druckprofile | Hoch | unklar | Nur als Anreicherung |
| **Marktguru API** | Aktuelle Angebote | Mittel | Privat | Eigener Harvester (existiert) |
| **Google Shopping** (Playwright) | Universell | Variabel | — | Nur Fallback |

**Lokaler Spiegel:** Für OpenFoodFacts wird empfohlen, bei mehr als wenigen hundert Produkten den vollständigen Datenabzug als CSV oder JSONL herunterzuladen statt jeden Scan einzeln zu fragen. Forager spiegelt täglich nachts den **Delta-Export** in eine lokale Mongo- oder Postgres-Tabelle und fragt zuerst lokal, dann remote. Das spart Latenz und respektiert die Bitte, dass 1 API-Call = 1 echter User-Scan ist.

### 7.4 Bildverarbeitung

```
Originalbild → SHA256-Hash → EXIF-Strip → Resize-Varianten (orig, 1024, 256) →
  S3-kompatibles Storage (MinIO/Synology) → URL in artifacts-Tabelle
```

Bei Mehrfachbildern bietet Claude eine Pre-Selection (z.B. das offensichtlichste Hero-Shot ohne Wasserzeichen), der Approver kann frei wählen oder eigene Bilder hochladen.

---

## 8. Claude-Integration

### 8.1 Wo läuft Claude?

Pro **deine Entscheidung**: Eigener Microservice (Enrichment-Worker), Aufträge in Postgres/Redis, Trigger durch Worker-Loop.

Der Worker greift auf **zwei Claude-Modi** zurück:

| Modus | Wann | Mechanismus |
|---|---|---|
| **A: Anthropic-API direkt** | Strukturierung von Roh-Daten zu JSON | `anthropic` Python SDK, klassischer `messages.create` mit JSON-Schema |
| **B: Claude Code (CLI)** | Komplexe Webrecherche, mehrstufiges Reasoning, Playwright-Steuerung | Claude Code CLI als Subprozess, läuft mit MCP-Server für Playwright + lokales Filesystem |

**Modus A** ist 95 % der Fälle — schnell, deterministisch, JSON-Schema-validiert.
**Modus B** kommt nur, wenn Modus A "ich brauche mehr Daten" zurückmeldet (z.B. Hersteller-Webseite öffnen, Datenblatt verstehen, Specs aus PDF ziehen).

### 8.2 Prompt-Template (Auszug)

```
<role>
Du bist Forager, ein Inventarisierungs-Assistent. Deine Aufgabe ist es, Roh-Daten
aus Produktquellen in das kanonische Forager-Schema v1.0 zu normalisieren.
</role>

<context>
Zielsystem: {{target_backend}}
Eintrags-Tag (Hangar-Location): {{target_location}}
User-Kommentar: {{user_comment}}
</context>

<input_bag>
{{provider_bag_json}}
</input_bag>

<backend_taxonomies>
Vorhandene Kategorien in {{target_backend}}: {{categories_json}}
Vorhandene Hersteller: {{manufacturers_json}}
Vorhandene Lieferanten: {{suppliers_json}}
</backend_taxonomies>

<task>
1. Identifiziere das Produkt (Name, Hersteller, EAN, MPN).
2. Klassifiziere:
   - Snipe-IT: hardware/accessory/consumable/component/license
   - Grocy: Produktgruppe, Mengeneinheiten
   - Spoolman: nur wenn Filament
3. Schlage Kategorien/Hersteller/Lieferanten aus den vorhandenen Listen vor.
   Wenn nichts passt, schlage einen neuen Eintrag vor und MARKIERE ihn als "new".
4. Wähle das beste Produktbild (Hero-Shot, weißer Hintergrund, ohne Wasserzeichen).
5. Gib Konfidenz pro Feld an, wenn unsicher.
6. Antworte AUSSCHLIESSLICH als JSON nach Schema v1.0 — keine Erklärung davor/danach.
</task>
```

### 8.3 Konfidenz und Re-Enrichment

Wenn `confidence_overall < 0.7`, springt der Job auf `review_partial` und kennzeichnet die schwachen Felder. Der Approver kann:

- **Annehmen wie vorgeschlagen**
- **Felder editieren**
- **Re-Enrich anfordern** mit Hinweis (z.B. "Es ist ein Netzteil, kein Notebook" oder "schau auf [Hersteller-Link]")

Der Hinweis fließt in den Prompt zurück und der Worker läuft erneut.

### 8.4 Approval-Modi

| Modus | Verhalten | Anwendung |
|---|---|---|
| **strict** | Jeder Job geht durch Approval (Default) | HomeLab, Mandanten-Setup |
| **auto-high-confidence** | `confidence_overall ≥ 0.95` und keine neuen Dependencies → automatisch anlegen | Bulk-Onboarding nach Inventur |
| **auto-known-ean** | EAN ist bereits in Forager bekannt, identische Klassifikation → automatisch | Wiederkäufe ("noch eine Packung Salz") |

Pro Backend und pro User einstellbar.

---

## 9. Backend-Integration: Snipe-IT als Referenz

### 9.1 API-Endpunkte (relevanter Auszug)

Snipe-IT verfügt über REST-Routen für Manufacturers, Suppliers, Models, Categories, Statuslabels, Assets, Accessories, Consumables und Components. Damit haben wir alle nötigen Bausteine für Forager.

| Snipe-IT-Endpunkt | Zweck in Forager |
|---|---|
| `GET /api/v1/manufacturers?search=Dell` | Dependency-Resolution |
| `POST /api/v1/manufacturers` | Anlegen neuer Hersteller |
| `GET /api/v1/categories?search=Laptop` | Dependency-Resolution |
| `POST /api/v1/categories` | Anlegen neuer Kategorien |
| `GET /api/v1/suppliers?search=Amazon` | Dependency-Resolution |
| `POST /api/v1/suppliers` | Anlegen neuer Lieferanten |
| `GET /api/v1/models?search=Latitude` | Dependency-Resolution |
| `POST /api/v1/models` | Anlegen Asset-Modell |
| `POST /api/v1/hardware` | Anlegen Asset |
| `POST /api/v1/hardware/{id}/upload` | Bild hochladen |
| `POST /api/v1/accessories` | Anlegen Zubehör |
| `POST /api/v1/consumables` | Anlegen Verbrauchsmaterial |
| `POST /api/v1/components` | Anlegen Komponente |

Wichtig zu beachten: Die Snipe-IT API liefert bei GET-Aufrufen verschachtelte Objekte für Category und Manufacturer, erwartet bei POST/PUT aber flache ID-Felder (category_id, manufacturer_id). Das Plugin abstrahiert das.

### 9.2 Snipe-IT-Asset-Anlage-Sequenz

```
1. CHECK   GET    /manufacturers?search=<name>          → existing or new
   IF new: POST   /manufacturers                         → manufacturer_id
   
2. CHECK   GET    /categories?search=<name>             → existing or new
   IF new: POST   /categories                            → category_id

3. CHECK   GET    /models?search=<model_name>           → existing or new
   IF new: POST   /models                                → model_id
           {name, manufacturer_id, category_id, model_number, eol}

4. CHECK   GET    /suppliers?search=<supplier_name>     → existing or new
   IF new: POST   /suppliers                             → supplier_id

5. POST    /hardware                                     → asset_id, asset_tag
           {model_id, status_id, name, serial, supplier_id, purchase_cost,
            purchase_date, rtd_location_id, custom_fields...}

6. POST    /hardware/{asset_id}/upload                  → upload image
```

Jeder Schritt wird **vor** dem Schreiben dem Approver in der UI gezeigt. Wenn der Approver einen Hersteller ablehnt und einen bestehenden wählt, wird `1.` nicht ausgeführt, sondern die `manufacturer_id` direkt aus dem bestehenden Eintrag genommen.

### 9.3 Asset-Kind-Mapping

Claude klassifiziert in 5 Snipe-IT-Asset-Kinder; das Plugin routet entsprechend:

| Claude-Output | Snipe-IT-Endpunkt | Mengen-Tracking |
|---|---|---|
| `hardware` | `/hardware` | Individuell (eindeutige Asset-Tags) |
| `accessory` | `/accessories` | Anzahl, kein Asset-Tag |
| `consumable` | `/consumables` | Anzahl, "verbraucht sich" |
| `component` | `/components` | Anzahl, an Hardware koppelbar |
| `license` | `/licenses` | Seats, an User koppelbar |

Das ist eine sinnvolle Erweiterung deines Beispiels "Netzteil für Dell Latitude 7400": Claude würde das als `accessory` klassifizieren, weil es zwar ein Hardware-Teil ist, aber meist nicht einzeln getrackt (kein Service-Tag). Ein Notebook selbst dagegen ist `hardware`.

### 9.4 Hangar-Integration: Standort = Tag

Der `target_location` aus dem Job ist die Hangar-Tag-ID (z.B. `HH-AK-KX10-F0203`). Das Snipe-IT-Plugin in Forager nutzt Hangars `LookupByID`-Capability, um den Tag in einen `rtd_location_id` aufzulösen. Damit landen alle neuen Assets sofort an der korrekten physischen Stelle.

---

## 10. Backend-Integration: Grocy & Spoolman (Phase 2)

Die gleiche Plugin-Architektur, andere Endpunkte:

**Grocy** — die kanonische Schwierigkeit ist die **Mengeneinheiten-Hierarchie** (Bestandsmengeneinheit, Einkaufsmengeneinheit, Verbrauchsmengeneinheit + ME-Umrechnungen). Aus deinen Screenshots: ein Alpen JodSalz wird in Gramm getrackt, in Packungen gekauft, Umrechnung 1 Packung = 500 Gramm. Claude muss diese Hierarchie aus dem Provider-Bag rekonstruieren und das Grocy-Plugin legt sie über `/api/objects/quantity_unit_conversions` an.

Zusätzlich Grocy-Spezifika:
- Geschäft (`shopping_locations`) — meist aus `commerce.supplier`
- Standort (`locations`) — Hangar-Tag
- Produktgruppe — aus `classification.grocy.product_group_suggestion`
- Preis pro Geschäft — über `/api/stock/products/{id}/add` mit `shopping_location_id`

**Spoolman** — relevant nur wenn `classification.spoolman` gefüllt ist. SpoolmanDB-Lookup liefert Hersteller, Material, Farbe, Dichte, Durchmesser. Webseiten-Scraping ergänzt um Spool-Gewicht und Preis. Anlage über Spoolman `POST /api/v1/filament` und ggf. `POST /api/v1/spool`.

Da du explizit gesagt hast "Snipe-IT zuerst, andere als Plugins nach MVP" — die Plugin-Interfaces (siehe Section 11) werden trotzdem von Tag 1 so designt, dass Grocy/Spoolman ohne Refactoring nachgezogen werden können.

---

## 11. Plugin-Architektur (geteilt mit Hangar)

### 11.1 Capability-Interfaces (Go)

```go
package plugin

// Bestehende Hangar-Capabilities (Inventur-Sicht)
type Searcher interface {
    Search(ctx context.Context, query string) ([]Item, error)
}
type LookupByID interface {
    Lookup(ctx context.Context, id string) (*Item, error)
}
type Mover interface {
    Move(ctx context.Context, itemID, sourceLoc, targetLoc, actor string) error
}

// Neue Forager-Capabilities (Onboarding-Sicht)
type Creator interface {
    Create(ctx context.Context, payload CreatePayload) (*CreateResult, error)
}

type DepResolver interface {
    // Sucht oder erzeugt Stammdaten-Abhängigkeiten
    ResolveDep(ctx context.Context, dep DepRequest) (*DepResolution, error)
}

type ImageUploader interface {
    UploadImage(ctx context.Context, itemID string, image ImageBlob) error
}

type TaxonomyProvider interface {
    // Liefert das, was Claude im Prompt als 'backend_taxonomies' braucht
    Categories(ctx context.Context) ([]Taxonomy, error)
    Manufacturers(ctx context.Context) ([]Taxonomy, error)
    Suppliers(ctx context.Context) ([]Taxonomy, error)
}

// Optional, für Idempotenz (P4)
type ExternalKeyLookup interface {
    LookupByEAN(ctx context.Context, ean string) (*Item, error)
}
```

Ein Plugin implementiert nur das, was es kann. Das Snipe-IT-Plugin: `Searcher`, `LookupByID`, `Mover`, `Creator`, `DepResolver`, `ImageUploader`, `TaxonomyProvider`. Das Grocy-Plugin (Phase 2): alles außer Mover ist trivial. Das Spoolman-Plugin: kein Mover (wie heute schon in Hangar).

### 11.2 Verzeichnisstruktur (Forager-Repo)

```
forager/
├── README.md
├── docker-compose.yml
├── .env.example
├── cmd/
│   ├── api/                  # Go: Forager REST API
│   │   └── main.go
│   └── worker/               # Python: Enrichment Worker
│       └── main.py
├── internal/                 # Go (gemeinsam mit Hangar als git-submodule oder shared pkg)
│   ├── plugins/
│   │   ├── snipeit/
│   │   ├── grocy/
│   │   └── spoolman/
│   ├── plugin/               # Capability-Interfaces
│   ├── models/               # Bun-ORM-Modelle
│   ├── api/
│   │   ├── jobs.go
│   │   ├── approvals.go
│   │   └── sse.go
│   └── auth/
├── worker/                   # Python
│   ├── pyproject.toml
│   ├── forager_worker/
│   │   ├── main.py
│   │   ├── providers/
│   │   │   ├── openfoodfacts.py
│   │   │   ├── openproductsfacts.py
│   │   │   ├── spoolmandb.py
│   │   │   ├── marktguru.py
│   │   │   └── google_shopping.py
│   │   ├── scrapers/
│   │   │   ├── base.py
│   │   │   ├── amazon.py
│   │   │   ├── lidl.py
│   │   │   ├── rewe.py
│   │   │   ├── obi.py
│   │   │   ├── mediamarkt.py
│   │   │   └── generic.py
│   │   ├── claude/
│   │   │   ├── client.py
│   │   │   ├── prompts/
│   │   │   └── schemas.py
│   │   ├── images.py
│   │   └── queue.py
│   └── tests/
├── pwa/                      # React-PWA
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── public/
│   │   ├── manifest.webmanifest
│   │   └── sw.js
│   └── src/
│       ├── routes/
│       │   ├── ScanRoute.tsx
│       │   ├── JobListRoute.tsx
│       │   ├── JobDetailRoute.tsx
│       │   └── ApprovalRoute.tsx
│       ├── components/
│       │   ├── Scanner.tsx
│       │   ├── BluetoothScanner.tsx
│       │   ├── ImagePicker.tsx
│       │   └── DependencyResolver.tsx
│       └── lib/
│           ├── api.ts
│           └── sse.ts
├── docs/
│   ├── architecture.md
│   ├── schema-v1.0.md
│   ├── plugin-writing.md
│   └── deployment.md
├── deploy/
│   ├── traefik/
│   └── pangolin/
└── tests/
    ├── e2e/
    └── fixtures/
        ├── alpen-jodsalz.json
        ├── dell-latitude-7400.json
        └── lidl-laser.json
```

---

## 12. PWA-Konzept

### 12.1 Routen

| Route | Zweck |
|---|---|
| `/` | Dashboard: meine offenen Jobs, Jobs zur Freigabe, Schnellscan-Button |
| `/scan` | Vollbild-Kamera-Scanner für EAN/QR + Modus-Switch für Bluetooth-Scanner |
| `/new` | Formular: URL, manuelle Eingabe, Foto-Upload als Eingabe |
| `/jobs` | Liste aller Jobs mit Filter (Status, Backend, Datum) |
| `/jobs/:id` | Detail + Approval-UI |
| `/settings` | Backend-Auswahl, Standard-Standort, Scanner-Pairing |

### 12.2 Scan-Workflow (das wichtigste UI)

```
┌──────────────────────────────┐
│  [≡]   FORAGER       [📷⚡]   │
│ ────────────────────────────│
│                              │
│    ╔══════════════════╗     │
│    ║                  ║     │
│    ║   ┌────────┐     ║     │ <- Live-Kameraview
│    ║   │EAN ROI │     ║     │    mit ZXing-JS
│    ║   └────────┘     ║     │
│    ║                  ║     │
│    ╚══════════════════╝     │
│                              │
│  Letzter Scan:               │
│  📋 4337256064880            │
│  → Suche läuft...            │
│                              │
│ ────────────────────────────│
│  [Backend: Snipe-IT ▾]      │
│  [Standort: HH-AK-KX10-F02] │
│  [Kommentar: ...           ] │
│                              │
│        [✓ AUFTRAG ANLEGEN]   │
└──────────────────────────────┘
```

Nach Scan wird sofort ein Pre-Lookup gegen die EAN-Datenbanken gemacht (optimistisch, im Hintergrund). Wenn ein Treffer da ist, sieht der User schon im Scan-Screen "→ Alpen JodSalz (Rewe Beste Wahl)" und kann mit hoher Sicherheit "Auftrag anlegen" tippen.

### 12.3 Approval-Workflow

```
┌────────────────────────────────────────┐
│  Job #abc12 — review_ready             │
│ ──────────────────────────────────────│
│  📷 [Bild 1] [Bild 2] [Bild 3]  +     │ <- Bildauswahl, Karussell
│       (selected: Bild 1)               │
│                                        │
│  Name:        [Alpen JodSalz       ]  │
│  Hersteller:  [Rewe Beste Wahl ▾ ✓ ]  │ <- ✓ = vorhanden
│  Kategorie:   [Konserven         ▾ ⚠]  │ <- ⚠ = neu, wird angelegt
│  Klasse:      [Verbrauchsmaterial▾]   │
│  EAN:         [4337256064880      ]   │
│  Lieferant:   [Rewe              ▾ ✓ ]│
│  Preis:       [0,69 € / Packung   ]   │
│  Standort:    [HH-AK-KX10-F0203   ]   │
│                                        │
│  Claude-Konfidenz: 92%                 │
│  Quellen: amazon.de, openfoodfacts     │
│ ──────────────────────────────────────│
│  Kommentar an Worker / Approver:       │
│  [                                  ]  │
│                                        │
│  [✗ ABLEHNEN]  [↻ RE-ENRICH]  [✓ OK]  │
└────────────────────────────────────────┘
```

Klick auf "✓ OK" zeigt einen **Confirmation-Dialog**, der zeigt was wirklich geschrieben wird:

```
Beim Anlegen werden folgende Backend-Aktionen ausgeführt:

✓ Hersteller "Rewe Beste Wahl"    (vorhanden, ID=12)
+ Kategorie  "Konserven"           (wird neu angelegt)
✓ Lieferant  "Rewe"                (vorhanden, ID=8)
+ Asset      "Alpen JodSalz"        (wird angelegt, Tag wird vergeben)

[ABBRECHEN]                         [BESTÄTIGEN UND ANLEGEN]
```

### 12.4 Real-Time-Updates per SSE

Statt Polling abonniert die PWA `GET /api/v1/jobs/:id/events` als Server-Sent-Event-Stream. Wenn der Worker zwischen Phasen wechselt, sieht der User sofort:

```
11:30:12  submitted
11:30:14  enriching (provider: openfoodfacts)
11:30:18  enriching (provider: amazon)
11:30:22  enriching (claude structuring)
11:30:25  review_ready
```

Das gibt das Gefühl, das Tool ist "live", und reduziert Frustration bei längerer Verarbeitung.

### 12.5 Bluetooth-Scanner-Pairing

Zwei Modi:

1. **HID-Modus (Standard)** — der Scanner pairt sich als Bluetooth-Tastatur. Die PWA hat ein verstecktes `<input>` mit Fokus, das die Eingabe abfängt. Funktioniert mit fast jedem Scanner. Vorteil: keine Berechtigungen nötig.
2. **BLE-GATT-Modus (Premium)** — über Web Bluetooth API direkt zum Scanner. Erlaubt Steuerung (Vibration, LED, Trigger), funktioniert aber nur mit kompatiblen Scannern und nur in Chromium-Browsern. Optional einschaltbar.

### 12.6 Offline-Fähigkeit

Service Worker cached App-Shell. Scans im Offline-Modus werden lokal in IndexedDB gepuffert und beim nächsten Online-Event synchronisiert. Approvals brauchen Online — der Worker und die Backend-APIs sind nicht offline.

---

## 13. Sicherheit, Auth & Multi-User

### 13.1 Authentifizierung

Forager hat **keine eigene User-DB**. Optionen:

- **Authentik / Authelia** als OIDC-Provider (deine bestehende HomeLab-Lösung)
- **Hangar-Session-Sharing** wenn Hangar und Forager auf gleicher Domain laufen
- **API-Token** für Service-to-Service (z.B. CI-Pipeline-Onboarding)

### 13.2 Autorisierung

Rollen pro Backend separat konfigurierbar:

| Rolle | Rechte |
|---|---|
| `scanner` | Jobs erstellen, eigene Jobs sehen |
| `approver` | Alle Jobs in zugewiesenen Backends sehen + freigeben |
| `admin` | Backend-Konfiguration, alle Jobs, Auto-Approve-Regeln |

### 13.3 Geheimnis-Verwaltung

- Snipe-IT/Grocy/Spoolman-API-Tokens und Anthropic-Key via `.env` oder Docker Secrets.
- **Niemals** in der DB oder im Frontend.
- Forager-zu-Backend-Calls laufen ausschließlich vom Server, nie vom Browser.

### 13.4 Audit-Trail (P7)

Jede Mutation in `audit_log`:
- Wer (User-ID, Worker-ID)
- Was (action: submit/enrich/approve/create/reject)
- Wann (TIMESTAMPTZ)
- Detail (vorher/nachher als JSONB)

Das ist die KRITIS/NIS2-relevante Spur, die du in deinen MSP-Mandaten ohnehin brauchst.

### 13.5 PII und Speicherbegrenzung

- Bilder und Roh-HTML der Provider werden in S3/MinIO gehalten und nach **90 Tagen** automatisch gelöscht (nach `done`-Status).
- Abgelehnte Jobs werden nach **30 Tagen** vollständig (inkl. Artefakte) gelöscht.
- Anthropic-API-Calls verwenden den `no-retain`-Mode falls verfügbar.

---

## 14. Deployment im HomeLab Maschen

```yaml
# docker-compose.yml (gekürzt)
services:
  forager-postgres:
    image: postgres:17
    volumes: [forager-pg:/var/lib/postgresql/data]
    environment:
      POSTGRES_DB: forager
      POSTGRES_USER: forager
    networks: [forager]

  forager-redis:
    image: redis:7-alpine
    networks: [forager]

  forager-minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    volumes: [forager-minio:/data]
    networks: [forager]

  forager-api:
    build: ./cmd/api
    depends_on: [forager-postgres, forager-redis]
    environment:
      DATABASE_URL: postgres://forager:...@forager-postgres/forager
      REDIS_URL: redis://forager-redis:6379
      HANGAR_BASE_URL: http://hangar:8080
    networks: [forager, traefik]
    labels:
      - traefik.enable=true
      - traefik.http.routers.forager.rule=Host(`forager.strausmann.cloud`)

  forager-worker:
    build: ./worker
    depends_on: [forager-postgres, forager-redis, forager-minio]
    environment:
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      DATABASE_URL: postgres://forager:...@forager-postgres/forager
      REDIS_URL: redis://forager-redis:6379
      S3_ENDPOINT: http://forager-minio:9000
      PLAYWRIGHT_BROWSERS_PATH: /ms-playwright
    deploy:
      replicas: 2     # mehrere parallele Worker
    networks: [forager]

  forager-pwa:
    build: ./pwa
    networks: [forager, traefik]
    labels:
      - traefik.enable=true
      - traefik.http.routers.forager-pwa.rule=Host(`forager.strausmann.cloud`) && PathPrefix(`/`)

networks:
  forager:
  traefik:
    external: true

volumes:
  forager-pg:
  forager-minio:
```

Routing über Pangolin → Traefik (vorhandenes Setup). Optionale Authentik-ForwardAuth-Middleware für `/api/*`.

---

## 15. Standardisierte Aktionen gegen Backend-APIs

Damit Claude und das Plugin-System einheitlich kommunizieren, gibt es ein **kanonisches Aktion-Schema**:

```jsonc
{
  "actions": [
    {
      "step": 1,
      "kind": "ensure_dependency",
      "dep_type": "manufacturer",
      "backend": "snipeit",
      "match_strategy": "fuzzy_name",
      "input": { "name": "Rewe Beste Wahl" },
      "if_not_found": "create",
      "create_payload": { "name": "Rewe Beste Wahl", "url": "https://rewe.de" }
    },
    {
      "step": 2,
      "kind": "ensure_dependency",
      "dep_type": "category",
      "backend": "snipeit",
      "match_strategy": "exact_name",
      "input": { "name": "Konserven", "category_type": "consumable" },
      "if_not_found": "create"
    },
    {
      "step": 3,
      "kind": "create_item",
      "item_type": "consumable",
      "backend": "snipeit",
      "payload": {
        "name": "Alpen JodSalz",
        "manufacturer_id": "{{step1.result.id}}",
        "category_id": "{{step2.result.id}}",
        "qty": 1,
        "purchase_cost": 0.69
      }
    },
    {
      "step": 4,
      "kind": "upload_image",
      "backend": "snipeit",
      "target_ref": "{{step3.result.id}}",
      "image_artifact_id": "img-1"
    }
  ]
}
```

Der Approver sieht diese Aktions-Liste exakt so — sie ist das Vertrags-Dokument zwischen "was Claude meint" und "was im Backend passiert". Variable Substitution (`{{stepN.result.id}}`) wird erst zur Ausführungszeit aufgelöst.

---

## 16. Roadmap

### Phase 1 — MVP (8–10 Wochen)

**Ziel:** Snipe-IT-Onboarding aus EAN-Scan und Amazon/Lidl/REWE-URLs funktioniert end-to-end.

- [ ] Forager-API (Go) mit Job-CRUD, SSE, OIDC-Auth
- [ ] Enrichment-Worker (Python) mit Providern: OpenFoodFacts, OpenProductsFacts
- [ ] Scraper für Amazon, Lidl, REWE, generischer Fallback
- [ ] Claude-Integration via Anthropic-API (Modus A)
- [ ] Snipe-IT-Plugin mit `Creator`, `DepResolver`, `TaxonomyProvider`, `ImageUploader`
- [ ] PWA mit Scan, Job-Liste, Approval-UI, Bildauswahl
- [ ] Docker-Compose-Deployment im HomeLab
- [ ] OpenFoodFacts-Spiegel (Daily Delta)

### Phase 2 — Grocy + Spoolman (4–6 Wochen)

- [ ] Grocy-Plugin (inkl. Quantity-Unit-Conversions, Shopping-Locations)
- [ ] Spoolman-Plugin (inkl. SpoolmanDB-Spiegel)
- [ ] Marktguru-Provider-Anbindung (Wiederverwendung des bestehenden Harvesters)
- [ ] Cross-Backend-Routing (ein Scan kann mehrere Backends bedienen — z.B. Filament gleichzeitig in Spoolman + als Verbrauchsmaterial in Snipe-IT)

### Phase 3 — Advanced (4–6 Wochen)

- [ ] Claude-Code-Subprozess (Modus B) für komplexe Recherchen
- [ ] Auto-Approve-Regeln (high-confidence + known-EAN)
- [ ] Bulk-Onboarding (CSV-Upload, mehrere EANs)
- [ ] Mandanten-Modus (Multi-Snipe-IT für MSP-Kunden, jeder Tenant getrennt)
- [ ] Hardware-Scanner-spezifische BLE-GATT-Plugins (Eyoyo, Inateck)
- [ ] Dashboard-Widgets für Hangar (Forager-Jobs als Card auf Hangar-Startseite)

### Phase 4 — Ökosystem (offen)

- [ ] Eigenes Forager-Plugin-SDK (analog zu Hangar) für Drittsysteme (Mercurial-, Zammad-, Intune-Integration)
- [ ] LLM-Provider-Abstraktion (lokale Modelle via Ollama als Fallback, deine Hetzner-GPU-Erfahrung)
- [ ] Public-Beta unter `forager.strausmann.cloud` für Community-Feedback

---

## 17. Offene Fragen & Risiken

| # | Punkt | Bemerkung |
|---|---|---|
| **R1** | **Anti-Bot bei Amazon/MediaMarkt** | Playwright wird teilweise erkannt. Residential-Proxy als Fallback, oder Cookie-Reuse aus echtem Browser-Login. Tradeoff: Aufwand vs. Trefferquote. |
| **R2** | **Anthropic-Kosten** | Pro Enrichment ca. 5–15k Tokens In + 1–2k Out. Bei 100 Jobs/Tag und Opus → kalkulierbar. Sonnet als Default für 95% reicht völlig. |
| **R3** | **Bildurheberrecht** | Bilder von Amazon/Hersteller-Seiten sind nicht frei. Für private/MSP-interne Nutzung unkritisch, für öffentliches Inventarsystem rechtliche Prüfung nötig. OFF-Bilder sind CC-BY-SA. |
| **R4** | **EAN-Treffer bei Hardware** | Notebooks und Netzteile haben oft keine EAN auf dem Produkt selbst (nur auf der Verpackung). Daher: MPN (Manufacturer Part Number) als zweites Identifikationskriterium. |
| **R5** | **Sprache der Backend-Taxonomien** | Wenn Snipe-IT-Kategorien deutsch sind, aber Hersteller-Seite englisch scrapet — Claude muss matchen. Lösung: Fuzzy-Matching + explizite Übersetzungs-Hinweise im Prompt. |
| **R6** | **Mengeneinheit-Komplexität bei Grocy** | Aus 1× Smartphone-Scan eine korrekte 3-stufige ME-Hierarchie zu rekonstruieren ist nicht trivial. Möglich, dass `review_partial` hier häufiger nötig ist. |
| **R7** | **Concurrent Approvals** | Wenn zwei Approver gleichzeitig dieselben neuen Dependencies sehen, könnte es zu Duplikaten kommen. Lösung: Optimistic Locking auf `dependency_proposals` plus Dedup-Check direkt vor Backend-Write. |
| **R8** | **Hangar-Integration** | Forager nutzt Hangar-Plugins als Bibliothek. Wenn Hangar Plugin-Interfaces ändert, muss Forager mit. Lösung: Shared Go-Modul mit semantischer Versionierung, Forager pinnt eine Version. |

---

## 18. Erfolgskriterien

Ein MVP gilt als erfolgreich, wenn:

1. **Time-to-Asset** (Zeit zwischen Scan und vollständigem Snipe-IT-Eintrag) < 90 Sekunden bei ungestörtem Workflow.
2. **Approval-Aufwand** ≤ 15 Sekunden pro Job (Sichtprüfung + Klick) für typische Items.
3. **Trefferrate** ≥ 80 % bei EAN-Scans (Item korrekt identifiziert ohne manuelle Korrektur).
4. **Dependency-Duplikate** = 0 (jede neue Kategorie/Hersteller/Lieferant entsteht nur dann, wenn wirklich nicht vorhanden).
5. **Snipe-IT-Datenqualität** messbar besser: Vor/Nach-Vergleich der "Vollständigkeit-Quote" (welcher Anteil der Items hat Bild, Hersteller, Lieferant, Preis, Kategorie).

---

## 19. Quick-Start für Entwicklung

```bash
# 1. Repo clonen
git clone https://git.strausmann.de/strausmann/forager.git
cd forager

# 2. Env vorbereiten
cp .env.example .env
$EDITOR .env   # ANTHROPIC_API_KEY, SNIPEIT_TOKEN, SNIPEIT_URL, ...

# 3. Stack hochfahren
docker compose up -d

# 4. PWA aufrufen
open https://forager.strausmann.cloud

# 5. Test-Scan
# EAN 4337256064880 (Alpen JodSalz) eintippen oder scannen
# → Job sollte in <30s im 'review_ready' landen
```

Build und Tests laufen **wie bei Hangar** ausschließlich im GitLab-Runner — keine Go/Python-Toolchain auf dem Host:

```bash
# Go
docker run --rm -v "$PWD:/app" -w /app golang:1.25-alpine sh -c \
  "apk add --no-cache git gcc musl-dev bash >/dev/null && go test -buildvcs=false ./... -count=1"

# Python
docker run --rm -v "$PWD/worker:/app" -w /app python:3.13-slim sh -c \
  "pip install -e .[dev] && pytest"
```

---

## 20. Receipt Intelligence — Kassenbon-Verarbeitung & Lernsystem

Dieses Kapitel ergänzt Forager um einen **eigenständigen, aber tief integrierten Workflow**: Kassenbons werden gescannt oder als PDF hochgeladen, OCR und Claude extrahieren Positionen, gegen ein versioniertes **Händler-Profil-Repository** abgeglichen und über Produkt-Mappings idempotent in Grocy oder Snipe-IT gebucht.

Der Grundgedanke ist *Learning Without Drift*: das System wird mit jedem Bon klüger, aber alle Verbesserungen sind explizit, versioniert und überprüfbar — keine implizit driftenden ML-Modelle.

### 20.1 Designprinzipien (Ergänzung zu Section 3)

| # | Prinzip | Konsequenz |
|---|---|---|
| **P9** | **Explicit Learning** | Jede neue Erkenntnis (Händler-Layout, Produkt-Mapping) wird als Code/Daten-Artefakt mit Versionierung gespeichert — keine Black-Box-ML-Weights. |
| **P10** | **Community-First für Layouts** | Händler-Profile leben in einem öffentlichen Git-Repo (`forager-merchants`). Layouts sind nicht personenbezogen und profitieren von Crowdsourcing. |
| **P11** | **Privacy-First für Käufe** | Tatsächliche Kassenbons, Produkt-Mappings, Einkaufshistorie bleiben pro-User in lokaler Forager-DB. Niemals im Git-Repo. |
| **P12** | **OCR ist Werkzeug, nicht Wahrheit** | Rohe OCR-Tokens werden bewahrt. Claude und Layout-Regeln interpretieren — wenn eine Interpretation falsch ist, lässt sie sich aus den Rohdaten neu ableiten. |
| **P13** | **Idempotenz auch hier** | Derselbe Bon zweimal hochgeladen → keine doppelte Buchung. Hash über (Händler, Datum, Uhrzeit, Summe, Positionen) als Dedup-Schlüssel. |

### 20.2 High-Level-Flow

```
┌───────────────┐    ┌──────────────┐    ┌──────────────────┐    ┌────────────┐
│ PWA: Scan/PDF │ →  │ Forager API  │ →  │ Receipt Worker   │ →  │ Approval   │
│ Upload        │    │ (POST receipt)│    │ (OCR + Claude)   │    │ UI         │
└───────────────┘    └──────────────┘    └────────┬─────────┘    └─────┬──────┘
                                                  │                    │
                                                  ▼                    ▼
                                         ┌────────────────┐    ┌──────────────┐
                                         │ Merchant       │    │ Backend      │
                                         │ Profile Repo   │    │ Booking      │
                                         │ (Git-Submodule)│    │ (Grocy/      │
                                         └────────────────┘    │  Snipe-IT)   │
                                                               └──────────────┘
```

### 20.3 Drei-Schicht-Lernmodell

Das ist das konzeptionelle Herzstück. Forager lernt auf **drei klar getrennten Ebenen**:

**Schicht 1 — Layout-Profile (global, Git-versioniert)**

> "Wie sieht ein REWE-Bon aus?"

Versionierte YAML-Dateien im Repo `forager-merchants`. Beschreiben das *strukturelle Layout* einer Händler-Kassenbon-Vorlage: Wo steht der Händlername? Wie sind Positionszeilen aufgebaut? Welche Spalten gibt es? Wie sieht ein Mehrzeilen-Eintrag aus? Wie ist Pfand markiert?

Diese Profile sind **nicht personenbezogen** — sie beschreiben öffentliche Geschäftsdokumente. Daher Open-Source.

**Schicht 2 — Produkt-Aliase (pro User, lokale DB)**

> "Auf REWE-Bons heißt 'YOG.PFIRSICH 500G' = mein Grocy-Produkt 'Joghurt Pfirsich (Edeka Gut & Günstig)'"

Mappings zwischen der **Bon-Kurzschreibweise eines Händlers** und dem **konkreten Backend-Produkt eines Users**. Diese Mappings sind hochpersönlich — du kaufst andere Marken als jemand anderes, und auch dieselbe Bon-Bezeichnung kann auf unterschiedliche Backend-Produkte zeigen.

Daher: **lokal pro Forager-Instanz**, nie im Git-Repo.

**Schicht 3 — Heuristiken & Regeln (global, Git-versioniert)**

> "Wenn '8 % MwSt' am Zeilenende, dann ist es Lebensmittel. Wenn '+0,25 PFAND', dann Pfand-Position."

Verallgemeinerbare Regeln, die *händlerübergreifend* gelten. Werden ebenfalls im Git-Repo gepflegt, aber in einer separaten Ebene unterhalb der Händler-Profile.

### 20.4 Das Git-Repository `forager-merchants`

```
forager-merchants/
├── README.md
├── CONTRIBUTING.md
├── LICENSE                      # CC-BY-SA 4.0 (Layouts sind Daten, nicht Code)
├── schema/
│   ├── merchant-profile.v1.json # JSON-Schema für Validierung
│   └── heuristic.v1.json
├── merchants/
│   ├── de/
│   │   ├── rewe/
│   │   │   ├── profile.yaml
│   │   │   ├── samples/         # anonymisierte Beispiel-Bons
│   │   │   │   ├── 2024-classic.txt
│   │   │   │   ├── 2025-self-checkout.txt
│   │   │   │   └── 2026-payback.txt
│   │   │   └── tests/
│   │   │       └── parse_test.yaml  # erwartete Parse-Outputs
│   │   ├── lidl/
│   │   ├── aldi-nord/
│   │   ├── aldi-sued/
│   │   ├── edeka/
│   │   ├── kaufland/
│   │   ├── rossmann/
│   │   ├── dm/
│   │   ├── obi/
│   │   ├── bauhaus/
│   │   ├── ikea/
│   │   └── mediamarkt/
│   ├── at/
│   ├── ch/
│   └── _generic/                # Fallback-Regeln
│       └── profile.yaml
├── heuristics/
│   ├── pfand.yaml               # Pfand-Erkennung deutschlandweit
│   ├── mwst-categories.yaml     # 7% vs. 19% Mappings
│   ├── weight-items.yaml        # Wiegeartikel (Fleisch, Obst, etc.)
│   ├── coupon-discounts.yaml
│   └── payback-bonus.yaml
└── ci/
    ├── validate-profiles.sh
    └── run-parse-tests.sh
```

**Versionierung & Distribution:**
- Forager pinnt eine bestimmte Commit-SHA des Repos
- Updates per `forager update merchants --to <sha>` (Approval-pflichtig)
- Im Docker-Image wird das Repo als Build-Asset oder als Volume-Mount mitgeliefert
- Validierung in CI: jede Profil-Änderung muss alle `parse_test.yaml`-Cases bestehen

### 20.5 Merchant Profile Schema (Beispiel REWE)

```yaml
# merchants/de/rewe/profile.yaml
schema_version: 1
merchant:
  id: de.rewe
  name: REWE
  country: DE
  brand_variants:
    - "REWE"
    - "REWE Markt"
    - "REWE GROUP"
  detection:
    # Wie erkennt man REWE-Bons?
    header_patterns:
      - regex: '^\s*REWE\s+Markt\s+GmbH'
        confidence: 1.0
      - regex: '^\s*REWE'
        confidence: 0.7
      - regex: 'reweGroup\.de|rewe\.de'
        confidence: 0.9
    footer_patterns:
      - regex: 'EUR\s*\d+,\d{2}\s*$'    # Summe am Ende
        confidence: 0.3
    logo_hash: null                       # optional: SHA256 eines bekannten Logos

layout:
  # Bon-Aufbau
  sections:
    - id: header
      until_marker: '^[-=]{5,}'           # Trennlinie endet Header
      contains: [merchant_name, address, store_number]
    - id: items
      until_marker: '^SUMME|^Gesamt|^Zu zahlen'
      multiline: true                     # REWE nutzt 2-Zeilen-Items
    - id: totals
      until_marker: '^Zahlart|^EC-Cash|^MasterCard'
    - id: payment
      until_marker: '$'

  item_layout:
    # Wie sieht eine typische Item-Zeile aus?
    primary_pattern: |
      ^(?P<name>.{1,30})\s+(?P<price>\d+,\d{2})\s+(?P<tax_class>[AB])?\s*$
    
    # Mehrzeilig: Manchmal steht der Preis in Zeile 2
    multiline_patterns:
      - description: "Wiegeartikel mit Preis-pro-Kilo in Folgezeile"
        primary: '^(?P<name>.{1,30})$'
        secondary: '^\s+(?P<weight>\d+,\d{3})\s*kg\s+x\s+(?P<price_per_kg>\d+,\d{2})\s*EUR/kg\s+(?P<total>\d+,\d{2})\s+[AB]$'
        result_kind: weight_item
      
      - description: "Mengenartikel mit Stückpreis"
        primary: '^(?P<name>.{1,30})$'
        secondary: '^\s+(?P<qty>\d+)\s*Stk\s+x\s+(?P<unit_price>\d+,\d{2})\s+(?P<total>\d+,\d{2})\s+[AB]$'
        result_kind: quantity_item

  pfand:
    detection:
      - regex: '(?i)PFAND\s+(?P<amount>\d+,\d{2})'
      - regex: '(?i)EINWEG\s+(?P<amount>\d+,\d{2})'
      - regex: '(?i)MEHRWEG\s+(?P<amount>\d+,\d{2})'
    attach_to: previous_item   # Pfand gehört zur Zeile davor

  discounts:
    detection:
      - regex: '^\s*RABATT\s+-(?P<amount>\d+,\d{2})'
      - regex: '^\s*COUPON\s+-(?P<amount>\d+,\d{2})'
      - regex: '^\s*PAYBACK.*-(?P<amount>\d+,\d{2})'
    attach_to: previous_item

  date_extraction:
    patterns:
      - regex: '(?P<date>\d{2}\.\d{2}\.\d{4})\s+(?P<time>\d{2}:\d{2}(:\d{2})?)'
        date_format: "%d.%m.%Y"
        time_format: "%H:%M"

  totals:
    grand_total: 'SUMME\s+EUR\s+(?P<amount>\d+,\d{2})'
    tax_breakdown:
      - regex: '^\s*A\s+7,0\s*%\s+(?P<net>\d+,\d{2})\s+(?P<tax>\d+,\d{2})\s+(?P<gross>\d+,\d{2})'
        class: A
        rate: 0.07
      - regex: '^\s*B\s+19,0\s*%\s+(?P<net>\d+,\d{2})\s+(?P<tax>\d+,\d{2})\s+(?P<gross>\d+,\d{2})'
        class: B
        rate: 0.19

normalization:
  # Bon-spezifische Abkürzungen → kanonische Begriffe
  abbreviations:
    "BIO":  "Bio"
    "GETR": "Getränk"
    "FL":   "Flasche"
    "FRISCH": "Frisch"
    "KG":   "kg"
    "GR":   "Gramm"
    "PCK":  "Packung"
    "PKG":  "Packung"

confidence_thresholds:
  parse_min: 0.7         # darunter → review_partial
  header_detection: 0.6
  item_extraction: 0.75
```

Das ist ein dichtes Dokument, aber jeder Block hat einen klaren Zweck. Wichtig: das Profil ist deklarativ — keine Python/Go-Funktionen, sondern Regex und Selektoren. Damit ist es sprachunabhängig und leicht zu validieren.

### 20.6 Datenmodell (Erweiterung zu Section 5)

```sql
-- Kassenbons als eigene Entität
CREATE TABLE receipts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      TEXT NOT NULL,
    
    -- Original-Asset
    source_kind     TEXT NOT NULL,        -- 'photo', 'pdf', 'email'
    source_url      TEXT NOT NULL,        -- s3://forager/receipts/...
    source_sha256   TEXT NOT NULL,
    
    -- Erkannter Kontext
    merchant_id     TEXT,                  -- 'de.rewe' aus Profil
    merchant_confidence NUMERIC(3,2),
    profile_version TEXT,                  -- 'forager-merchants@abc123'
    purchase_date   DATE,
    purchase_time   TIME,
    store_identifier TEXT,                 -- Filialnummer
    
    -- Totals
    grand_total     NUMERIC(10,2),
    currency        TEXT DEFAULT 'EUR',
    tax_breakdown   JSONB,                 -- [{class:'A', rate:0.07, gross:...}, ...]
    
    -- Verarbeitungs-Status
    status          TEXT NOT NULL,         -- siehe Lifecycle
    parse_method    TEXT,                  -- 'tesseract+profile', 'claude_vision', 'manual'
    raw_ocr_text    TEXT,                  -- vollständiger OCR-Output (zur Re-Analyse)
    raw_ocr_tokens  JSONB,                 -- Tesseract-Token-Boxen mit Confidence
    parse_warnings  JSONB,
    
    -- Idempotenz
    dedup_hash      TEXT NOT NULL,         -- siehe Section 20.11
    
    -- Backend-Routing
    target_backend  TEXT NOT NULL,         -- 'grocy', 'snipeit', 'multi'
    booking_result  JSONB,                 -- {grocy_entries:[...], snipeit_entries:[...]}
    
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    UNIQUE (dedup_hash, created_by)
);

CREATE INDEX idx_receipts_status ON receipts (status) WHERE status NOT IN ('done','rejected');
CREATE INDEX idx_receipts_merchant_date ON receipts (merchant_id, purchase_date);


-- Positionen auf dem Bon
CREATE TABLE receipt_lines (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_id          UUID NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
    line_number         INT NOT NULL,
    
    -- Roh-Daten (was auf dem Bon steht)
    raw_text            TEXT NOT NULL,
    raw_text_lines      JSONB,             -- bei Multi-Line-Items: Original-Zeilen
    raw_bbox            JSONB,             -- {x,y,w,h} für visuelles Debugging
    
    -- Geparste Daten
    parsed_name         TEXT,
    parsed_quantity     NUMERIC(10,3),
    parsed_unit         TEXT,              -- 'Stk', 'kg', 'l', 'g'
    parsed_unit_price   NUMERIC(10,4),
    parsed_total        NUMERIC(10,2),
    parsed_tax_class    TEXT,              -- 'A'=7%, 'B'=19%
    parse_confidence    NUMERIC(3,2),
    
    -- Pfand & Rabatte (als verknüpfte Positionen)
    parent_line_id      UUID REFERENCES receipt_lines(id),  -- für Pfand/Rabatt-Zeilen
    line_kind           TEXT NOT NULL,     -- 'item', 'pfand', 'discount', 'coupon', 'payback'
    
    -- Mapping & Buchung
    matched_alias_id    UUID REFERENCES product_aliases(id),
    matched_backend_id  TEXT,              -- Grocy-Product-ID oder Snipe-IT-Item-ID
    mapping_confidence  NUMERIC(3,2),
    mapping_source      TEXT,              -- 'alias_db', 'fuzzy', 'manual', 'pending'
    
    booking_status      TEXT NOT NULL,     -- 'pending','booked','skipped','manual_needed','error'
    booking_result      JSONB,             -- {grocy_purchase_id:..., new_price:...}
    booking_error       TEXT,
    
    user_note           TEXT
);

CREATE INDEX idx_receipt_lines_receipt ON receipt_lines (receipt_id, line_number);
CREATE INDEX idx_receipt_lines_pending ON receipt_lines (booking_status) WHERE booking_status IN ('pending','manual_needed');


-- Schicht 2: Produkt-Aliase pro User (das eigentliche Lernen)
CREATE TABLE product_aliases (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           TEXT NOT NULL,         -- pro User isoliert
    merchant_id       TEXT NOT NULL,         -- 'de.rewe' aus Profil
    backend           TEXT NOT NULL,         -- 'grocy', 'snipeit'
    backend_item_id   TEXT NOT NULL,         -- Grocy product_id, Snipe-IT asset_id
    
    -- Der eigentliche Alias
    alias_pattern     TEXT NOT NULL,         -- z.B. 'YOG.PFIRSICH 500G'
    alias_pattern_normalized TEXT NOT NULL,  -- normalisiert für Match (lowercase, ohne Sonderzeichen)
    alias_kind        TEXT NOT NULL,         -- 'exact', 'prefix', 'regex'
    
    -- Lern-Metadaten
    confirmed_count   INT NOT NULL DEFAULT 1, -- wie oft bestätigt
    last_confirmed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    first_seen_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by        TEXT NOT NULL,         -- 'user:bjoern' oder 'auto:claude'
    
    -- Optional: pro-Item-Defaults
    default_quantity      NUMERIC(10,3),
    default_unit          TEXT,
    default_quantity_unit_id TEXT,           -- Grocy-spezifisch
    
    UNIQUE (user_id, merchant_id, backend, alias_pattern_normalized)
);

CREATE INDEX idx_aliases_lookup ON product_aliases 
    (user_id, merchant_id, backend, alias_pattern_normalized);


-- Lerntrigger-Log: hilft, drift zu erkennen
CREATE TABLE alias_decisions (
    id              BIGSERIAL PRIMARY KEY,
    user_id         TEXT NOT NULL,
    receipt_line_id UUID NOT NULL REFERENCES receipt_lines(id),
    alias_id        UUID REFERENCES product_aliases(id),
    decision        TEXT NOT NULL,           -- 'created','confirmed','overridden','rejected'
    previous_match  TEXT,
    new_match       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- Schicht 1+3: Profile-Cache (vom Git-Repo importiert)
CREATE TABLE merchant_profiles_cache (
    id              TEXT PRIMARY KEY,       -- 'de.rewe'
    profile_version TEXT NOT NULL,           -- Git-SHA
    profile_yaml    TEXT NOT NULL,
    compiled        JSONB NOT NULL,          -- vorkompilierte Regex, fertig zum Match
    imported_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Beachte das Design: **`receipt_lines.raw_text`** wird **immer** behalten. Selbst wenn das Parsing schiefgeht oder das Mapping korrigiert werden muss — die Rohdaten sind die Wahrheit, alles andere ist abgeleitet (P12).

### 20.7 Verarbeitungs-Pipeline

```python
async def process_receipt(receipt: Receipt) -> ProcessedReceipt:
    # Phase 1: OCR (lokal, mehrstufig)
    ocr_result = await ocr_pipeline.run(receipt.source_url)
    receipt.raw_ocr_text = ocr_result.text
    receipt.raw_ocr_tokens = ocr_result.tokens
    
    # Phase 2: Händler-Erkennung
    merchant = await merchant_detector.detect(
        ocr_text=ocr_result.text,
        profiles=load_all_profiles()
    )
    
    if merchant.confidence < 0.6:
        # Fallback: Claude soll raten
        merchant = await claude_merchant_detection(ocr_result.text)
    
    receipt.merchant_id = merchant.id
    receipt.profile_version = merchant.profile_version
    
    # Phase 3: Profil-gesteuertes Parsing
    profile = load_profile(merchant.id)
    parse_result = profile_parser.parse(ocr_result, profile)
    
    receipt.purchase_date = parse_result.date
    receipt.grand_total = parse_result.total
    receipt.tax_breakdown = parse_result.taxes
    
    # Phase 4: Claude-Verifikation (nur unsichere Positionen)
    uncertain_lines = [l for l in parse_result.lines if l.confidence < 0.85]
    if uncertain_lines:
        claude_result = await claude_refine_lines(
            raw_ocr=ocr_result,
            uncertain_lines=uncertain_lines,
            profile=profile
        )
        parse_result.merge(claude_result)
    
    # Phase 5: Idempotenz-Check
    receipt.dedup_hash = compute_dedup_hash(receipt, parse_result)
    if await is_duplicate(receipt.dedup_hash, receipt.created_by):
        raise DuplicateReceipt(existing_id=...)
    
    # Phase 6: Pfand/Rabatt-Zuordnung
    parse_result = attach_pfand_and_discounts(parse_result, profile)
    
    # Phase 7: Produkt-Mapping (pro Zeile)
    for line in parse_result.lines:
        if line.line_kind != 'item':
            continue
        
        mapping = await resolve_product_mapping(
            user_id=receipt.created_by,
            merchant_id=merchant.id,
            backend=receipt.target_backend,
            line=line
        )
        line.matched_alias_id = mapping.alias_id
        line.matched_backend_id = mapping.backend_id
        line.mapping_confidence = mapping.confidence
        line.mapping_source = mapping.source  # 'alias_db' / 'fuzzy' / 'pending'
        
        if mapping.confidence < 0.85:
            line.booking_status = 'manual_needed'
        else:
            line.booking_status = 'pending'  # wartet auf Approval
    
    # Phase 8: Approval-Vorbereitung
    receipt.status = 'review_ready' if all_lines_mapped_or_skipped(parse_result) else 'review_partial'
    
    return parse_result
```

Das ist ein **mehrstufiger Trichter**: deterministische Regeln aus dem Profil zuerst (billig, schnell), Claude nur dort, wo Regeln scheitern (teuer, langsam). Dadurch bleibt der Großteil der Verarbeitung lokal und kostengünstig.

### 20.8 OCR-Pipeline im Detail

```python
class OCRPipeline:
    """Mehrstufige OCR mit Vorverarbeitung."""
    
    async def run(self, source_url: str) -> OCRResult:
        # Schritt 1: Quelle normalisieren
        if source_url.endswith('.pdf'):
            images = pdf_to_images(source_url, dpi=300)
        else:
            images = [load_image(source_url)]
        
        # Schritt 2: Bildvorverarbeitung
        # Bons sind oft schief fotografiert, ungleichmäßig beleuchtet, knittrig
        processed = []
        for img in images:
            img = deskew(img)                   # Rotation korrigieren
            img = perspective_correct(img)      # Perspektive (z.B. mit OpenCV)
            img = adaptive_threshold(img)       # Binärisierung
            img = remove_noise(img)
            processed.append(img)
        
        # Schritt 3: OCR mit Tesseract (Default) oder PaddleOCR (besser für Deutsch)
        tokens = []
        full_text = []
        for img in processed:
            result = paddleocr.recognize(img, lang='de')
            # PaddleOCR liefert pro Token: text, bbox, confidence
            tokens.extend(result.tokens)
            full_text.append(result.text)
        
        # Schritt 4: Layout-Rekonstruktion
        # PaddleOCR liefert Tokens, wir müssen Zeilen aus Y-Koordinaten rekonstruieren
        lines = reconstruct_lines(tokens, tolerance_px=8)
        
        return OCRResult(
            text='\n'.join(full_text),
            tokens=tokens,
            lines=lines,
            engine='paddleocr',
            engine_version='2.7.0'
        )
```

**Warum PaddleOCR statt Tesseract als Default?** PaddleOCR ist auf gedruckten deutschen Texten und Quittungen deutlich genauer und liefert die Token-Boxen mit, die wir für Multi-Line-Items brauchen. Tesseract bleibt als Fallback drin (z.B. wenn PaddleOCR-Container nicht verfügbar).

### 20.9 Multi-Line-Items: das REWE-Fleisch-Beispiel

Ein typischer Bon-Eintrag für Wiegeartikel:

```
RINDERHACKFLEISCH
   0,452 kg x 8,99 EUR/kg          4,06 B
```

Das Profil definiert das in `multiline_patterns`:

```yaml
multiline_patterns:
  - description: "Wiegeartikel"
    primary: '^(?P<name>[A-ZÄÖÜ][A-ZÄÖÜ\s.-]{1,29})$'
    secondary: '^\s+(?P<weight>\d+,\d{3})\s*kg\s+x\s+(?P<price_per_kg>\d+,\d{2})\s*EUR/kg\s+(?P<total>\d+,\d{2})\s+(?P<tax>[AB])$'
    result_kind: weight_item
```

Der Parser arbeitet zustandsbehaftet: wenn `primary` matcht und die nächste Zeile auf `secondary` passt, wird beides zu **einer** `receipt_line` zusammengeführt:

```json
{
  "raw_text_lines": [
    "RINDERHACKFLEISCH",
    "   0,452 kg x 8,99 EUR/kg          4,06 B"
  ],
  "parsed_name": "RINDERHACKFLEISCH",
  "parsed_quantity": 0.452,
  "parsed_unit": "kg",
  "parsed_unit_price": 8.99,
  "parsed_total": 4.06,
  "parsed_tax_class": "B",
  "line_kind": "item"
}
```

### 20.10 Pfand-Behandlung

```
COCA COLA 1,5L                       1,99 B
   PFAND EINWEG                       0,25 B
```

Profil-Regel:

```yaml
pfand:
  detection:
    - regex: '(?i)PFAND\s+EINWEG\s+(?P<amount>\d+,\d{2})'
  attach_to: previous_item
```

Resultat: Zwei `receipt_lines`-Einträge, wobei der zweite per `parent_line_id` auf den ersten zeigt:

```json
[
  {
    "line_number": 5,
    "raw_text": "COCA COLA 1,5L",
    "parsed_total": 1.99,
    "line_kind": "item",
    "matched_backend_id": "grocy:product:142"
  },
  {
    "line_number": 6,
    "raw_text": "PFAND EINWEG 0,25",
    "parsed_total": 0.25,
    "line_kind": "pfand",
    "parent_line_id": "<id of line 5>"
  }
]
```

Bei der Buchung in Grocy: nur die `item`-Zeile wird als Stock-Add gebucht, der Pfand-Eintrag aktualisiert ggf. ein separates Grocy-Pfand-Produkt oder wird als Metadaten zur Hauptbuchung mitgegeben.

### 20.11 Idempotenz-Hash

```python
def compute_dedup_hash(receipt: Receipt, parse: ParseResult) -> str:
    """Stabiler Hash über die invarianten Eigenschaften eines Bons."""
    payload = {
        "merchant": receipt.merchant_id,
        "store": receipt.store_identifier,
        "date": str(parse.date),
        "time": str(parse.time) if parse.time else None,
        "total": str(parse.grand_total),
        "line_count": len(parse.lines),
        "line_totals": sorted([str(l.parsed_total) for l in parse.lines if l.line_kind == 'item'])
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()
```

Damit verhindern wir Doppel-Uploads (z.B. Foto + PDF desselben Bons) zuverlässig. Falls Datum/Uhrzeit/Store fehlen — was bei schlechter OCR vorkommt — fällt der Job auf `review_partial`, statt einen schwachen Hash zu produzieren.

### 20.12 Produkt-Mapping: Resolver-Logik

```python
async def resolve_product_mapping(
    user_id: str, merchant_id: str, backend: str, line: ReceiptLine
) -> MappingResult:
    
    normalized = normalize_alias(line.parsed_name)  
    # lowercase, ä→ae, Sonderzeichen weg, abbreviations.expand
    
    # Versuch 1: Exakter Alias (höchste Konfidenz)
    exact = await db.find_alias(
        user_id=user_id, merchant_id=merchant_id, backend=backend,
        alias_pattern_normalized=normalized, alias_kind='exact'
    )
    if exact:
        # Lern-Counter erhöhen
        await db.increment_alias_confirmation(exact.id)
        return MappingResult(
            alias_id=exact.id, backend_id=exact.backend_item_id,
            confidence=0.98, source='alias_db'
        )
    
    # Versuch 2: Prefix-Match (z.B. "MIL.VOLL 1L" → Alias "MIL.VOLL")
    prefix = await db.find_alias_prefix(user_id, merchant_id, backend, normalized)
    if prefix:
        return MappingResult(
            alias_id=prefix.id, backend_id=prefix.backend_item_id,
            confidence=0.85, source='alias_prefix'
        )
    
    # Versuch 3: Fuzzy gegen alle bisherigen Aliase desselben Users+Händlers
    candidates = await db.fuzzy_search_aliases(
        user_id, merchant_id, backend, normalized,
        algorithm='rapidfuzz_partial_ratio', min_score=80
    )
    if candidates and candidates[0].score >= 90:
        return MappingResult(
            alias_id=candidates[0].id, backend_id=candidates[0].backend_item_id,
            confidence=0.75, source='fuzzy'
        )
    
    # Versuch 4: Fuzzy gegen Backend-Produktnamen (nicht über Alias-DB, sondern direkt im Backend)
    # Hilfreich wenn der User schon Produkte hat aber noch nie über Bon zugeordnet hat
    backend_match = await backend_plugin.fuzzy_search_products(normalized)
    if backend_match and backend_match.score >= 92:
        # Konservativ: Claude verifizieren lassen
        verification = await claude_verify_mapping(
            bon_text=line.raw_text, backend_product=backend_match.product
        )
        if verification.is_match:
            return MappingResult(
                alias_id=None, backend_id=backend_match.id,
                confidence=verification.confidence, source='backend_fuzzy_claude'
            )
    
    # Versuch 5: Pending — User muss manuell mappen
    return MappingResult(
        alias_id=None, backend_id=None,
        confidence=0.0, source='pending'
    )
```

**Lern-Mechanik:** Wenn ein User in der Approval-UI eine `pending`-Zeile auf ein Backend-Produkt mappt, wird automatisch ein `product_aliases`-Eintrag erzeugt:

```python
async def on_manual_mapping(
    user_id: str, line: ReceiptLine, backend_id: str
):
    await db.create_alias(
        user_id=user_id,
        merchant_id=line.receipt.merchant_id,
        backend=line.receipt.target_backend,
        backend_item_id=backend_id,
        alias_pattern=line.parsed_name,
        alias_pattern_normalized=normalize_alias(line.parsed_name),
        alias_kind='exact',
        created_by=f'user:{user_id}'
    )
    # Logging für Drift-Erkennung
    await db.log_alias_decision(
        user_id=user_id, line_id=line.id,
        decision='created', new_match=backend_id
    )
```

Beim **zweiten Mal** dasselbe Produkt: exakter Match aus Schritt 1, automatisch gebucht — das ist das gefühlte "Forager hat gelernt".

### 20.13 Approval-UI für Bons

Erweiterte Detail-Ansicht im Vergleich zum Item-Approval:

```
┌─────────────────────────────────────────────────────────────────┐
│  Kassenbon #r-742a — review_ready                               │
│  REWE · Filiale Schulstraße 61 · 20.05.2026 14:32               │
│  Gesamt: 47,82 EUR                                               │
│ ───────────────────────────────────────────────────────────────│
│  [Bon-Foto]    │  Position │ Match              │ Status        │
│                │  ─────────┼────────────────────┼──────────────│
│  ┌─────────┐   │ 1 MILCH.. │ ✓ Bio-Vollmilch    │ bookable    │
│  │  📷    │   │ 2 RINDERH.│ ✓ Hackfleisch Rind │ bookable    │
│  │ Quelle │   │ 3 BANANE. │ ⚠ neu → mappen    │ pending     │
│  │        │   │ 4 PFAND   │   (→ Position 5)   │ pfand       │
│  │        │   │ 5 COCA C. │ ✓ Coca-Cola 1,5L   │ bookable    │
│  │        │   │ 6 COUPON  │ - (Rabatt)         │ skip        │
│  └─────────┘   │ ...                                            │
│                │                                                │
│  Bon-Quelle:   │  3 von 12 Positionen brauchen Mapping         │
│  upload.pdf    │  [➜ ALLE PENDING MAPPEN]                       │
│ ───────────────────────────────────────────────────────────────│
│  Buchungsziel: [Grocy ▾]      Auto-Lernen: [✓]                 │
│                                                                  │
│  [✗ VERWERFEN]  [✎ TEILBUCHUNG]  [✓ BEKANNTE BUCHEN, REST PEND.]│
└─────────────────────────────────────────────────────────────────┘
```

Auf der rechten Seite ist jede Zeile interaktiv:

```
┌──────────────────────────────────────────────────────────┐
│ Position 3: "BANANE LOSE"                                │
│                                                           │
│  Bon-Text (Original):   BANANE LOSE                      │
│  Bon-Text (Detail):     0,724 kg x 1,99 EUR/kg = 1,44 B  │
│                                                           │
│  Vorschläge aus Grocy:                                   │
│   ○ Bananen Bio (ID 23)                       Match 87% │
│   ○ Bananen Chiquita (ID 47)                  Match 72% │
│   ○ Bananen lose (ID 89)                      Match 95% │
│   ⊙ Bananen lose (ID 89)  ← ausgewählt                   │
│                                                           │
│   [+ Neues Grocy-Produkt anlegen]                        │
│   [⊘ Diese Position überspringen]                        │
│                                                           │
│  ☑ Diese Zuordnung als Alias speichern                   │
│    (zukünftig wird "BANANE LOSE" → "Bananen lose" automatisch) │
└──────────────────────────────────────────────────────────┘
```

Die Approval-Logik aus deiner Anforderung "bekannte sofort buchen, unbekannte als pending" ist hier visualisiert: der Button "BEKANNTE BUCHEN, REST PEND." führt aus, die `pending`-Liste bleibt offen, der User kann später zurückkehren.

### 20.14 Pending-Verwaltung

Eine separate PWA-Route `/receipts/pending` zeigt alle `receipt_lines` mit `booking_status='manual_needed'` quer über alle Bons:

```
┌─────────────────────────────────────────────────────────┐
│  PENDING MAPPINGS  (14 offen)                            │
│ ───────────────────────────────────────────────────────│
│  REWE × 8                                                │
│    "BANANE LOSE"      aus 3 Bons          [→ mappen]   │
│    "BIO MOEHRE B."    aus 2 Bons          [→ mappen]   │
│    ...                                                   │
│                                                          │
│  LIDL × 4                                                │
│    "MILBONA H-MIL"    aus 4 Bons          [→ mappen]   │
│    ...                                                   │
│                                                          │
│  ROSSMANN × 2                                            │
│    ...                                                   │
│ ───────────────────────────────────────────────────────│
│  Tip: Mappings über mehrere Bons hinweg sind             │
│       effizienter — Forager wendet die neue Zuordnung   │
│       rückwirkend auf alle pending-Zeilen an.            │
└─────────────────────────────────────────────────────────┘
```

Wenn ein User hier `"BANANE LOSE"` einmal mappt, werden **alle 3 pending-Zeilen** in den 3 Bons automatisch mit-gebucht (Approval-pflichtig, aber als Bulk).

### 20.15 Preis-Update in Grocy / Forager-Preishistorie

Eine zentrale Anforderung: Einkaufspreise aktuell halten. Pro gebuchter Position:

```python
async def book_grocy_purchase(line: ReceiptLine):
    plugin = grocy_plugin
    
    # Bestand aufstocken
    purchase_response = await plugin.add_stock(
        product_id=line.matched_backend_id,
        amount=line.parsed_quantity,
        best_before=compute_best_before(line, product),
        price=line.parsed_unit_price or (line.parsed_total / line.parsed_quantity),
        shopping_location_id=resolve_shopping_location(line.receipt.merchant_id),
        purchased_date=line.receipt.purchase_date
    )
    
    # Forager-Preishistorie (immer mitführen, unabhängig von Grocy)
    await db.insert_price_history(
        backend='grocy',
        backend_item_id=line.matched_backend_id,
        merchant_id=line.receipt.merchant_id,
        store_identifier=line.receipt.store_identifier,
        price=line.parsed_unit_price,
        quantity=line.parsed_quantity,
        unit=line.parsed_unit,
        date=line.receipt.purchase_date,
        source_receipt_id=line.receipt.id
    )
    
    return purchase_response
```

Die Forager-eigene Preishistorie ist Gold wert: sie zeigt Preisentwicklung über Händler hinweg, auch wenn das jeweilige Backend (Grocy) das nicht so granular speichert. Daraus lässt sich später ein Dashboard bauen: "Bananen lose: REWE 1,99 EUR/kg vs. LIDL 1,49 EUR/kg (Stand: heute)".

### 20.16 Foto-Upload-Workflow (deine andere Anforderung)

> "Wenn man Produkte fotografiert, kann man das Foto bei Grocy, Snipe-IT hochladen, wenn es kein Foto aus den öffentlichen Quellen gibt oder überschrieben werden soll."

Das ist eine generische Funktion und gehört nicht ausschließlich zur Bon-Verarbeitung. Daher als Querschnitt-Feature:

**Trigger:** In jedem Item-Approval-Screen (Section 12.3) oder in der Item-Detail-Ansicht (`/items/:backend/:id`) gibt es einen Button **"Foto aufnehmen / hochladen"**.

**Flow:**

```
PWA Camera → Photo Capture → Local Preview → 
  Optional: Crop/Rotate → Upload to Forager API → 
    Image Pipeline (siehe Section 7.4) → 
      Backend-Plugin.UploadImage(item_id, blob) → 
        Update artifacts table mit 'user_photo'-Source
```

**Konfliktlösung:** Wenn das Item schon ein Bild hat:

```
Dieses Item hat bereits ein Bild von 'openfoodfacts' (Hochgeladen 20.04.2026)

   ○ Neues Bild ersetzt altes
   ○ Neues Bild zusätzlich (Backend unterstützt Multi-Image?)
   ○ Neues Bild als Forager-internes Backup (nicht ans Backend)

   [ABBRECHEN]  [HOCHLADEN]
```

Snipe-IT erlaubt `image` als einzelnes Feld — also Ersetzen. Grocy erlaubt nur ein `picture_file_name` — auch Ersetzen. Bei Snipe-IT-Assets gibt es zusätzlich `file_uploads` für Dokumente, was wir parallel nutzen können.

**Wo die Forager-Foto-Funktion in die Bon-Verarbeitung greift:** Beim Bon-Mapping, wenn der User auf "+ Neues Grocy-Produkt anlegen" klickt, geht der Flow in den ganz normalen Forager-Onboarding-Workflow (Section 12) über — und dort kann man das Foto direkt mit aufnehmen. Damit ist der Onboarding-Pfad einheitlich, unabhängig davon, ob er per Scan, URL oder Bon-Position gestartet wird.

### 20.17 Snipe-IT-Anwendungsfall für Bons

Bons sind nicht nur für Food. Beispiel **OBI-Bon nach Werkzeugkauf**:

```
SDS-PLUS BOHRER 6mm                  3,99 B
AKKU-SCHRAUBER PXC 18V               79,99 B
PAYBACK BONUS                       -2,00
```

- Position 1 → Grocy-Verbrauchsmaterial *oder* Snipe-IT-Komponente, je nachdem wie der User strukturiert
- Position 2 → Snipe-IT-Hardware-Asset

Im Approval kann pro Position das Ziel-Backend gewählt werden — der Bon ist `target_backend='multi'`. Das `merchant_profile` enthält dafür einen Hinweis:

```yaml
default_routing:
  primary: grocy        # für Food-Bons
  hardware_signals:     # wenn diese Strings auf Bon vorkommen → eher Snipe-IT
    - "BOHRER"
    - "SCHRAUBER"
    - "SÄGE"
    - "KABEL"
  override_per_line: true
```

Claude bekommt diesen Hinweis im Prompt und schlägt pro Zeile ein Ziel-Backend vor, der User bestätigt.

### 20.18 Forager-Merchants — CI & Community

```yaml
# .gitlab-ci.yml im forager-merchants Repo

stages:
  - validate
  - test
  - publish

validate-schema:
  stage: validate
  image: python:3.13-slim
  script:
    - pip install jsonschema pyyaml
    - python ci/validate-profiles.py merchants/

parse-tests:
  stage: test
  image: registry.strausmann.de/forager/parser:latest
  script:
    - forager-parser test-all merchants/

publish-release:
  stage: publish
  only: [tags]
  script:
    - tar czf merchants-${CI_COMMIT_TAG}.tar.gz merchants/ heuristics/
    - upload to Forager Marketplace
```

**Contribution-Workflow:**

1. User stößt auf neuen/geänderten Händler-Bon, dessen Profil nicht passt
2. In der PWA: "Profil-Problem melden" → Anonymisierter Bon-Text + erwartete vs. erhaltene Parse-Ergebnisse werden vorbereitet
3. User kann das als GitLab-Issue absenden (mit anonymisierten Daten)
4. Maintainer (du, später Community) prüft, passt Profil an, schreibt einen `parse_test.yaml`-Case
5. PR mergen, neue Version, Forager-Instanzen ziehen Update

Anonymisierung ist hier nicht trivial — Preise, Filialnummern, Zeiten dürfen drinbleiben (relevant für Layout), persönliche Daten wie Payback-Nummer, EC-Karten-Maskierung dürfen nicht. Ein **Anonymisierungs-Helfer in der PWA** ersetzt vor dem Upload alles, was nach personenbezogenem Token aussieht (Karten-PANs, Payback-IDs, Namen aus Mail-Adressen).

### 20.19 Bon-Summen-Plausibilität

Manchmal stimmen Bon-Summen nicht ganz (Centrundungen, fehlende Zeilen, OCR-Fehler bei Preisen). Profil-Parser prüft:

```python
def reconcile_totals(parse: ParseResult) -> List[Warning]:
    warnings = []
    
    computed_total = sum(l.parsed_total for l in parse.lines if l.line_kind in ('item', 'pfand')) \
                   - sum(l.parsed_total for l in parse.lines if l.line_kind in ('discount', 'coupon'))
    
    if abs(computed_total - parse.grand_total) > 0.02:
        warnings.append(Warning(
            kind='total_mismatch',
            detail=f'Summe Positionen: {computed_total}, Bon-Summe: {parse.grand_total}'
        ))
    
    # MwSt-Cross-Check
    for tax_class, breakdown in parse.tax_breakdown.items():
        lines_of_class = [l for l in parse.lines if l.parsed_tax_class == tax_class]
        gross_sum = sum(l.parsed_total for l in lines_of_class)
        if abs(gross_sum - breakdown.gross) > 0.02:
            warnings.append(Warning(
                kind='tax_mismatch',
                detail=f'Klasse {tax_class}: {gross_sum} vs Bon {breakdown.gross}'
            ))
    
    return warnings
```

Warnungen erscheinen prominent in der Approval-UI — das ist die letzte Verteidigungslinie vor falscher Buchung.

### 20.20 Drift-Erkennung

Da das Lernsystem akkumuliert, kann sich Drift einschleichen (falsche Mappings, die sich verfestigen). Forager schaut periodisch:

```sql
-- Aliase, die in den letzten 90 Tagen häufig überschrieben wurden → verdächtig
SELECT alias_pattern, COUNT(*) as overrides
FROM alias_decisions
WHERE decision = 'overridden'
  AND created_at > now() - interval '90 days'
GROUP BY alias_pattern
HAVING COUNT(*) > 3;

-- Aliase, die seit > 1 Jahr nicht mehr bestätigt wurden → vermutlich Produkt vom Markt
SELECT * FROM product_aliases
WHERE last_confirmed_at < now() - interval '1 year';
```

Diese Listen erscheinen unter `/settings/aliases/review` — der User kann aufräumen, ohne dass das System still aufräumt.

### 20.21 Erweiterte Roadmap (Ergänzung zu Section 16)

**Phase 2.5 — Receipt Intelligence (parallel zu Phase 2, 4–6 Wochen)**

- [ ] OCR-Pipeline (PaddleOCR + Tesseract-Fallback) als Docker-Service
- [ ] `forager-merchants` Repo initial mit REWE, Lidl, Aldi-Süd, Edeka, OBI, Rossmann
- [ ] Receipt-Datenmodell + Migrationen
- [ ] Profile-Cache & Hot-Reload bei Git-Update
- [ ] Mapping-Resolver + Lern-Logik
- [ ] PWA-Routen: Receipt-Upload, Receipt-Approval, Pending-Liste
- [ ] Foto-Upload-Querschnitt-Feature (Section 20.16)
- [ ] Anonymisierungs-Helfer
- [ ] Issue-Template "Profil-Problem melden"

**Phase 3 — Erweiterungen**

- [ ] Mehrsprachige Profile (AT, CH)
- [ ] E-Mail-Inbox-Integration: digitale Bons direkt aus dem Postfach (REWE-App, Lidl Plus etc.)
- [ ] Bon-zu-Bon-Vergleich (gleiches Produkt, anderer Tag, anderer Preis → Trend-Erkennung)
- [ ] Marktguru-Cross-Check: gebuchter Preis vs. aktuelles Angebot → Hinweis "Du hättest 0,30 EUR sparen können"

### 20.22 Risiken-Ergänzung (zu Section 17)

| # | Punkt | Bemerkung |
|---|---|---|
| **R9** | **OCR-Qualität bei Foto-Bons** | Knittrige Bons, Thermopapier-Fading, Schräglage → Vorverarbeitung kritisch. Test-Suite mit "schwierigen" realen Bons als Regression-Tests. |
| **R10** | **Layout-Änderungen** | Händler ändern Bon-Layouts (z.B. nach Self-Checkout-Rollout). Lösung: `profile.yaml`-Versionierung mit Datums-Bereichen — "v1: bis 2025-06-30, v2: ab 2025-07-01". |
| **R11** | **Privacy bei Bon-Bildern** | Bons enthalten oft maskierte EC-Karten-PANs, Payback-IDs, Zeiten. Daher: Bon-Originalbilder verschlüsselt at-rest (LUKS auf MinIO-Volume), nach 90 Tagen löschen, nur OCR-Text bleibt. |
| **R12** | **Mapping-Verschmutzung** | Wenn ein User zwei Backend-Produkte für "Milch" hat und mal das eine, mal das andere mappt — Drift. Lösung: Drift-Erkennung (Section 20.20). |
| **R13** | **Pfand auf separatem Bon** | Manche Händler drucken Pfand-Rückgabe als eigenen Bon. Out-of-Scope für MVP, später als "negative Buchung" mit Verknüpfung zum Original-Bon. |

---

## 21. Was als nächstes?

**Empfehlung:** Bevor wir in Code gehen, ein dreistufiger Refinement-Schritt:

1. **Schema-Validierung an realen Beispielen**: Ich nehme die sieben Test-URLs aus deiner Ursprungs-Nachricht (Amazon-Notebook, Amazon-Netzteil, Marktguru-Cola, Lidl-Laser, REWE-Tiefkühl, OBI-Akku, MediaMarkt-iPad) und produziere für jedes ein vollständiges Enrichment-JSON nach Schema v1.0 — als "wäre Forager fertig". Damit sehen wir Lücken im Schema, bevor wir Code schreiben.
2. **Snipe-IT-Aktions-Sequenz simulieren**: Für ein Beispiel komplette Backend-Aktions-Sequenz durchgehen, inkl. Edge-Case "Kategorie 'Notebooks' existiert, aber als 'Laptops'".
3. **Receipt-Profil-Prototyp**: Du nimmst einen echten REWE- oder Lidl-Bon (anonymisiert), wir parsen ihn gemeinsam von Hand und schreiben das `profile.yaml` — dann testen wir, ob die Regeln greifen.

Sag bescheid, womit wir anfangen.

---

*Ende des Konzepts v0.2 (mit Receipt Intelligence)*
