from __future__ import annotations

import argparse
from pathlib import Path

from ene_minio import (
    GOLD_INDICATOR_BASE,
    add_common_args,
    connect_from_args,
    download_prefix,
    period_prefix,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download ENE indicator bases for design-based precision estimation."
    )
    add_common_args(parser)
    parser.add_argument("--base-dir", type=Path, default=Path.cwd())
    parser.add_argument("--target-dir", type=Path, default=None)
    parser.add_argument("--design-target-dir", type=Path, default=None)
    parser.add_argument(
        "--calibration-strategy",
        default="180X_1D",
        help="Quarterly calibration design to retrieve from Silver weights.",
    )
    parser.add_argument(
        "--skip-design",
        action="store_true",
        help="Download only the final indicator base.",
    )
    parser.add_argument(
        "--asof",
        default=None,
        help=(
            "Optional immutable base version to download from "
            f"{GOLD_INDICATOR_BASE}/asof=<asof>/."
        ),
    )
    args = parser.parse_args()

    base_dir = args.base_dir.resolve()
    if args.target_dir:
        target_dir = args.target_dir
    elif args.period == "annual":
        target_dir = base_dir / "data" / "inputs" / "annual" / args.year
    else:
        target_dir = base_dir / "data" / "inputs" / "quarterly" / args.quarter

    design_root = args.design_target_dir or (base_dir / "data" / "design")
    if args.period != "annual" and args.design_target_dir:
        design_target_dir = args.design_target_dir
    elif args.period != "annual":
        design_target_dir = (
            design_root
            / "quarterly"
            / args.quarter
            / args.calibration_strategy
        )

    root = period_prefix(args.period, quarter=args.quarter, year=args.year)
    suffix = f"/asof={args.asof}" if args.asof else ""

    client = connect_from_args(args)
    download_prefix(
        client,
        "gold",
        f"{root}/{GOLD_INDICATOR_BASE}{suffix}",
        target_dir,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )
    if args.period == "annual" and not args.skip_design:
        for quarter in ("T1", "T2", "T3", "T4"):
            quarter_period = f"{quarter}_{args.year}"
            quarterly_design_target = (
                design_root
                / "quarterly"
                / quarter_period
                / args.calibration_strategy
            )
            download_prefix(
                client,
                "silver",
                (
                    f"enem/{quarter_period}/poids/calibration_design/"
                    f"{args.calibration_strategy}"
                ),
                quarterly_design_target,
                dry_run=args.dry_run,
                overwrite=args.overwrite,
            )
    elif not args.skip_design:
        download_prefix(
            client,
            "silver",
            (
                f"{root}/poids/calibration_design/"
                f"{args.calibration_strategy}"
            ),
            design_target_dir,
            dry_run=args.dry_run,
            overwrite=args.overwrite,
        )


if __name__ == "__main__":
    main()
