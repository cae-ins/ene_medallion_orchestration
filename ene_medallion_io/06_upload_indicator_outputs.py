from __future__ import annotations

import argparse
from pathlib import Path

from ene_minio import (
    GOLD_INDICATORS,
    add_common_args,
    connect_from_args,
    ensure_ene_period_layout,
    period_label,
    period_prefix,
    upload_directory,
)
from tabulation_contract import indicator_products


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Upload the ENE tabulation products to gold/.../indicateurs/: only the files "
            "listed by tabulation_contract.indicator_products (diagnostics, logs, drafts "
            "and copies stay local)."
        )
    )
    add_common_args(parser)
    parser.add_argument("--base-dir", type=Path, default=Path.cwd())
    parser.add_argument("--results-dir", type=Path, default=None)
    # Kept for compatibility with older launchers: publication follows the product list.
    for obsolete in ("--include-archives", "--include-templates", "--include-graphs", "--include-drafts"):
        parser.add_argument(obsolete, action="store_true", help="obsolète : sans effet")
    args = parser.parse_args()
    if any((args.include_archives, args.include_templates, args.include_graphs, args.include_drafts)):
        print("note : les options --include-* sont sans effet, seuls les produits listés sont publiés")

    base_dir = args.base_dir.resolve()
    label = period_label(args.period, quarter=args.quarter, year=args.year)
    results_dir = args.results_dir or (
        base_dir / "outputs" / ("annual" if args.period == "annual" else "quarterly") / label
    )

    client = connect_from_args(args)
    ensure_ene_period_layout(client, args.period, quarter=args.quarter, year=args.year, dry_run=args.dry_run)
    upload_directory(
        client,
        results_dir,
        "gold",
        f"{period_prefix(args.period, quarter=args.quarter, year=args.year)}/{GOLD_INDICATORS}",
        dry_run=args.dry_run,
        overwrite=args.overwrite,
        include_globs=indicator_products(args.period, label),
    )


if __name__ == "__main__":
    main()
