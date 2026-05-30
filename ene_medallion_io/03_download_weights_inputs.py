from __future__ import annotations

import argparse
from pathlib import Path

from ene_minio import add_common_args, connect_from_args, download_file, download_prefix


def main() -> None:
    parser = argparse.ArgumentParser(description="Download ENE weights inputs from silver/staging.")
    add_common_args(parser)
    parser.add_argument("--base-dir", type=Path, default=Path.cwd())
    args = parser.parse_args()

    base_dir = args.base_dir.resolve()
    client = connect_from_args(args)

    download_file(
        client,
        "silver",
        f"enem/{args.quarter}/menage/menage_{args.quarter}.dta",
        base_dir / "data" / "02_cleaned" / "Menage" / args.quarter / f"menage_{args.quarter}.dta",
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )
    download_file(
        client,
        "silver",
        f"enem/{args.quarter}/individu/individu_{args.quarter}.dta",
        base_dir / "data" / "02_cleaned" / "Individu" / args.quarter / f"individu_{args.quarter}.dta",
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )
    download_prefix(
        client,
        "staging",
        f"enem/{args.quarter}/brutes/denombrement",
        base_dir / "data" / "01_raw" / "denombrement" / args.quarter,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )
    download_prefix(
        client,
        "staging",
        "enem/references",
        base_dir / "data" / "00_reference",
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
