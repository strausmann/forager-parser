"""
The actual parser — turns text + profile into a ParseResult.

Wesentliche Algorithmus-Schritte:
1. Sektions-Identifikation grob (header, items, totals, etc.) — wir bleiben
   pragmatisch und schauen erstmal zeilenweise.
2. Für jede Zeile: Item-Patterns durchprobieren (zuerst Multi-Line mit
   requires_secondary, dann Single-Line). Bei Multi-Line: nächste Zeile
   konsumieren, wenn Secondary matcht.
3. Pfand-Patterns als Sonderfall — können auch eigenständige Aggregat-Items
   sein (Lidl-Stil).
4. Totals, Tax-Breakdown, Loyalty, Datum extrahieren.
5. Plausibilitätscheck: computed_total ≈ grand_total?
"""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Iterable

from .models import (
    AssessmentMetadata,
    Loyalty,
    LoyaltyEvent,
    Merchant,
    OverallConfidence,
    ParsedLine,
    ParseResult,
    Payment,
    ProfileAssessment,
    PurchaseDatetime,
    Store,
    TaxBreakdownRow,
    Totals,
    Warning,
)
from .profile import Profile


def _to_decimal(s: str) -> Decimal:
    """German number string → Decimal. '1,99' → Decimal('1.99')."""
    return Decimal(s.replace(".", "").replace(",", "."))


def _strip_name(name: str, post_strip: list[re.Pattern[str]]) -> str:
    out = name.strip()
    for pat in post_strip:
        out = pat.sub("", out).strip()
    return out


class ParseContext:
    """Mutable state across parsing phases."""

    def __init__(self, profile: Profile, raw_text: str):
        self.profile = profile
        self.raw_lines: list[str] = raw_text.splitlines()
        self.lines: list[ParsedLine] = []
        self.warnings: list[Warning] = []
        self.matched_pattern_ids: dict[str, list[int]] = {}
        self.consumed: set[int] = set()  # Zeilenindizes, die durch Multi-Line aufgebraucht wurden

    def record_match(self, pattern_id: str, line_number: int) -> None:
        self.matched_pattern_ids.setdefault(pattern_id, []).append(line_number)

    def add_warning(self, code: str, message: str, severity: str = "warning",
                    affected_lines: Iterable[int] = ()) -> None:
        self.warnings.append(Warning(
            code=code, message=message, severity=severity,
            affected_lines=list(affected_lines),
        ))


def _try_item_patterns(ctx: ParseContext, idx: int) -> ParsedLine | None:
    """Versuche, an Position idx ein Item zu erkennen. Konsumiert ggf. idx+1."""
    line = ctx.raw_lines[idx]
    next_line = ctx.raw_lines[idx + 1] if idx + 1 < len(ctx.raw_lines) else ""

    for pat in ctx.profile.item_patterns:
        m = pat.primary.match(line)
        if not m:
            continue

        # Bei Multi-Line: zweite Zeile prüfen
        if pat.requires_secondary and pat.secondary is not None:
            sm = pat.secondary.match(next_line)
            if not sm:
                continue  # nicht dieses Muster — nächstes versuchen

            ctx.consumed.add(idx + 1)
            ctx.record_match(pat.id, idx)

            groups = {**m.groupdict(), **sm.groupdict()}
            name = _strip_name(groups.get("name", ""), pat.name_post_strip)

            parsed = ParsedLine(
                line_number=len(ctx.lines) + 1,
                raw_text=line + "\n" + next_line,
                raw_text_lines=[line, next_line],
                line_kind="item",
                parsed_name=name,
                parsed_total=_to_decimal(groups["total"]) if "total" in groups else None,
                parsed_tax_class=groups.get("tax_class"),
                parse_confidence=0.95,
                matched_pattern_id=pat.id,
                flags=["multi_line_raw"],
            )

            if pat.kind == "weight_item":
                parsed.parsed_quantity = _to_decimal(groups["weight"])
                parsed.parsed_unit = "kg"
                if "price_per_kg" in groups:
                    parsed.parsed_unit_price = _to_decimal(groups["price_per_kg"])
                parsed.flags.append("weight_item")
            elif pat.kind == "quantity_item":
                parsed.parsed_quantity = Decimal(groups["qty"])
                parsed.parsed_unit = "Stk"
                parsed.parsed_unit_price = _to_decimal(groups["unit_price"])
                parsed.flags.append("quantity_multiline")

            return parsed

        # Single-Line oder optionale Secondary
        ctx.record_match(pat.id, idx)
        groups = m.groupdict()
        name = _strip_name(groups.get("name", ""), pat.name_post_strip)

        parsed = ParsedLine(
            line_number=len(ctx.lines) + 1,
            raw_text=line,
            line_kind="item",
            parsed_name=name,
            parsed_total=_to_decimal(groups["total"]) if "total" in groups else None,
            parsed_tax_class=groups.get("tax_class"),
            parse_confidence=0.92,
            matched_pattern_id=pat.id,
        )

        # Inline-Quantity (Lidl, Knolles): qty + unit_price inline vorhanden?
        if "qty" in groups and "unit_price" in groups:
            parsed.parsed_quantity = Decimal(groups["qty"])
            parsed.parsed_unit = "Stk"
            parsed.parsed_unit_price = _to_decimal(groups["unit_price"])
            parsed.flags.append("quantity_inline")

        return parsed

    return None


def _try_special_patterns(ctx: ParseContext, idx: int,
                          patterns: list, default_kind: str) -> ParsedLine | None:
    """Generische Pattern-Erkennung für Pfand und Discounts."""
    line = ctx.raw_lines[idx]
    next_line = ctx.raw_lines[idx + 1] if idx + 1 < len(ctx.raw_lines) else ""

    for pat in patterns:
        m = pat.regex.match(line)
        if not m:
            continue

        groups = m.groupdict()
        ctx.record_match(pat.id, idx)

        total: Decimal | None = None
        if "total" in groups:
            total = _to_decimal(groups["total"])
        elif "amount" in groups:
            total = _to_decimal(groups["amount"])

        parsed = ParsedLine(
            line_number=len(ctx.lines) + 1,
            raw_text=line,
            line_kind=pat.kind or default_kind,
            parsed_total=total,
            parsed_tax_class=groups.get("tax_class"),
            parsed_name=groups.get("name"),
            parse_confidence=0.92,
            matched_pattern_id=pat.id,
            flags=list(pat.flags),
        )

        if pat.secondary is not None:
            sm = pat.secondary.match(next_line)
            if sm:
                ctx.consumed.add(idx + 1)
                sg = sm.groupdict()
                if "qty" in sg:
                    parsed.parsed_quantity = Decimal(sg["qty"])
                if "unit_amount" in sg:
                    parsed.parsed_unit_price = _to_decimal(sg["unit_amount"])
                parsed.raw_text = line + "\n" + next_line
                parsed.raw_text_lines = [line, next_line]
                parsed.flags.append("multi_line_raw")

        if pat.attach_to == "previous_item":
            for prev in reversed(ctx.lines):
                if prev.line_kind == "item":
                    parsed.parent_line_number = prev.line_number
                    break

        return parsed

    return None


def _try_pfand_patterns(ctx: ParseContext, idx: int) -> ParsedLine | None:
    return _try_special_patterns(ctx, idx, ctx.profile.pfand_patterns, "pfand_einweg")


def _try_discount_patterns(ctx: ParseContext, idx: int) -> ParsedLine | None:
    return _try_special_patterns(ctx, idx, ctx.profile.discount_patterns, "discount")


def _extract_lines(ctx: ParseContext) -> None:
    """Hauptschleife: Item- und Pfand-Erkennung pro Zeile."""
    for idx in range(len(ctx.raw_lines)):
        if idx in ctx.consumed:
            continue

        line = ctx.raw_lines[idx]
        if not line.strip():
            continue

        # Discount-Patterns zuerst (Frischerabatt -> spezifisch, würde sonst von Item missdeutet)
        parsed = _try_discount_patterns(ctx, idx)
        if parsed:
            ctx.lines.append(parsed)
            continue

        # Pfand danach
        parsed = _try_pfand_patterns(ctx, idx)
        if parsed:
            ctx.lines.append(parsed)
            continue

        parsed = _try_item_patterns(ctx, idx)
        if parsed:
            ctx.lines.append(parsed)
            continue


def _extract_datetime(ctx: ParseContext, raw_text: str) -> PurchaseDatetime:
    for ext in ctx.profile.date_extractors:
        # zuerst pro Zeile (für ^/$-Anchored Patterns)
        m = None
        for line in ctx.raw_lines:
            m = ext.regex.search(line)
            if m:
                break
        # Fallback: search auf raw_text (wenn Regex Multiline oder kein Anchor hat)
        if not m:
            m = ext.regex.search(raw_text)
        if not m:
            continue

        groups = m.groupdict()
        date_str = groups.get("date")
        time_str = groups.get("time")

        # Alternative: separate time_regex
        if not time_str and ext.time_regex is not None:
            for line in ctx.raw_lines:
                tm = ext.time_regex.search(line)
                if tm:
                    time_str = tm.group("time")
                    break

        if not date_str:
            continue

        try:
            d = datetime.strptime(date_str, ext.date_format).date()
        except ValueError:
            continue

        t = None
        if time_str and ext.time_format:
            try:
                t = datetime.strptime(time_str, ext.time_format).time()
            except ValueError:
                t = None

        primary = datetime.combine(d, t) if t else None
        return PurchaseDatetime(primary=primary, date_only=d, time_only=t)

    return PurchaseDatetime()


def _extract_store(ctx: ParseContext, raw_text: str) -> Store:
    store = Store()

    if ctx.profile.store_address_regex:
        for line in ctx.raw_lines:
            m = ctx.profile.store_address_regex.match(line)
            if m:
                store.street = m.group("street").strip() if "street" in m.groupdict() else None
                break

    if ctx.profile.store_city_regex:
        for line in ctx.raw_lines:
            m = ctx.profile.store_city_regex.match(line)
            if m:
                g = m.groupdict()
                store.zip = g.get("zip")
                store.city = g.get("city")
                break

    if ctx.profile.store_id_regex:
        for line in ctx.raw_lines:
            m = ctx.profile.store_id_regex.search(line)
            if m:
                g = m.groupdict()
                store.store_id = g.get("store_id") or g.get("store_id_inline")
                if store.store_id:
                    break

    # UID
    uid_match = re.search(r"UID\s*Nr\.?:\s*(DE\d{9})", raw_text)
    if uid_match:
        store.uid_number = uid_match.group(1)

    # Telefon (sehr lose, Best-Effort)
    phone_match = re.search(r"(?:Tel\.\s*)?(\d{4,5}[-\s]?[\d\s/]{5,})", raw_text)
    if phone_match:
        candidate = phone_match.group(1).strip()
        # nur akzeptieren wenn nicht offensichtlich anderes (Bon-Nummer, etc.)
        if len(candidate) <= 20 and "-" in candidate or "/" in candidate:
            store.phone = candidate

    return store


def _extract_totals(ctx: ParseContext, raw_text: str) -> tuple[Totals, Payment]:
    totals = Totals()
    payment = Payment()

    # Pro Zeile iterieren — Patterns nutzen ^/$, brauchen also Zeilen-Match
    for line in ctx.raw_lines:
        if totals.grand_total is None and ctx.profile.grand_total_regex:
            m = ctx.profile.grand_total_regex.match(line)
            if m:
                totals.grand_total = _to_decimal(m.group("amount"))

        if payment.method is None and ctx.profile.payment_regex:
            m = ctx.profile.payment_regex.match(line)
            if m:
                payment.method = m.group("method")
                payment.amount = _to_decimal(m.group("amount"))

        if totals.item_count_declared is None and ctx.profile.item_count_regex:
            m = ctx.profile.item_count_regex.match(line)
            if m:
                totals.item_count_declared = int(m.group("count"))

    totals.item_count_observed = sum(1 for ln in ctx.lines if ln.line_kind == "item")

    # computed_total: Items + Pfand - Discounts/Coupons
    computed = Decimal("0")
    positive_kinds = {"item", "pfand", "pfand_einweg", "pfand_mehrweg", "pfand_aggregate"}
    negative_kinds = {"pfand_return", "discount", "coupon"}
    for ln in ctx.lines:
        if ln.parsed_total is None:
            continue
        if ln.line_kind in positive_kinds:
            computed += ln.parsed_total
        elif ln.line_kind in negative_kinds:
            # pfand_return hat schon negativen Total in parsed_total
            computed += ln.parsed_total if ln.parsed_total < 0 else -ln.parsed_total
    totals.computed_total = computed

    if totals.grand_total is not None and totals.computed_total is not None:
        diff = abs(totals.grand_total - totals.computed_total)
        totals.totals_match = diff <= Decimal("0.02")

    return totals, payment


def _extract_tax_breakdown(ctx: ParseContext) -> list[TaxBreakdownRow]:
    if not ctx.profile.tax_breakdown_row:
        return []

    rows: list[TaxBreakdownRow] = []
    for line in ctx.raw_lines:
        m = ctx.profile.tax_breakdown_row.match(line)
        if not m:
            continue
        g = m.groupdict()
        rate_str = g["rate"].replace(",", ".")
        rows.append(TaxBreakdownRow(
            class_code=g["class"],
            rate=float(rate_str) / 100.0,
            net=_to_decimal(g["net"]),
            tax=_to_decimal(g["tax"]),
            gross=_to_decimal(g["gross"]),
        ))
    return rows


def _extract_loyalty(ctx: ParseContext, raw_text: str) -> Loyalty | None:
    if not ctx.profile.loyalty_program:
        return None

    events: list[LoyaltyEvent] = []
    pats = ctx.profile.loyalty_patterns

    if "earned_cashback" in pats:
        m = pats["earned_cashback"].search(raw_text)
        if m:
            events.append(LoyaltyEvent(
                event_kind="earned_cashback",
                amount_eur=_to_decimal(m.group("amount")),
                raw_text=m.group(0),
            ))

    if "earned_points" in pats:
        m = pats["earned_points"].search(raw_text)
        if m:
            events.append(LoyaltyEvent(
                event_kind="earned_points",
                points=int(m.group("points")),
                raw_text=m.group(0),
            ))

    if "eligible_amount" in pats:
        m = pats["eligible_amount"].search(raw_text)
        if m:
            events.append(LoyaltyEvent(
                event_kind="eligible_amount",
                amount_eur=_to_decimal(m.group("eligible_amount")),
                raw_text=m.group(0),
            ))

    if "coupon" in pats:
        for line in ctx.raw_lines:
            m = pats["coupon"].match(line)
            if m:
                g = m.groupdict()
                events.append(LoyaltyEvent(
                    event_kind="earned_coupon",
                    coupon_target=g.get("target", "").strip() if g.get("target") else None,
                    coupon_value=_to_decimal(g["value"]) if "value" in g else None,
                    raw_text=m.group(0),
                ))

    if "balance" in pats:
        m = pats["balance"].search(raw_text)
        if m:
            events.append(LoyaltyEvent(
                event_kind="balance_info",
                balance_eur=_to_decimal(m.group("balance")),
                raw_text=m.group(0),
            ))

    if "balance_eur" in pats:
        m = pats["balance_eur"].search(raw_text)
        if m:
            events.append(LoyaltyEvent(
                event_kind="balance_info",
                balance_eur=_to_decimal(m.group("balance")),
                raw_text=m.group(0),
            ))

    if "balance_points" in pats:
        m = pats["balance_points"].search(raw_text)
        if m:
            points = int(m.group("points").replace(".", ""))
            # in vorhandenes balance_info-Event integrieren oder neu anlegen
            integrated = False
            for ev in events:
                if ev.event_kind == "balance_info":
                    ev.balance_points = points
                    integrated = True
                    break
            if not integrated:
                events.append(LoyaltyEvent(event_kind="balance_info", balance_points=points,
                                           raw_text=m.group(0)))

    if not events:
        return None

    return Loyalty(program=ctx.profile.loyalty_program, events=events)


def _build_profile_assessment(ctx: ParseContext) -> ProfileAssessment:
    matched = [
        {"pattern_id": pid, "match_count": len(lines),
         "line_numbers_raw": lines}
        for pid, lines in ctx.matched_pattern_ids.items()
    ]

    # uncovered: Zeilen, die nach "EUR"-Header und vor Trennlinie standen,
    # aber von keinem Pattern erfasst wurden. Sehr grobe Heuristik —
    # dient nur als Hinweis, nicht als Wahrheit.
    uncovered: list[dict] = []
    in_item_section = False
    for idx, line in enumerate(ctx.raw_lines):
        stripped = line.strip()
        if not in_item_section:
            if stripped == "EUR":
                in_item_section = True
            continue
        if re.match(r"^-+\s*$", stripped) or "SUMME" in stripped or "Zu zahlen" in stripped \
                or "Posten:" in stripped:
            in_item_section = False
            continue
        if idx in ctx.consumed:
            continue
        # erfasst durch eines unserer Pattern?
        was_matched = any(idx in lines for lines in ctx.matched_pattern_ids.values())
        if not was_matched and stripped:
            uncovered.append({
                "line_number_raw": idx,
                "raw_text": line,
                "guessed_kind": "unknown",
            })

    return ProfileAssessment(
        mode="validated_against_known",
        matched_patterns=matched,
        failed_patterns=[],
        uncovered_lines=uncovered,
    )


def _compute_overall_confidence(result: ParseResult) -> OverallConfidence:
    """Aggregierte Konfidenz aus Einzelteilen."""
    merchant_conf = result.merchant.confidence
    datetime_conf = 1.0 if result.purchase_datetime.primary else (
        0.5 if result.purchase_datetime.date_only else 0.0
    )
    if result.lines:
        item_conf = sum(ln.parse_confidence for ln in result.lines) / len(result.lines)
    else:
        item_conf = 0.0
    totals_conf = 1.0 if result.totals.totals_match else (0.5 if result.totals.grand_total else 0.0)

    overall = (merchant_conf + datetime_conf + item_conf + totals_conf) / 4

    return OverallConfidence(
        merchant_identification=round(merchant_conf, 3),
        datetime_extraction=round(datetime_conf, 3),
        item_parsing=round(item_conf, 3),
        totals_reconciliation=round(totals_conf, 3),
        overall=round(overall, 3),
    )


def parse(raw_text: str, profile: Profile, *,
          merchant_confidence: float = 1.0) -> ParseResult:
    """
    Parst einen Bon-Text mit gegebenem Profil. Profil-Erkennung muss separat
    erfolgt sein (via detector.detect_merchant).
    """
    ctx = ParseContext(profile, raw_text)

    _extract_lines(ctx)
    purchase_dt = _extract_datetime(ctx, raw_text)
    store = _extract_store(ctx, raw_text)
    totals, payment = _extract_totals(ctx, raw_text)
    tax_breakdown = _extract_tax_breakdown(ctx)
    loyalty = _extract_loyalty(ctx, raw_text)
    profile_assessment = _build_profile_assessment(ctx)

    if totals.grand_total is not None and totals.totals_match is False:
        ctx.add_warning(
            "totals_mismatch",
            f"Bon-Summe ({totals.grand_total}) ≠ computed ({totals.computed_total})",
            severity="warning",
        )

    if totals.item_count_declared is not None \
            and totals.item_count_declared != totals.item_count_observed:
        ctx.add_warning(
            "line_count_mismatch",
            f"Bon meldet {totals.item_count_declared} Posten, erkannt: {totals.item_count_observed}",
            severity="warning",
        )

    if not purchase_dt.primary and not purchase_dt.date_only:
        ctx.add_warning("missing_datetime", "Kein Datum auf dem Bon erkannt", severity="warning")

    result = ParseResult(
        status="ok" if not ctx.warnings or all(w.severity != "error" for w in ctx.warnings) else "partial",
        assessment_metadata=AssessmentMetadata(
            parser_engine="profile-regex",
            profile_id=profile.merchant_id,
        ),
        merchant=Merchant(
            identified=True,
            merchant_id=profile.merchant_id,
            name=profile.name,
            country=profile.country,
            confidence=merchant_confidence,
            parent_chain=profile.parent_chain,
        ),
        store=store,
        purchase_datetime=purchase_dt,
        totals=totals,
        tax_breakdown=tax_breakdown,
        payment=payment,
        lines=ctx.lines,
        loyalty=loyalty,
        profile_assessment=profile_assessment,
        warnings=ctx.warnings,
    )

    result.overall_confidence = _compute_overall_confidence(result)

    return result
