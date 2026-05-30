from __future__ import annotations

import argparse
from pathlib import Path

from ene_minio import add_common_args, connect_from_args, download_prefix, period_prefix


def main() -> None:
    parser = argparse.ArgumentParser(description="Download ENE gold indicator-ready bases for tabulations.")
    add_common_args(parser)
    parser.add_argument("--base-dir", type=Path, default=Path.cwd())
    parser.add_argument("--target-dir", type=Path, default=None)
    args = parser.parse_args()

    base_dir = args.base_dir.resolve()
    if args.target_dir:
        target_dir = args.target_dir
    elif args.period == "annual":
        target_dir = base_dir / "Bulletin_Trimestriel" / "Base" / "Base_brute" / "annual" / args.year
    else:
        target_dir = base_dir / "Bulletin_Trimestriel" / "Base" / "Base_brute"

    client = connect_from_args(args)
    download_prefix(
        client,
        "gold",
        f"{period_prefix(args.period, quarter=args.quarter, year=args.year)}/base_indicateurs",
        target_dir,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
