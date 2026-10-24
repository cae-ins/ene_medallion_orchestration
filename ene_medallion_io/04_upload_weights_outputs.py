from __future__ import annotations

import argparse
from pathlib import Path

from ene_minio import (
    GOLD_WEIGHTED_BASE,
    add_common_args,
    connect_from_args,
    ensure_ene_period_layout,
    period_label,
    period_prefix,
    upload_directory,
    upload_file,
)


# Data contract of silver/enem/<T>/poids/: the published products of a quarter,
# relative to data/04_weights/<T>/. Anything else in the local folder (tests,
# exploratory files) is never published.
QUARTERLY_WEIGHT_PRODUCTS = (
    "base_weights/base_weights_{label}.dta",
    "base_weights/inconsistent_rows_{label}.dta",
    "base_weights/individu_{label}.dta",
    "base_weights/SR_individu_{label}.dta",
    "base_weights/menage_{label}.dta",
    "base_weights/probabilities_gt1_{label}.dta",
    "base_weights/nr_modele_*_{label}.csv",
    "base_weights/nr_comparaison_*_{label}.csv",
    "calibrated_weights/individu_{label}_CAL.dta",
    "household_weights/menage_weights_*_{label}.dta",
)


def annual_lfs_weight_files(weights_dir: Path, year: str) -> list[Path]:
    """Return the Parquet product first, followed by the DTA compatibility file."""
    annual_files: list[Path] = []
    for suffix in ("parquet", "dta"):
        expected_name = f"LFS_WEIGHTS_{year}.{suffix}"
        direct_candidates = [
            weights_dir / expected_name,
            weights_dir / "calibrated_weights" / expected_name,
        ]
        match = next(
            (candidate for candidate in direct_candidates if candidate.is_file()),
            None,
        )
        if match is None:
            matches = sorted(
                path
                for path in weights_dir.rglob(expected_name)
                if path.is_file()
                and "copie" not in path.name.lower()
                and "copy" not in path.name.lower()
            )
            match = matches[0] if matches else None
        if match is not None:
            annual_files.append(match)
    return annual_files


def quarterly_calibration_images(
    base_dir: Path,
    quarter: str,
    strategy: str,
) -> list[Path]:
    quarter_code, year = quarter.split("_", maxsplit=1)
    calibration_dir = (
        base_dir
        / "data"
        / "07_QUARTERLY_WEIGHTING"
        / year
        / quarter_code
        / strategy
    )
    expected = (
        f"LFS_CALIBRATION_{year}_{quarter_code}_{strategy}_IMAGE.RData"
    )
    direct = calibration_dir / expected
    if direct.is_file():
        return [direct]
    if not calibration_dir.is_dir():
        return []
    return sorted(calibration_dir.glob("LFS_CALIBRATION_*_IMAGE.RData"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Upload ENE technical weight outputs to silver/poids and final "
            "weighted survey bases to gold/base_ponderee."
        )
    )
    add_common_args(parser)
    parser.add_argument("--base-dir", type=Path, default=Path.cwd())
    parser.add_argument(
        "--calibration-strategy",
        default="180X_1D",
        help="Quarterly calibration strategy whose calib_lfs image is published.",
    )
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
        annual_files = annual_lfs_weight_files(weights_dir, args.year)
        if not annual_files:
            print(
                "skip annual weights upload: no Parquet or DTA annual file "
                f"found under {weights_dir}"
            )
            return
        for annual_file in annual_files:
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
                f"{root}/{GOLD_WEIGHTED_BASE}/{key_name}",
                dry_run=args.dry_run,
                overwrite=args.overwrite,
            )
        # Quality report and manifest (method, quarters, checksums) for traceability.
        for name in (f"LFS_WEIGHTS_{args.year}_quality.csv", f"LFS_WEIGHTS_{args.year}_manifest.json"):
            upload_file(
                client,
                weights_dir / name,
                "silver",
                f"{root}/poids/{name}",
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
        include_globs=[pattern.format(label=label) for pattern in QUARTERLY_WEIGHT_PRODUCTS],
    )

    calibration_images = quarterly_calibration_images(
        base_dir,
        args.quarter,
        args.calibration_strategy,
    )
    if not calibration_images:
        print(
            "skip calibration design upload: no image found for "
            f"{args.quarter}/{args.calibration_strategy}"
        )
    for calibration_image in calibration_images:
        upload_file(
            client,
            calibration_image,
            "silver",
            (
                f"{root}/poids/calibration_design/"
                f"{args.calibration_strategy}/{calibration_image.name}"
            ),
            dry_run=args.dry_run,
            overwrite=args.overwrite,
        )

    weighted_base_files = [
        weights_dir / "calibrated_weights" / f"individu_{label}_CAL.dta",
        weights_dir / "base_weights" / f"menage_{label}.dta",
    ]
    for weighted_base_file in weighted_base_files:
        upload_file(
            client,
            weighted_base_file,
            "gold",
            f"{root}/{GOLD_WEIGHTED_BASE}/{weighted_base_file.name}",
            dry_run=args.dry_run,
            overwrite=args.overwrite,
        )


if __name__ == "__main__":
    main()
