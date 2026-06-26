from __future__ import annotations

import argparse
from pathlib import Path

from ene_minio import (
    add_common_args,
    connect_from_args,
    ensure_ene_period_layout,
    period_label,
    period_prefix,
    upload_directory,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload ENE prepared per-quarter work base(s) to gold/base_indicateurs "
        "(partition immuable par trimestre, versionnable via --asof)."
    )
    add_common_args(parser)
    parser.add_argument("--base-dir", type=Path, default=Path.cwd())
    parser.add_argument(
        "--asof",
        default=None,
        help="Sous-dossier de version (ex. 2026-06-26) -> base_indicateurs/asof=<asof>/. "
        "Sans --asof : ecriture directe (immuable, protegee par --overwrite).",
    )
    args = parser.parse_args()

    base_dir = args.base_dir.resolve()
    label = period_label(args.period, quarter=args.quarter, year=args.year)
    root = period_prefix(args.period, quarter=args.quarter, year=args.year)

    if args.period == "annual":
        work_dir = base_dir / "data" / "work" / "annual" / label
    else:
        work_dir = base_dir / "data" / "work" / "quarterly" / label

    client = connect_from_args(args)
    ensure_ene_period_layout(
        client,
        args.period,
        quarter=args.quarter,
        year=args.year,
        dry_run=args.dry_run,
    )

    suffix = f"/asof={args.asof}" if args.asof else ""
    dest = f"{root}/base_indicateurs{suffix}"

    upload_directory(
        client,
        work_dir,
        "gold",
        dest,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
        ignore_name_contains={"copie", "copy", "temp", "tmp", "~"},
    )


if __name__ == "__main__":
    main()
