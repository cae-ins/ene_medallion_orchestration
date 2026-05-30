from __future__ import annotations

import argparse
from pathlib import Path

from ene_minio import add_common_args, connect_from_args, ensure_ene_layout, upload_directory, upload_file


def default_raw_dir(base_dir: Path) -> Path:
    candidates = [
        base_dir / "datain" / "Base_brute",
        base_dir / "datain" / "brute",
    ]
    candidates.extend(sorted((base_dir / "datain").glob("Base_brute*")))
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return base_dir / "datain" / "Base_brute"


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload ENE raw inputs to the staging bucket.")
    add_common_args(parser)
    parser.add_argument("--base-dir", type=Path, default=Path.cwd())
    parser.add_argument("--raw-dir", type=Path, default=None)
    parser.add_argument("--codification-dir", type=Path, default=None)
    parser.add_argument("--references-dir", type=Path, default=None)
    parser.add_argument(
        "--other-raw-file",
        type=Path,
        action="append",
        default=[],
        help="Extra raw workbook/file to upload to staging codification, e.g. 'Autres a preciser.xlsx'.",
    )
    args = parser.parse_args()

    base_dir = args.base_dir.resolve()
    raw_dir = args.raw_dir or default_raw_dir(base_dir)
    codification_dir = args.codification_dir
    references_dir = args.references_dir

    client = connect_from_args(args)
    ensure_ene_layout(client, args.quarter, dry_run=args.dry_run)

    upload_directory(
        client,
        raw_dir,
        "staging",
        f"enem/{args.quarter}/brutes",
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )
    if codification_dir:
        upload_directory(
            client,
            codification_dir,
            "staging",
            f"enem/{args.quarter}/codification",
            dry_run=args.dry_run,
            overwrite=args.overwrite,
        )
    for extra_file in args.other_raw_file:
        extra_file = extra_file if extra_file.is_absolute() else base_dir / extra_file
        upload_file(
            client,
            extra_file,
            "staging",
            f"enem/{args.quarter}/codification/{extra_file.name}",
            dry_run=args.dry_run,
            overwrite=args.overwrite,
        )
    if references_dir:
        upload_directory(
            client,
            references_dir,
            "staging",
            "enem/references",
            dry_run=args.dry_run,
            overwrite=args.overwrite,
        )


if __name__ == "__main__":
    main()
