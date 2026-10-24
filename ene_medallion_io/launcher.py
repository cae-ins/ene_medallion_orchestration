"""Shared launcher logic for the ENE business repositories.

Each business repository (ENE_APUREMENT, ENE_SURVEY_WEIGHTS, ENE_INDICATORS_TABULATIONS,
ENE_PRECISION_ESTIMATION) has a short `scripts/medallion/medallion.py` that declares
its commands and calls `main()` below. This module:

- loads the .env files of the current folder, of the business repository and of this
  repository, never overriding a variable already set (credentials never live in code);
- adds the MinIO host to NO_PROXY;
- runs the I/O script of ene_medallion_io/ with the current interpreter and
  `--base-dir <business repository>`.

It works on Windows and Linux and replaces the former PowerShell wrappers.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

IO_DIR = Path(__file__).resolve().parent
ORCHESTRATION_ROOT = IO_DIR.parent


@dataclass(frozen=True)
class Command:
    """One launcher command: the ene_medallion_io script and the options it accepts."""

    script: str
    help: str
    period: bool = False        # accepts --period quarterly|annual and --year
    flags: tuple[str, ...] = field(default_factory=tuple)   # extra boolean flags passed through
    options: tuple[str, ...] = field(default_factory=tuple)  # extra valued options passed through


def load_env_files(project_root: Path) -> None:
    for env_file in dict.fromkeys([Path.cwd() / ".env", project_root / ".env", ORCHESTRATION_ROOT / ".env"]):
        if not env_file.is_file():
            continue
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = (part.strip() for part in line.split("=", 1))
            if name and not os.environ.get(name):
                os.environ[name] = value


def add_minio_host_to_no_proxy() -> None:
    host = urlparse(os.environ.get("MINIO_ENDPOINT", "")).hostname
    if not host:
        return
    hosts = [h.strip() for h in os.environ.get("NO_PROXY", "").split(",") if h.strip()]
    if host not in hosts:
        os.environ["NO_PROXY"] = os.environ["no_proxy"] = ",".join(hosts + [host])


def main(project_root: Path, commands: dict[str, Command], description: str, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=description)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, spec in commands.items():
        p = sub.add_parser(name, help=spec.help)
        p.add_argument("--quarter", default=None, help="TX_YYYY (défaut : ENE_QUARTER)")
        if spec.period:
            p.add_argument("--period", choices=("quarterly", "annual"), default=None,
                           help="défaut : ENE_PERIOD, sinon quarterly")
            p.add_argument("--year", default=None, help="défaut : ENE_YEAR")
        for flag in spec.flags:
            p.add_argument(f"--{flag}", action="store_true")
        for option in spec.options:
            p.add_argument(f"--{option}", default=None)
        p.add_argument("--dry-run", action="store_true")
        p.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    spec = commands[args.command]

    load_env_files(project_root)
    add_minio_host_to_no_proxy()
    # Accented file names must not crash the scripts when their output is redirected (Windows).
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    command = [sys.executable, str(IO_DIR / spec.script), "--base-dir", str(project_root)]
    quarter = args.quarter or os.environ.get("ENE_QUARTER")
    if quarter:
        command += ["--quarter", quarter]
    if spec.period:
        command += ["--period", args.period or os.environ.get("ENE_PERIOD") or "quarterly"]
        year = args.year or os.environ.get("ENE_YEAR")
        if year:
            command += ["--year", year]
    for flag in spec.flags:
        if getattr(args, flag.replace("-", "_")):
            command.append(f"--{flag}")
    for option in spec.options:
        value = getattr(args, option.replace("-", "_"))
        if value is not None:
            command += [f"--{option}", value]
    command += [f for f, on in (("--dry-run", args.dry_run), ("--overwrite", args.overwrite)) if on]

    # The I/O scripts import their sibling modules (ene_minio, weights_contract, ...).
    return subprocess.call(command, cwd=IO_DIR)


def find_orchestration(project_root: Path) -> Path:
    """Used by the business launchers: ENE_ORCHESTRATION_ROOT, else the sibling folder."""
    root = Path(os.environ.get("ENE_ORCHESTRATION_ROOT", project_root.parent / "ENE_MEDALLION_ORCHESTRATION"))
    if not (root / "ene_medallion_io" / "launcher.py").is_file():
        sys.exit(f"ENE_MEDALLION_ORCHESTRATION introuvable : {root} (définir ENE_ORCHESTRATION_ROOT)")
    return root.resolve()
