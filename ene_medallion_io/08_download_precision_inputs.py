from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ene_minio import add_common_args, connect_from_args, download_file
from precision_contract import DEFAULT_CALIBRATION_STRATEGY, precision_inputs


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Download every input of the ENE precision estimation (final indicator base and "
            "calibrated designs; see precision_contract.py) into <base-dir>."
        )
    )
    add_common_args(parser)
    parser.add_argument("--base-dir", type=Path, default=Path.cwd())
    parser.add_argument("--target-dir", type=Path, default=None,
                        help="Put the indicator base directly in this folder.")
    parser.add_argument("--design-target-dir", type=Path, default=None,
                        help="Put the calibrated designs directly in this folder.")
    parser.add_argument("--calibration-strategy", default=DEFAULT_CALIBRATION_STRATEGY)
    parser.add_argument("--skip-design", action="store_true", help="Download only the indicator base.")
    parser.add_argument("--asof", default=None,
                        help="Version of the indicator base to read under base_indicateurs/asof=<asof>/.")
    args = parser.parse_args()

    base_dir = args.base_dir.resolve()
    items = precision_inputs(
        args.period, quarter=args.quarter, year=args.year,
        strategy=args.calibration_strategy, asof=args.asof, with_design=not args.skip_design,
    )
    client = connect_from_args(args)

    missing: list[str] = []
    for item in items:
        override = args.design_target_dir if "calibration_design" in item.key else args.target_dir
        target = (override / Path(item.local).name) if override else base_dir / item.local
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
