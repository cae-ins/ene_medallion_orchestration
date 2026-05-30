from __future__ import annotations

import argparse
from pathlib import Path

from ene_minio import add_common_args, connect_from_args, download_prefix


def main() -> None:
    parser = argparse.ArgumentParser(description="Download ENE apurement inputs from staging.")
    add_common_args(parser)
    parser.add_argument("--base-dir", type=Path, default=Path.cwd())
    args = parser.parse_args()

    base_dir = args.base_dir.resolve()
    client = connect_from_args(args)

    download_prefix(
        client,
        "staging",
        f"enem/{args.quarter}/brutes",
        base_dir / "datain" / "Base_brute",
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )
    download_prefix(
        client,
        "staging",
        f"enem/{args.quarter}/codification",
        base_dir / "document",
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )
    download_prefix(
        client,
        "staging",
        "enem/references",
        base_dir / "references",
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
