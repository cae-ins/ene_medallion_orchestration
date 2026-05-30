from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError


DEFAULT_CREDENTIALS_FILE = Path(r"C:\tmp\minio-server\MINIO_LOCAL_CREDENTIALS.txt")
DEFAULT_ENDPOINT = "http://127.0.0.1:9000"
DEFAULT_QUARTER = "T1_2026"
DEFAULT_YEAR = "2025"


@dataclass(frozen=True)
class MinioSettings:
    endpoint: str
    access_key: str
    secret_key: str
    region: str = "us-east-1"


def read_key_value_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if "url" in data:
            values["MINIO_ENDPOINT"] = data["url"]
        if "accessKey" in data:
            values["MINIO_ACCESS_KEY"] = data["accessKey"]
        if "secretKey" in data:
            values["MINIO_SECRET_KEY"] = data["secretKey"]
        return values

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def load_settings(credentials_file: Path | None = None) -> MinioSettings:
    file_values = read_key_value_file(credentials_file or DEFAULT_CREDENTIALS_FILE)

    endpoint = (
        os.getenv("MINIO_ENDPOINT")
        or file_values.get("MINIO_ENDPOINT")
        or file_values.get("MINIO_CONSOLE", "").replace(":9001", ":9000")
        or DEFAULT_ENDPOINT
    )
    access_key = (
        os.getenv("MINIO_ACCESS_KEY")
        or os.getenv("MINIO_ROOT_USER")
        or file_values.get("MINIO_ACCESS_KEY")
        or file_values.get("MINIO_ROOT_USER")
    )
    secret_key = (
        os.getenv("MINIO_SECRET_KEY")
        or os.getenv("MINIO_ROOT_PASSWORD")
        or file_values.get("MINIO_SECRET_KEY")
        or file_values.get("MINIO_ROOT_PASSWORD")
    )

    if not access_key or not secret_key:
        raise RuntimeError(
            "Missing MinIO credentials. Set MINIO_ACCESS_KEY/MINIO_SECRET_KEY "
            f"or provide a credentials file. Tried: {credentials_file or DEFAULT_CREDENTIALS_FILE}"
        )

    return MinioSettings(
        endpoint=endpoint.rstrip("/"),
        access_key=access_key,
        secret_key=secret_key,
        region=os.getenv("MINIO_REGION", "us-east-1"),
    )


def s3_client(settings: MinioSettings):
    return boto3.client(
        "s3",
        endpoint_url=settings.endpoint,
        aws_access_key_id=settings.access_key,
        aws_secret_access_key=settings.secret_key,
        config=Config(signature_version="s3v4"),
        region_name=settings.region,
    )


def normalize_prefix(prefix: str) -> str:
    prefix = prefix.replace("\\", "/").strip("/")
    return f"{prefix}/" if prefix else ""


def object_key(prefix: str, relative_path: Path) -> str:
    rel = relative_path.as_posix().strip("/")
    return f"{normalize_prefix(prefix)}{rel}"


def iter_files(root: Path, ignore_dir_names: set[str] | None = None) -> Iterable[Path]:
    if not root.exists():
        return []
    ignore_dir_names = ignore_dir_names or set()
    ignored_prefixes = ("~$", ".~")
    ignored_suffixes = (".tmp", ".temp")
    return (
        path
        for path in root.rglob("*")
        if path.is_file()
        and not any(part.startswith(".git") for part in path.parts)
        and not any(part in ignore_dir_names for part in path.relative_to(root).parts[:-1])
        and not any(path.name.startswith(prefix) for prefix in ignored_prefixes)
        and path.suffix.lower() not in ignored_suffixes
    )


def filter_files_by_name(
    files: Iterable[Path],
    *,
    ignore_name_contains: set[str] | None = None,
) -> list[Path]:
    ignore_name_contains = {item.lower() for item in (ignore_name_contains or set())}
    result: list[Path] = []
    for path in files:
        lowered = path.name.lower()
        if any(fragment in lowered for fragment in ignore_name_contains):
            continue
        result.append(path)
    return result


def head_exists(client, bucket: str, key: str) -> bool:
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code in {"404", "NoSuchKey", "NotFound"}:
            return False
        raise


def ensure_bucket(client, bucket: str, dry_run: bool = False) -> None:
    buckets = [item["Name"] for item in client.list_buckets().get("Buckets", [])]
    if bucket in buckets:
        return
    if dry_run:
        print(f"DRY-RUN create bucket {bucket}")
        return
    client.create_bucket(Bucket=bucket)
    print(f"created bucket {bucket}")


def put_keep(client, bucket: str, prefix: str, dry_run: bool = False) -> None:
    key = f"{normalize_prefix(prefix)}.keep"
    if dry_run:
        print(f"DRY-RUN put s3://{bucket}/{key}")
        return
    client.put_object(Bucket=bucket, Key=key, Body=b"")


def ensure_ene_layout(client, quarter: str, dry_run: bool = False) -> None:
    layout = {
        "staging": [
            f"enem/{quarter}/brutes/",
            f"enem/{quarter}/codification/",
            "enem/references/",
        ],
        "bronze": [
            f"enem/{quarter}/menage/",
            f"enem/{quarter}/individu/",
        ],
        "silver": [
            f"enem/{quarter}/menage/",
            f"enem/{quarter}/individu/",
            f"enem/{quarter}/poids/",
        ],
        "gold": [
            f"enem/{quarter}/base_indicateurs/",
            f"enem/{quarter}/indicateurs/",
        ],
    }
    for bucket, prefixes in layout.items():
        ensure_bucket(client, bucket, dry_run=dry_run)
        for prefix in prefixes:
            put_keep(client, bucket, prefix, dry_run=dry_run)


def period_label(period: str, *, quarter: str | None = None, year: str | None = None) -> str:
    if period == "annual":
        if not year:
            raise ValueError("Annual period requires --year.")
        return year
    if not quarter:
        raise ValueError("Quarterly period requires --quarter.")
    return quarter


def period_prefix(period: str, *, quarter: str | None = None, year: str | None = None) -> str:
    if period == "annual":
        return f"enem/annual/{period_label(period, year=year)}"
    return f"enem/{period_label(period, quarter=quarter)}"


def ensure_ene_period_layout(
    client,
    period: str,
    *,
    quarter: str | None = None,
    year: str | None = None,
    dry_run: bool = False,
) -> None:
    if period == "quarterly":
        ensure_ene_layout(client, period_label(period, quarter=quarter), dry_run=dry_run)
        return

    root = period_prefix(period, year=year)
    layout = {
        "silver": [
            f"{root}/poids/",
        ],
        "gold": [
            f"{root}/base_indicateurs/",
            f"{root}/indicateurs/",
        ],
    }
    for bucket, prefixes in layout.items():
        ensure_bucket(client, bucket, dry_run=dry_run)
        for prefix in prefixes:
            put_keep(client, bucket, prefix, dry_run=dry_run)


def upload_directory(
    client,
    local_dir: Path,
    bucket: str,
    prefix: str,
    *,
    dry_run: bool = False,
    overwrite: bool = False,
    manifest: bool = True,
    ignore_dir_names: set[str] | None = None,
    ignore_name_contains: set[str] | None = None,
) -> list[dict[str, object]]:
    local_dir = local_dir.resolve()
    if not local_dir.exists():
        print(f"skip missing local directory: {local_dir}")
        return []

    records: list[dict[str, object]] = []
    files = sorted(
        filter_files_by_name(
            iter_files(local_dir, ignore_dir_names=ignore_dir_names),
            ignore_name_contains=ignore_name_contains,
        )
    )
    for path in files:
        rel = path.relative_to(local_dir)
        key = object_key(prefix, rel)
        size = path.stat().st_size
        record = {
            "source": str(path),
            "bucket": bucket,
            "key": key,
            "size": size,
            "modified_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
        }
        records.append(record)

        if dry_run:
            print(f"DRY-RUN upload {path} -> s3://{bucket}/{key}")
            continue
        if not overwrite and head_exists(client, bucket, key):
            print(f"skip existing s3://{bucket}/{key}")
            continue
        client.upload_file(str(path), bucket, key)
        print(f"uploaded {path.name} -> s3://{bucket}/{key}")

    if manifest and records and not dry_run:
        manifest_key = f"{normalize_prefix(prefix)}_manifests/upload_{timestamp_id()}.json"
        body = json.dumps(
            {
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "local_dir": str(local_dir),
                "bucket": bucket,
                "prefix": normalize_prefix(prefix),
                "file_count": len(records),
                "total_bytes": sum(int(item["size"]) for item in records),
                "files": records,
            },
            indent=2,
        ).encode("utf-8")
        client.put_object(Bucket=bucket, Key=manifest_key, Body=body)
        print(f"uploaded manifest -> s3://{bucket}/{manifest_key}")

    print(f"{'would upload' if dry_run else 'processed'} {len(records)} file(s)")
    return records


def upload_file(
    client,
    local_file: Path,
    bucket: str,
    key: str,
    *,
    dry_run: bool = False,
    overwrite: bool = False,
) -> dict[str, object] | None:
    local_file = local_file.resolve()
    if not local_file.exists() or not local_file.is_file():
        print(f"skip missing local file: {local_file}")
        return None

    key = key.replace("\\", "/").strip("/")
    record = {
        "source": str(local_file),
        "bucket": bucket,
        "key": key,
        "size": local_file.stat().st_size,
        "modified_utc": datetime.fromtimestamp(local_file.stat().st_mtime, timezone.utc).isoformat(),
    }

    if dry_run:
        print(f"DRY-RUN upload {local_file} -> s3://{bucket}/{key}")
        return record
    if not overwrite and head_exists(client, bucket, key):
        print(f"skip existing s3://{bucket}/{key}")
        return record
    client.upload_file(str(local_file), bucket, key)
    print(f"uploaded {local_file.name} -> s3://{bucket}/{key}")
    return record


def download_prefix(
    client,
    bucket: str,
    prefix: str,
    local_dir: Path,
    *,
    dry_run: bool = False,
    overwrite: bool = False,
) -> list[dict[str, object]]:
    normalized = normalize_prefix(prefix)
    paginator = client.get_paginator("list_objects_v2")
    records: list[dict[str, object]] = []

    for page in paginator.paginate(Bucket=bucket, Prefix=normalized):
        for item in page.get("Contents", []):
            key = item["Key"]
            if key.endswith("/.keep") or "/_manifests/" in key:
                continue
            rel = key.removeprefix(normalized)
            if not rel:
                continue
            target = local_dir / Path(rel)
            records.append(
                {
                    "bucket": bucket,
                    "key": key,
                    "target": str(target),
                    "size": item.get("Size", 0),
                }
            )
            if dry_run:
                print(f"DRY-RUN download s3://{bucket}/{key} -> {target}")
                continue
            if target.exists() and not overwrite:
                print(f"skip existing {target}")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            client.download_file(bucket, key, str(target))
            print(f"downloaded s3://{bucket}/{key} -> {target}")

    print(f"{'would download' if dry_run else 'processed'} {len(records)} object(s)")
    return records


def timestamp_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--period",
        choices=["quarterly", "annual"],
        default=os.getenv("ENE_PERIOD", "quarterly"),
    )
    parser.add_argument("--quarter", default=os.getenv("ENE_QUARTER", DEFAULT_QUARTER))
    parser.add_argument("--year", default=os.getenv("ENE_YEAR", DEFAULT_YEAR))
    parser.add_argument("--credentials-file", type=Path, default=DEFAULT_CREDENTIALS_FILE)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")


def connect_from_args(args):
    settings = load_settings(args.credentials_file)
    client = s3_client(settings)
    client.list_buckets()
    return client
