from __future__ import annotations

import argparse
from pathlib import Path

from ene_minio import (
    GOLD_INDICATORS,
    add_common_args,
    connect_from_args,
    ensure_ene_period_layout,
    period_prefix,
    upload_directory,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload ENE tabulation outputs to gold indicators.")
    add_common_args(parser)
    parser.add_argument("--base-dir", type=Path, default=Path.cwd())
    parser.add_argument("--results-dir", type=Path, default=None)
    parser.add_argument("--include-archives", action="store_true")
    parser.add_argument("--include-templates", action="store_true")
    parser.add_argument("--include-graphs", action="store_true")
    parser.add_argument("--include-drafts", action="store_true")
    args = parser.parse_args()

    base_dir = args.base_dir.resolve()
    if args.results_dir:
        results_dir = args.results_dir
    elif args.period == "annual":
        results_dir = base_dir / "outputs" / "annual" / args.year
    else:
        results_dir = base_dir / "outputs" / "quarterly" / args.quarter

    client = connect_from_args(args)
    ensure_ene_period_layout(
        client,
        args.period,
        quarter=args.quarter,
        year=args.year,
        dry_run=args.dry_run,
    )

    ignored_dirs = set()
    if not args.include_archives:
        ignored_dirs.add("Archive")
    if not args.include_templates:
        ignored_dirs.add("Templates")
    if not args.include_graphs:
        ignored_dirs.add("graphs")

    ignored_name_fragments = set()
    if not args.include_templates:
        ignored_name_fragments.add("template")
    if not args.include_drafts:
        ignored_name_fragments.update({"copie", "copy", "test", "2024"})
    upload_directory(
        client,
        results_dir,
        "gold",
        f"{period_prefix(args.period, quarter=args.quarter, year=args.year)}/{GOLD_INDICATORS}",
        dry_run=args.dry_run,
        overwrite=args.overwrite,
        ignore_dir_names=ignored_dirs,
        ignore_name_contains=ignored_name_fragments,
    )


if __name__ == "__main__":
    main()
