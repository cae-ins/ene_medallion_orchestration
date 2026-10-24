from __future__ import annotations

import argparse
from pathlib import Path

from ene_minio import add_common_args, connect_from_args, ensure_ene_layout, upload_directory, upload_file
from weights_contract import REFERENCES, Item, cleaned_survey, quarter_inputs, quarters_until


def publish(client, item: Item, data_dir: Path, *, dry_run: bool, overwrite: bool) -> None:
    source = data_dir / item.local
    if item.is_dir:
        upload_directory(client, source, item.bucket, item.key, dry_run=dry_run, overwrite=overwrite)
    else:
        upload_file(client, source, item.bucket, item.key, dry_run=dry_run, overwrite=overwrite)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Publish the inputs owned by the ENE weighting stage (enumeration, enumeration "
            "updates, population totals, reference files) so that the weighting can run "
            "from MinIO on any computer. See weights_contract.py."
        )
    )
    add_common_args(parser)
    parser.add_argument("--base-dir", type=Path, default=Path.cwd())
    parser.add_argument("--all-quarters", action="store_true",
                        help="Publish every quarter from the start of the survey up to --quarter.")
    parser.add_argument("--references", action="store_true", help="Also publish the reference files.")
    parser.add_argument(
        "--with-cleaned-surveys",
        action="store_true",
        help=(
            "Migration only: publish the local cleaned menage/individu files to silver when "
            "they are missing there. Never replaces an object (owned by the apurement stage)."
        ),
    )
    args = parser.parse_args()

    data_dir = args.base_dir.resolve() / "data"
    client = connect_from_args(args)
    quarters = quarters_until(args.quarter) if args.all_quarters else [args.quarter]

    if args.references:
        for item in REFERENCES:
            publish(client, item, data_dir, dry_run=args.dry_run, overwrite=args.overwrite)

    for quarter in quarters:
        print(f"\n== {quarter} ==")
        ensure_ene_layout(client, quarter, dry_run=args.dry_run)
        for item in quarter_inputs(quarter):
            publish(client, item, data_dir, dry_run=args.dry_run, overwrite=args.overwrite)
        if args.with_cleaned_surveys:
            for item in cleaned_survey(quarter):
                publish(client, item, data_dir, dry_run=args.dry_run, overwrite=False)


if __name__ == "__main__":
    main()
