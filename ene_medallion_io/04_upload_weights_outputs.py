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
    upload_file,
)


def annual_lfs_weight_file(weights_dir: Path, year: str) -> Path | None:
    expected_name = f"LFS_WEIGHTS_{year}.dta"
    direct_candidates = [
        weights_dir / expected_name,
        weights_dir / "calibrated_weights" / expected_name,
    ]
    for candidate in direct_candidates:
        if candidate.exists():
            return candidate

    matches = sorted(
        path
        for path in weights_dir.rglob(expected_name)
        if path.is_file()
        and "copie" not in path.name.lower()
        and "copy" not in path.name.lower()
    )
    return matches[0] if matches else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload ENE weights outputs to silver/gold.")
    add_common_args(parser)
    parser.add_argument("--base-dir", type=Path, default=Path.cwd())
    args = parser.parse_args()

    base_dir = args.base_dir.resolve()
    client = connect_from_args(args)
    ensure_ene_period_layout(
        client,
        args.period,
        quarter=args.quarter,
        year=args.year,
        dry_run=args.dry_run,
    )

    label = period_label(args.period, quarter=args.quarter, year=args.year)
    root = period_prefix(args.period, quarter=args.quarter, year=args.year)
    weights_dir = base_dir / "data" / "04_weights" / label

    if args.period == "annual":
        annual_file = annual_lfs_weight_file(weights_dir, args.year)
        if annual_file is None:
            print(f"skip annual weights upload: no LFS_WEIGHTS_{args.year}.dta found under {weights_dir}")
            return
        key_name = annual_file.name
        upload_file(
            client,
            annual_file,
            "silver",
            f"{root}/poids/{key_name}",
            dry_run=args.dry_run,
            overwrite=args.overwrite,
        )
        upload_file(
            client,
            annual_file,
            "gold",
            f"{root}/base_indicateurs/{key_name}",
            dry_run=args.dry_run,
            overwrite=args.overwrite,
        )
        return

    upload_directory(
        client,
        weights_dir,
        "silver",
        f"{root}/poids",
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )

    upload_directory(
        client,
        weights_dir / "calibrated_weights",
        "gold",
        f"{root}/base_indicateurs",
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )
    upload_directory(
        client,
        weights_dir / "base_weights",
        "gold",
        f"{root}/base_indicateurs",
        dry_run=args.dry_run,
        overwrite=args.overwrite,
        ignore_name_contains={"base_weights", "inconsistent", "individu"},
    )


if __name__ == "__main__":
    main()
