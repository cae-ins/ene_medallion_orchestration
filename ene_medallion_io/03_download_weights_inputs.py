from __future__ import annotations

import argparse
from pathlib import Path

from ene_minio import add_common_args, connect_from_args, download_file, download_prefix
from weights_contract import weights_inputs


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Download every input of the ENE weighting pipeline for one quarter "
            "(see weights_contract.py) into <base-dir>/data."
        )
    )
    add_common_args(parser)
    parser.add_argument("--base-dir", type=Path, default=Path.cwd())
    args = parser.parse_args()

    data_dir = args.base_dir.resolve() / "data"
    client = connect_from_args(args)

    missing: list[str] = []
    for item in weights_inputs(args.quarter):
        target = data_dir / item.local
        if item.is_dir:
            records = download_prefix(
                client, item.bucket, item.key, target, dry_run=args.dry_run, overwrite=args.overwrite
            )
            if not records and not item.optional:
                missing.append(f"s3://{item.bucket}/{item.key}/")
        elif download_file(
            client, item.bucket, item.key, target, dry_run=args.dry_run, overwrite=args.overwrite
        ) is None:
            missing.append(f"s3://{item.bucket}/{item.key}")

    if missing:
        print(f"\n{len(missing)} entrée(s) absente(s) de MinIO :")
        for key in missing:
            print(f"  - {key}")


if __name__ == "__main__":
    main()
