"""
CLI: `forager-parser parse <bon.txt> [--profile <id>] [--verify-with-claude]`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from .detector import detect_merchant
from .parser import parse
from .profile import load_all_profiles, load_profile
from .verifier import verify_with_claude

DEFAULT_PROFILES_DIR = Path(__file__).parent.parent.parent / "profiles"


@click.group()
def cli() -> None:
    """Forager Parser CLI."""


@cli.command("parse")
@click.argument("bon_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--profile", "profile_id",
              help="merchant_id wie 'de.rewe', oder variant_id wie 'de.rewe.ohg-piclum'. "
                   "Wenn weggelassen: Auto-Detection.")
@click.option("--profiles-dir", type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=DEFAULT_PROFILES_DIR)
@click.option("--verify-with-claude/--no-verify", default=False,
              help="Vergleich mit Claude (braucht ANTHROPIC_API_KEY).")
@click.option("--output", "-o", type=click.Path(dir_okay=False, path_type=Path),
              help="JSON-Output in Datei statt stdout.")
def parse_cmd(bon_file: Path, profile_id: str | None, profiles_dir: Path,
              verify_with_claude: bool, output: Path | None) -> None:
    """Parst einen Bon und gibt das Ergebnis als JSON aus."""

    raw_text = bon_file.read_text(encoding="utf-8")

    bundles = load_all_profiles(profiles_dir)
    if not bundles:
        click.echo(f"Fehler: keine Profile gefunden unter {profiles_dir}", err=True)
        sys.exit(2)

    if profile_id:
        # Profile id may be a base merchant_id or a variant_id
        profile = None
        for mid, bundle in bundles.items():
            if mid == profile_id:
                profile = bundle.base
                break
            for variant in bundle.variants:
                if variant.variant_id == profile_id:
                    profile = variant
                    break
            if profile:
                break
        if not profile:
            all_ids = []
            for mid, b in bundles.items():
                all_ids.append(mid)
                all_ids.extend(v.variant_id for v in b.variants if v.variant_id)
            click.echo(f"Fehler: Profil '{profile_id}' nicht gefunden. "
                       f"Verfügbar: {sorted(all_ids)}", err=True)
            sys.exit(2)
        merchant_conf = 1.0
    else:
        detection = detect_merchant(raw_text, bundles)
        if not detection.profile:
            click.echo("Fehler: kein passendes Profil gefunden.", err=True)
            click.echo("Kandidaten (Score):", err=True)
            for mid, score in detection.candidates[:5]:
                click.echo(f"  {mid}: {score:.2f}", err=True)
            sys.exit(2)
        profile = detection.profile
        merchant_conf = min(detection.score, 1.0)
        if profile.is_variant:
            click.echo(f"Erkanntes Profil: {profile.merchant_id} "
                       f"(Variant: {profile.variant_id}, Score: {detection.score:.2f}, "
                       f"Variant-Conditions matched: {detection.variant_match_count})",
                       err=True)
        else:
            click.echo(f"Erkanntes Profil: {profile.merchant_id} "
                       f"(Score: {detection.score:.2f})", err=True)

    result = parse(raw_text, profile, merchant_confidence=merchant_conf)

    if verify_with_claude:
        verification = verify_with_claude_runner(raw_text, result)
        result_dict = result.to_dict()
        result_dict["claude_verification"] = verification.__dict__
    else:
        result_dict = result.to_dict()

    out_json = json.dumps(result_dict, indent=2, ensure_ascii=False, default=str)

    if output:
        output.write_text(out_json, encoding="utf-8")
        click.echo(f"Geschrieben: {output}", err=True)
    else:
        click.echo(out_json)


def verify_with_claude_runner(raw_text: str, parser_result):
    return verify_with_claude(raw_text, parser_result.to_dict())


@cli.command("detect")
@click.argument("bon_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--profiles-dir", type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=DEFAULT_PROFILES_DIR)
def detect_cmd(bon_file: Path, profiles_dir: Path) -> None:
    """Nur Händler-Detection, kein Parsing."""
    raw_text = bon_file.read_text(encoding="utf-8")
    bundles = load_all_profiles(profiles_dir)
    detection = detect_merchant(raw_text, bundles)

    if detection.profile:
        if detection.profile.is_variant:
            click.echo(f"Top-Kandidat: {detection.profile.merchant_id} "
                       f"(Variant: {detection.profile.variant_id})")
            click.echo(f"Variant-Conditions matched: {detection.variant_match_count}")
        else:
            click.echo(f"Top-Kandidat: {detection.profile.merchant_id}")
    else:
        click.echo("Top-Kandidat: KEINER")

    click.echo(f"Score: {detection.score:.2f}")
    click.echo("Alle Kandidaten:")
    for mid, score in detection.candidates:
        marker = "✓" if detection.profile and mid == detection.profile.merchant_id else " "
        click.echo(f"  {marker} {mid:<30} {score:.2f}")


@cli.command("list-profiles")
@click.option("--profiles-dir", type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=DEFAULT_PROFILES_DIR)
def list_profiles_cmd(profiles_dir: Path) -> None:
    """Listet alle ladbaren Profile auf — Bases und Variants."""
    bundles = load_all_profiles(profiles_dir)
    for mid in sorted(bundles.keys()):
        bundle = bundles[mid]
        p = bundle.base
        click.echo(f"{mid:<30}  {p.name}  ({p.country})"
                   f"  parent={p.parent_chain or '-'}"
                   f"  items={len(p.item_patterns)}  pfand={len(p.pfand_patterns)}"
                   f"  variants={len(bundle.variants)}")
        for v in bundle.variants:
            applies = v.applies_to
            cond_summary = []
            if applies:
                if applies.uid_regex:
                    cond_summary.append(f"uid={applies.uid_regex.pattern}")
                if applies.zip_regex:
                    cond_summary.append(f"zip={applies.zip_regex.pattern}")
                if applies.header_marker_regex:
                    cond_summary.append(f"header={applies.header_marker_regex.pattern}")
                if applies.cities:
                    cond_summary.append(f"cities={applies.cities}")
            click.echo(f"    ↳ {v.variant_id}  applies_to: {', '.join(cond_summary) or '(none)'}")


if __name__ == "__main__":
    cli()
