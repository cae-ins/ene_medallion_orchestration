from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from apurement_contract import (
    QUALITY_REPORT_GLOBS,
    QUALITY_REPORTS_DIR,
    QUARTER_MARKER,
    apurement_products,
    quality_reports_prefix,
)
from ene_minio import (
    add_common_args,
    connect_from_args,
    ensure_ene_layout,
    timestamp_id,
    upload_directory,
    upload_file,
)


def code_version(base_dir: Path) -> str | None:
    """Commit of the apurement repository that produced the outputs (traceability)."""
    try:
        return subprocess.run(
            ["git", "-C", str(base_dir), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Publish the apurement products of one quarter to silver (explicit list in "
            "apurement_contract.apurement_products; nothing else is sent)."
        )
    )
    add_common_args(parser)
    parser.add_argument("--base-dir", type=Path, default=Path.cwd())
    parser.add_argument(
        "--with-quality-reports",
        action="store_true",
        help="Also publish the Excel anomaly reports of document/ to silver/.../quality_reports/.",
    )
    parser.add_argument(
        "--skip-quarter-check",
        action="store_true",
        help=f"Publish even if {QUARTER_MARKER} is missing (outputs produced before the marker existed).",
    )
    args = parser.parse_args()

    base_dir = args.base_dir.resolve()
    products = apurement_products(args.quarter)

    # The Stata run writes the quarter it processed into dataout/ right after emptying it:
    # never publish the outputs of another quarter under this quarter's keys.
    marker = base_dir / QUARTER_MARKER
    produced = marker.read_text(encoding="utf-8").strip() if marker.is_file() else None
    if produced != args.quarter and not (produced is None and args.skip_quarter_check):
        print(
            f"Refus : {QUARTER_MARKER} indique {produced or 'absent'}, trimestre demandé {args.quarter}. "
            "Relancer l'apurement pour ce trimestre (ou --skip-quarter-check si le marqueur est absent "
            "et que les sorties sont bien celles de ce trimestre)."
        )
        return 1

    # Output contract: every product must exist and be non-empty before any upload.
    invalid = [
        item.local for item in products
        if not (base_dir / item.local).is_file() or (base_dir / item.local).stat().st_size == 0
    ]
    if invalid:
        print("Contrat de sortie de l'apurement non respecté (fichiers absents ou vides) :")
        for path in invalid:
            print(f"  - {path}")
        return 1
    print(f"apurement output contract validation: OK ({len(products)} files)")

    client = connect_from_args(args)
    ensure_ene_layout(client, args.quarter, dry_run=args.dry_run)

    records = [
        upload_file(
            client, base_dir / item.local, item.bucket, item.key,
            dry_run=args.dry_run, overwrite=args.overwrite,
        )
        for item in products
    ]
    if args.with_quality_reports:
        upload_directory(
            client,
            base_dir / QUALITY_REPORTS_DIR,
            "silver",
            quality_reports_prefix(args.quarter),
            dry_run=args.dry_run,
            overwrite=args.overwrite,
            ignore_dir_names={"codification"},
            include_globs=QUALITY_REPORT_GLOBS,
        )

    manifest_key = f"enem/{args.quarter}/_manifests/apurement_{timestamp_id()}.json"
    if args.dry_run:
        print(f"DRY-RUN put s3://silver/{manifest_key}")
        return 0
    body = json.dumps(
        {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "quarter": args.quarter,
            "code_version": code_version(base_dir),
            "files": [record for record in records if record],
        },
        indent=2,
    ).encode("utf-8")
    client.put_object(Bucket="silver", Key=manifest_key, Body=body)
    print(f"uploaded manifest -> s3://silver/{manifest_key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
