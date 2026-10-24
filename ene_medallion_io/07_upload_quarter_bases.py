from __future__ import annotations

import argparse
from pathlib import Path

from ene_minio import (
    GOLD_INDICATOR_BASE,
    add_common_args,
    connect_from_args,
    ensure_ene_period_layout,
    period_label,
    period_prefix,
    upload_directory,
)
from tabulation_contract import base_products


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            f"Upload the ENE work bases to gold/{GOLD_INDICATOR_BASE}: only the products of "
            "tabulation_contract.base_products (Traite_<AATq>.dta and the pooled base for a "
            "quarter; the annual precision base). Versionable with --asof."
        )
    )
    add_common_args(parser)
    parser.add_argument("--base-dir", type=Path, default=Path.cwd())
    parser.add_argument(
        "--asof",
        default=None,
        help=(
            f"Sous-dossier de version (ex. 2026-06-26) -> {GOLD_INDICATOR_BASE}/asof=<asof>/. "
            "Sans --asof : écriture directe (immuable, protégée par --overwrite)."
        ),
    )
    args = parser.parse_args()

    base_dir = args.base_dir.resolve()
    label = period_label(args.period, quarter=args.quarter, year=args.year)
    root = period_prefix(args.period, quarter=args.quarter, year=args.year)
    work_dir = base_dir / "data" / "work" / ("annual" if args.period == "annual" else "quarterly") / label

    client = connect_from_args(args)
    ensure_ene_period_layout(client, args.period, quarter=args.quarter, year=args.year, dry_run=args.dry_run)
    suffix = f"/asof={args.asof}" if args.asof else ""
    upload_directory(
        client,
        work_dir,
        "gold",
        f"{root}/{GOLD_INDICATOR_BASE}{suffix}",
        dry_run=args.dry_run,
        overwrite=args.overwrite,
        include_globs=base_products(args.period, label),
    )


if __name__ == "__main__":
    main()
