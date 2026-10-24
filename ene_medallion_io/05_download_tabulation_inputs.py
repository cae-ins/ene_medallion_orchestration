from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ene_minio import add_common_args, connect_from_args, download_file
from tabulation_contract import annual_inputs, quarterly_inputs


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Download every input of the ENE tabulation for one quarter or one year "
            "(see tabulation_contract.py) into <base-dir>."
        )
    )
    add_common_args(parser)
    parser.add_argument("--base-dir", type=Path, default=Path.cwd())
    parser.add_argument("--target-dir", type=Path, default=None,
                        help="Put every file directly in this folder instead of the contract locations.")
    parser.add_argument("--pooled-quarter", default=None,
                        help="Annual only: quarter whose pooled base holds the year (default T4_<year>).")
    args = parser.parse_args()

    base_dir = args.base_dir.resolve()
    items = (annual_inputs(args.year, args.pooled_quarter) if args.period == "annual"
             else quarterly_inputs(args.quarter))
    client = connect_from_args(args)

    missing: list[str] = []
    for item in items:
        target = (args.target_dir / Path(item.local).name) if args.target_dir else base_dir / item.local
        if download_file(client, item.bucket, item.key, target,
                         dry_run=args.dry_run, overwrite=args.overwrite) is None and not item.optional:
            missing.append(f"s3://{item.bucket}/{item.key}")
    if missing:
        print(f"\n{len(missing)} entrée(s) obligatoire(s) absente(s) de MinIO :")
        for key in missing:
            print(f"  - {key}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
