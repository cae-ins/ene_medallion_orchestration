from __future__ import annotations

import argparse
from pathlib import Path

from ene_minio import add_common_args, connect_from_args, ensure_ene_layout, upload_directory


def upload_if_present(client, path: Path, bucket: str, prefix: str, args) -> None:
    upload_directory(
        client,
        path,
        bucket,
        prefix,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )


def upload_standard_bronze(client, base_dir: Path, args) -> None:
    standard_dir = base_dir / "datain" / "standard"
    menage_dir = standard_dir / "menage"
    individu_dir = standard_dir / "individu"

    if menage_dir.exists() or individu_dir.exists():
        upload_if_present(
            client,
            menage_dir,
            "bronze",
            f"enem/{args.quarter}/menage",
            args,
        )
        upload_if_present(
            client,
            individu_dir,
            "bronze",
            f"enem/{args.quarter}/individu",
            args,
        )
        return

    upload_directory(
        client,
        standard_dir,
        "bronze",
        f"enem/{args.quarter}/menage",
        dry_run=args.dry_run,
        overwrite=args.overwrite,
        ignore_name_contains={"indiv"},
    )
    upload_directory(
        client,
        standard_dir,
        "bronze",
        f"enem/{args.quarter}/individu",
        dry_run=args.dry_run,
        overwrite=args.overwrite,
        ignore_name_contains={"qm_"},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload ENE apurement outputs to bronze/silver.")
    add_common_args(parser)
    parser.add_argument("--base-dir", type=Path, default=Path.cwd())
    parser.add_argument("--quality-dir", type=Path, default=None)
    parser.add_argument("--skip-quality-reports", action="store_true")
    args = parser.parse_args()

    base_dir = args.base_dir.resolve()
    client = connect_from_args(args)
    ensure_ene_layout(client, args.quarter, dry_run=args.dry_run)

    upload_standard_bronze(client, base_dir, args)
    upload_if_present(
        client,
        base_dir / "dataout" / "standard" / "menage",
        "silver",
        f"enem/{args.quarter}/menage/standard",
        args,
    )
    upload_if_present(
        client,
        base_dir / "dataout" / "standard" / "individu",
        "silver",
        f"enem/{args.quarter}/individu/standard",
        args,
    )
    upload_if_present(
        client,
        base_dir / "dataout" / "menage",
        "silver",
        f"enem/{args.quarter}/menage",
        args,
    )
    upload_if_present(
        client,
        base_dir / "dataout" / "individu",
        "silver",
        f"enem/{args.quarter}/individu",
        args,
    )
    if not args.skip_quality_reports:
        quality_dir = args.quality_dir or base_dir / "document"
        upload_if_present(
            client,
            quality_dir,
            "silver",
            f"enem/{args.quarter}/quality_reports/apurement_errors",
            args,
        )


if __name__ == "__main__":
    main()
