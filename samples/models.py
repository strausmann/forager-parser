"""
Datenmodelle für Forager Parser.

Diese Modelle entsprechen einer kompakten Teilmenge des Forager Receipt
Assessment Schema v1. Der Prototyp fokussiert auf parse-relevante Felder;
Drift-Detection und Profile-Proposals werden separat ausgegeben.
"""
from __future__ import annotations

from datetime import date as Date
from datetime import time as Time
from datetime import datetime as DateTime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Merchant(BaseModel):
    identified: bool
    merchant_id: str | None = None
    name: str | None = None
    country: str | None = None
    confidence: float = 0.0
    parent_chain: str | None = None


class Store(BaseModel):
    street: str | None = None
    zip: str | None = None
    city: str | None = None
    phone: str | None = None
    store_id: str | None = None
    uid_number: str | None = None


class PurchaseDatetime(BaseModel):
    primary: DateTime | None = None
    date_only: Date | None = None
    time_only: Time | None = None


class TaxBreakdownRow(BaseModel):
    class_code: str
    rate: float
    net: Decimal
    tax: Decimal
    gross: Decimal


class Totals(BaseModel):
    grand_total: Decimal | None = None
    currency: str = "EUR"
    computed_total: Decimal | None = None
    totals_match: bool | None = None
    item_count_declared: int | None = None
    item_count_observed: int = 0


class Payment(BaseModel):
    method: str | None = None
    amount: Decimal | None = None


class ParsedLine(BaseModel):
    """Eine Position auf dem Bon."""
    model_config = ConfigDict(populate_by_name=True)

    line_number: int
    raw_text: str
    raw_text_lines: list[str] | None = None
    line_kind: str  # item|pfand|pfand_aggregate|pfand_return|discount|coupon|loyalty_info|unknown
    parsed_name: str | None = None
    parsed_quantity: Decimal | None = None
    parsed_unit: str | None = None
    parsed_unit_price: Decimal | None = None
    parsed_total: Decimal | None = None
    parsed_tax_class: str | None = None
    parse_confidence: float = 0.0
    parent_line_number: int | None = None
    flags: list[str] = Field(default_factory=list)
    matched_pattern_id: str | None = None


class LoyaltyEvent(BaseModel):
    event_kind: str
    points: int | None = None
    amount_eur: Decimal | None = None
    coupon_target: str | None = None
    coupon_value: Decimal | None = None
    balance_points: int | None = None
    balance_eur: Decimal | None = None
    raw_text: str | None = None


class Loyalty(BaseModel):
    program: str
    events: list[LoyaltyEvent] = Field(default_factory=list)


class ProfileAssessment(BaseModel):
    mode: str  # validated_against_known | no_profile_available
    matched_patterns: list[dict[str, Any]] = Field(default_factory=list)
    failed_patterns: list[dict[str, Any]] = Field(default_factory=list)
    uncovered_lines: list[dict[str, Any]] = Field(default_factory=list)


class Warning(BaseModel):
    code: str
    message: str
    severity: str = "warning"  # info|warning|error
    affected_lines: list[int] = Field(default_factory=list)


class OverallConfidence(BaseModel):
    merchant_identification: float = 0.0
    datetime_extraction: float = 0.0
    item_parsing: float = 0.0
    totals_reconciliation: float = 0.0
    overall: float = 0.0


class AssessmentMetadata(BaseModel):
    assessor_version: str = "0.1.0-prototype"
    prompt_version: str | None = None
    model: str | None = None
    parser_engine: str = "profile-regex"
    profile_id: str | None = None


class ParseResult(BaseModel):
    """Top-Level-Output eines Parser-Laufs — kompakte Schema-v1-Variante."""
    schema_version: str = "1"
    status: str = "ok"
    failure_reason: str | None = None
    assessment_metadata: AssessmentMetadata = Field(default_factory=AssessmentMetadata)
    merchant: Merchant
    store: Store = Field(default_factory=Store)
    purchase_datetime: PurchaseDatetime = Field(default_factory=PurchaseDatetime)
    totals: Totals = Field(default_factory=Totals)
    tax_breakdown: list[TaxBreakdownRow] = Field(default_factory=list)
    payment: Payment = Field(default_factory=Payment)
    lines: list[ParsedLine] = Field(default_factory=list)
    loyalty: Loyalty | None = None
    profile_assessment: ProfileAssessment | None = None
    warnings: list[Warning] = Field(default_factory=list)
    overall_confidence: OverallConfidence = Field(default_factory=OverallConfidence)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=False)
