"""
Profile loading and compilation.

Profiles werden aus YAML geladen und alle Regex-Patterns vor dem
Parsen kompiliert (cached). Compile-Fehler werden früh sichtbar.

Variant-Modell (v0.3):
- Ein Variant hat `extends: <parent_merchant_id>` und `applies_to:` mit Bedingungen
- Beim Laden wird das Parent-Dict mit dem Variant-Dict deep-merged (Variant gewinnt)
- Erst dann wird kompiliert — d.h. die Profile-Klasse weiß nichts von Vererbung.
- Selektion des passenden Variants passiert in detector.py auf Basis von `applies_to`
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ItemPattern:
    id: str
    kind: str
    primary: re.Pattern[str]
    secondary: re.Pattern[str] | None
    requires_secondary: bool
    name_post_strip: list[re.Pattern[str]] = field(default_factory=list)


@dataclass
class PfandPattern:
    id: str
    kind: str
    regex: re.Pattern[str]
    secondary: re.Pattern[str] | None
    attach_to: str
    flags: list[str] = field(default_factory=list)


@dataclass
class DateExtractor:
    description: str
    regex: re.Pattern[str]
    date_format: str
    time_format: str | None
    time_regex: re.Pattern[str] | None


@dataclass
class AppliesTo:
    """Conditions under which a variant applies. All are AND-combined."""
    zip_regex: re.Pattern[str] | None = None
    uid_regex: re.Pattern[str] | None = None
    header_marker_regex: re.Pattern[str] | None = None
    store_id_regex: re.Pattern[str] | None = None
    cities: list[str] = field(default_factory=list)
    valid_from: str | None = None
    valid_until: str | None = None

    @property
    def condition_count(self) -> int:
        return sum([
            self.zip_regex is not None,
            self.uid_regex is not None,
            self.header_marker_regex is not None,
            self.store_id_regex is not None,
            len(self.cities) > 0,
            self.valid_from is not None,
            self.valid_until is not None,
        ])


@dataclass
class Profile:
    """Compiled profile, ready for parsing."""
    merchant_id: str
    name: str
    country: str
    parent_chain: str | None
    brand_variants: list[str]

    variant_id: str | None
    extends: str | None
    applies_to: AppliesTo | None

    detection_patterns: list[tuple[re.Pattern[str], float]]
    detection_minimum_score: float

    tax_classes: dict[str, dict[str, Any]]

    item_patterns: list[ItemPattern]
    pfand_patterns: list[PfandPattern]
    discount_patterns: list[PfandPattern]

    date_extractors: list[DateExtractor]
    store_address_regex: re.Pattern[str] | None
    store_city_regex: re.Pattern[str] | None
    store_id_regex: re.Pattern[str] | None

    grand_total_regex: re.Pattern[str] | None
    payment_regex: re.Pattern[str] | None
    item_count_regex: re.Pattern[str] | None

    tax_breakdown_header: re.Pattern[str] | None
    tax_breakdown_row: re.Pattern[str] | None

    loyalty_program: str | None
    loyalty_patterns: dict[str, re.Pattern[str]]

    @property
    def is_variant(self) -> bool:
        return self.extends is not None


class ProfileLoadError(Exception):
    pass


def _compile(pattern: str | None, *, flags: int = 0) -> re.Pattern[str] | None:
    if pattern is None:
        return None
    try:
        return re.compile(pattern, flags)
    except re.error as exc:
        raise ProfileLoadError(f"regex compile failed for {pattern!r}: {exc}") from exc


def _deep_merge(base: dict, overlay: dict) -> dict:
    """
    Deep-merge overlay into base. Overlay wins for scalars and lists,
    dicts are merged recursively.

    Variants ÜBERSCHREIBEN Listen statt sie zu erweitern.
    """
    result = copy.deepcopy(base)
    for key, val in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = copy.deepcopy(val)
    return result


def _parse_applies_to(data: dict | None) -> AppliesTo | None:
    if not data:
        return None
    return AppliesTo(
        zip_regex=_compile(data.get("zip_regex")),
        uid_regex=_compile(data.get("uid_regex")),
        header_marker_regex=_compile(data.get("header_marker_regex") or data.get("header_marker")),
        store_id_regex=_compile(data.get("store_id_regex")),
        cities=data.get("cities", []),
        valid_from=data.get("valid_from"),
        valid_until=data.get("valid_until"),
    )


def _compile_profile_from_dict(data: dict[str, Any]) -> Profile:
    if data.get("schema_version") not in (1, "1"):
        raise ProfileLoadError(f"unsupported schema_version: {data.get('schema_version')}")

    merchant = data["merchant"]

    detection_patterns: list[tuple[re.Pattern[str], float]] = []
    for entry in data.get("detection", {}).get("header_patterns", []):
        detection_patterns.append((
            _compile(entry["regex"]),
            float(entry.get("confidence", 0.5)),
        ))

    item_patterns: list[ItemPattern] = []
    for entry in data.get("item_patterns", []):
        item_patterns.append(ItemPattern(
            id=entry["id"],
            kind=entry["kind"],
            primary=_compile(entry["primary"]),
            secondary=_compile(entry.get("secondary")),
            requires_secondary=bool(entry.get("requires_secondary", False)),
            name_post_strip=[_compile(p) for p in entry.get("name_post_strip", [])],
        ))

    pfand_patterns: list[PfandPattern] = []
    for entry in data.get("pfand_patterns", []):
        pfand_patterns.append(PfandPattern(
            id=entry["id"],
            kind=entry.get("kind", "pfand_einweg"),
            regex=_compile(entry["regex"]),
            secondary=_compile(entry.get("secondary")),
            attach_to=entry.get("attach_to", "previous_item"),
            flags=entry.get("flags", []),
        ))

    discount_patterns: list[PfandPattern] = []
    for entry in data.get("discount_patterns", []):
        discount_patterns.append(PfandPattern(
            id=entry["id"],
            kind=entry.get("kind", "discount"),
            regex=_compile(entry["regex"]),
            secondary=_compile(entry.get("secondary")),
            attach_to=entry.get("attach_to", "previous_item"),
            flags=entry.get("flags", []),
        ))

    date_extractors: list[DateExtractor] = []
    for entry in data.get("date_extraction", []):
        date_extractors.append(DateExtractor(
            description=entry.get("description", ""),
            regex=_compile(entry["regex"]),
            date_format=entry["date_format"],
            time_format=entry.get("time_format"),
            time_regex=_compile(entry.get("time_regex")),
        ))

    store = data.get("store_extraction", {})

    def _store_re(key: str) -> re.Pattern[str] | None:
        sub = store.get(key)
        if not sub:
            return None
        return _compile(sub.get("regex"))

    totals = data.get("totals", {})
    tax_bd = data.get("tax_breakdown", {})
    loyalty = data.get("loyalty", {})

    return Profile(
        merchant_id=merchant["id"],
        name=merchant["name"],
        country=merchant["country"],
        parent_chain=merchant.get("parent_chain"),
        brand_variants=merchant.get("brand_variants", []),
        variant_id=data.get("variant_id"),
        extends=data.get("extends"),
        applies_to=_parse_applies_to(data.get("applies_to")),
        detection_patterns=detection_patterns,
        detection_minimum_score=float(data.get("detection", {}).get("minimum_score", 0.7)),
        tax_classes=data.get("tax_classes", {}),
        item_patterns=item_patterns,
        pfand_patterns=pfand_patterns,
        discount_patterns=discount_patterns,
        date_extractors=date_extractors,
        store_address_regex=_store_re("address_line"),
        store_city_regex=_store_re("city_line"),
        store_id_regex=_store_re("store_id"),
        grand_total_regex=_compile(totals.get("grand_total")),
        payment_regex=_compile(totals.get("payment")),
        item_count_regex=_compile(totals.get("item_count")),
        tax_breakdown_header=_compile(tax_bd.get("table_header")),
        tax_breakdown_row=_compile(tax_bd.get("row_regex")),
        loyalty_program=loyalty.get("program"),
        loyalty_patterns={
            k: _compile(v)
            for k, v in loyalty.items()
            if k != "program" and isinstance(v, str)
        },
    )


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ProfileLoadError(f"profile not found: {path}")
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_profile(path: Path | str) -> Profile:
    """Load and compile a single profile from YAML (no variant resolution)."""
    return _compile_profile_from_dict(_load_yaml(Path(path)))


@dataclass
class ProfileBundle:
    """A base profile plus all variants that extend it."""
    base: Profile
    variants: list[Profile] = field(default_factory=list)


def load_all_profiles(profiles_dir: Path | str) -> dict[str, ProfileBundle]:
    """
    Load all base profiles AND their variants from <profiles_dir>.

    Layout:
        <profiles_dir>/<country>/<merchant>/profile.yaml         → base
        <profiles_dir>/<country>/<merchant>/variants/<name>.yaml → variants
    """
    profiles_dir = Path(profiles_dir)

    bases: dict[str, dict[str, Any]] = {}
    bases_path: dict[str, Path] = {}
    for profile_path in profiles_dir.rglob("profile.yaml"):
        data = _load_yaml(profile_path)
        if "extends" in data:
            continue
        merchant_id = data["merchant"]["id"]
        bases[merchant_id] = data
        bases_path[merchant_id] = profile_path

    bundles: dict[str, ProfileBundle] = {}
    for merchant_id, base_data in bases.items():
        base_profile = _compile_profile_from_dict(base_data)
        bundle = ProfileBundle(base=base_profile)

        base_dir = bases_path[merchant_id].parent
        variants_dir = base_dir / "variants"
        if variants_dir.is_dir():
            for variant_path in sorted(variants_dir.glob("*.yaml")):
                variant_data = _load_yaml(variant_path)
                if variant_data.get("extends") != merchant_id:
                    raise ProfileLoadError(
                        f"{variant_path}: extends '{variant_data.get('extends')}' "
                        f"but is located under '{merchant_id}'"
                    )
                merged = _deep_merge(base_data, variant_data)
                variant_profile = _compile_profile_from_dict(merged)
                bundle.variants.append(variant_profile)

        bundles[merchant_id] = bundle

    return bundles


def get_all_profiles_flat(bundles: dict[str, ProfileBundle]) -> dict[str, Profile]:
    """
    Flatten bundles back to merchant_id → base Profile for backwards-compatible callers.
    Variants are NOT included here — use select_profile() for variant resolution.
    """
    return {mid: bundle.base for mid, bundle in bundles.items()}
