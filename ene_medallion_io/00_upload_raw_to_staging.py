from __future__ import annotations

import argparse
import sys
from pathlib import Path

from apurement_contract import apurement_inputs
from ene_minio import add_common_args, connect_from_args, ensure_ene_layout, upload_directory, upload_file


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Publish the inputs owned by the apurement stage to staging (see "
            "apurement_contract.py): the immutable Survey Solutions snapshot "
            "(datain/staging) and the codification workbooks (document/codification). "
            "Existing objects are kept unless --overwrite."
        )
    )
    add_common_args(parser)
    parser.add_argument("--base-dir", type=Path, default=Path.cwd())
    parser.add_argument("--skip-codification", action="store_true")
    args = parser.parse_args()

    base_dir = args.base_dir.resolve()
    client = connect_from_args(args)
    ensure_ene_layout(client, args.quarter, dry_run=args.dry_run)

    missing: list[str] = []
    for item in apurement_inputs(args.quarter):
        source = base_dir / item.local
        if item.is_dir:
            if args.skip_codification:
                continue
            records = upload_directory(
                client, source, item.bucket, item.key, dry_run=args.dry_run, overwrite=args.overwrite
            )
            if not records and not item.optional:
                missing.append(f"{item.local}/")
        elif upload_file(
            client, source, item.bucket, item.key, dry_run=args.dry_run, overwrite=args.overwrite
        ) is None and not item.optional:
            missing.append(item.local)

    if missing:
        print(f"\n{len(missing)} fichier(s) local(aux) obligatoire(s) absent(s) :")
        for path in missing:
            print(f"  - {path}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
