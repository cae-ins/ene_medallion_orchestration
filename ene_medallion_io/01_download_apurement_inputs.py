from __future__ import annotations

import argparse
import sys
from pathlib import Path

from apurement_contract import apurement_inputs
from ene_minio import add_common_args, connect_from_args, download_file, download_prefix


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Download every input of the ENE apurement for one quarter "
            "(see apurement_contract.py) into <base-dir>."
        )
    )
    add_common_args(parser)
    parser.add_argument("--base-dir", type=Path, default=Path.cwd())
    args = parser.parse_args()

    base_dir = args.base_dir.resolve()
    client = connect_from_args(args)

    missing: list[str] = []
    for item in apurement_inputs(args.quarter):
        target = base_dir / item.local
        if item.is_dir:
            records = download_prefix(
                client, item.bucket, item.key, target, dry_run=args.dry_run, overwrite=args.overwrite
            )
            if not records and not item.optional:
                missing.append(f"s3://{item.bucket}/{item.key}/")
        elif download_file(
            client, item.bucket, item.key, target, dry_run=args.dry_run, overwrite=args.overwrite
        ) is None and not item.optional:
            missing.append(f"s3://{item.bucket}/{item.key}")

    if missing:
        print(f"\n{len(missing)} entrée(s) obligatoire(s) absente(s) de MinIO :")
        for key in missing:
            print(f"  - {key}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
