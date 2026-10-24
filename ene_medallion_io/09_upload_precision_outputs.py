from __future__ import annotations

import argparse
import json
from pathlib import Path

from ene_minio import (
    GOLD_PRECISION,
    add_common_args,
    connect_from_args,
    ensure_ene_period_layout,
    period_prefix,
    upload_file,
)
from precision_contract import precision_outputs
from precision_contract import results_dir as precision_results_dir


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload ENE precision estimates to gold/precision."
    )
    add_common_args(parser)
    parser.add_argument("--base-dir", type=Path, default=Path.cwd())
    parser.add_argument("--results-dir", type=Path, default=None)
    parser.add_argument(
        "--asof",
        default=None,
        help="Optional immutable output version written under precision/asof=<asof>/.",
    )
    args = parser.parse_args()

    base_dir = args.base_dir.resolve()
    if args.results_dir:
        results_dir = args.results_dir
    elif args.period == "annual":
        results_dir = base_dir / "output" / "annual" / args.year
    else:
        results_dir = base_dir / "output" / "quarterly" / args.quarter

    client = connect_from_args(args)
    ensure_ene_period_layout(
        client,
        args.period,
        quarter=args.quarter,
        year=args.year,
        dry_run=args.dry_run,
    )

    root = period_prefix(args.period, quarter=args.quarter, year=args.year)
    suffix = f"/asof={args.asof}" if args.asof else ""
    period_label = args.year if args.period == "annual" else args.quarter
    manifest_path = results_dir / f"manifest_{period_label}.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Precision manifest not found: {manifest_path}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    # Only the products listed by precision_contract.PUBLISHED_MANIFEST_FIELDS are published.
    declared_files = [
        Path(item.local).relative_to(precision_results_dir(args.period, period_label)).as_posix()
        for item in precision_outputs(args.period, period_label, manifest, args.asof)
    ]

    missing_files = [
        relative for relative in declared_files
        if not (results_dir / Path(relative)).is_file()
    ]
    if missing_files:
        raise FileNotFoundError(
            "Files declared by precision manifest are missing: "
            + ", ".join(missing_files)
        )

    destination = f"{root}/{GOLD_PRECISION}{suffix}"
    for relative in dict.fromkeys(declared_files):
        upload_file(
            client,
            results_dir / Path(relative),
            "gold",
            f"{destination}/{Path(relative).as_posix()}",
            dry_run=args.dry_run,
            overwrite=args.overwrite,
        )


if __name__ == "__main__":
    main()
