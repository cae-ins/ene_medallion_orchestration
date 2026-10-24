"""Data contract of the ENE precision pipeline (repository ENE_PRECISION_ESTIMATION).

Every file the precision code reads is listed here with its MinIO location and the
place it lands in the repository; every file it publishes is derived from the run
manifest. Downloading `precision_inputs()` on any computer gives the R pipeline
(scripts/R/run_all.R --period <T or YYYY>) everything it needs: data, compute and
code are independent of one another.

Unlike weights_contract.Item.local (relative to <repository>/data), `local` is
relative to the repository root here, because inputs live under data/ and the
published results under output/.

Shared by 08_download_precision_inputs.py (read) and 09_upload_precision_outputs.py
(publish the products declared by manifest_<period>.json).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from weights_contract import FIRST_QUARTER, quarter_index, short_label

GOLD_INDICATOR_BASE = "base_indicateurs"
GOLD_PRECISION = "precision"
DEFAULT_CALIBRATION_STRATEGY = "180X_1D"

# Manifest fields whose value is a file published to gold/.../precision/.
# The manifest itself is always published. Every other file of output/<freq>/<period>/
# (older timestamped workbooks, control runs) stays local.
PUBLISHED_MANIFEST_FIELDS = (
    "result_file",                  # precision_<P>.parquet (main Gold product)
    "result_csv_file",              # precision_<P>.csv
    "workbook_file",                # precision_<P>.xlsx, or the timestamped one if locked
    "quality_file",                 # quality_<P>.parquet
    "quality_csv_file",
    "weight_consistency_file",      # weight_consistency_<P>.parquet
    "weight_consistency_csv_file",
    "figure_file",                  # figures/cv_national_<P>.png
    "session_info_file",            # sessionInfo.txt
    "rotation_overlap_file",        # annual only: rotation_overlap_<Y>.parquet
    "rotation_overlap_csv_file",
)

# Produced and kept locally, never published (ReGenesees objects, rebuilt from the inputs):
#   data/design/quarterly/<T>/<strategy>/calib_lfs_<T>_<strategy>.rds   (extracted from the image)
#   data/design/annual/<Y>/rotating_2_2_quarterly_calibrated_covariance/design_lfs_<Y>_*.rds


@dataclass(frozen=True)
class Item:
    bucket: str
    key: str            # object key
    local: str          # path relative to the repository root
    optional: bool = False


def _suffix(asof: str | None) -> str:
    return f"/asof={asof}" if asof else ""


def year_quarters(year: str) -> list[str]:
    """Quarters of `year` collected by the ENE-M (2024 starts at T2: FIRST_QUARTER)."""
    return [f"T{q}_{year}" for q in range(1, 5)
            if quarter_index(f"T{q}_{year}") >= quarter_index(FIRST_QUARTER)]


def indicator_base(period: str, label: str, asof: str | None = None) -> Item:
    """Final indicator base, owned by ENE_INDICATORS_TABULATIONS (07_upload_quarter_bases.py)."""
    if period == "annual":
        name = f"base_indicateurs_precision_{label}.parquet"
        root, local = f"enem/annual/{label}", f"data/inputs/annual/{label}/{name}"
    else:
        name = f"Traite_{short_label(label)}.dta"   # T1_2026 -> Traite_26T1.dta
        root, local = f"enem/{label}", f"data/inputs/quarterly/{label}/{name}"
    return Item("gold", f"{root}/{GOLD_INDICATOR_BASE}{_suffix(asof)}/{name}", local)


def calibration_design(quarter: str, strategy: str = DEFAULT_CALIBRATION_STRATEGY) -> Item:
    """Calibrated ReGenesees image (calib_lfs) of one quarter, owned by ENE_SURVEY_WEIGHTS
    (04_upload_weights_outputs.py)."""
    code, year = quarter.split("_", maxsplit=1)
    name = f"LFS_CALIBRATION_{year}_{code}_{strategy}_IMAGE.RData"
    return Item(
        "silver",
        f"enem/{quarter}/poids/calibration_design/{strategy}/{name}",
        f"data/design/quarterly/{quarter}/{strategy}/{name}",
    )


def precision_inputs(
    period: str,
    *,
    quarter: str | None = None,
    year: str | None = None,
    strategy: str = DEFAULT_CALIBRATION_STRATEGY,
    asof: str | None = None,
    with_design: bool = True,
) -> list[Item]:
    """Everything run_all.R reads for one quarter or one year: the final indicator base,
    then the calibrated design of the quarter, or of every collected quarter of the year
    (the annual variance combines their Taylor variances and Berger-Priam covariances)."""
    if period == "annual":
        if not year:
            raise ValueError("Annual period requires a year.")
        items = [indicator_base("annual", year, asof)]
        quarters = year_quarters(year)
    else:
        if not quarter:
            raise ValueError("Quarterly period requires a quarter.")
        items = [indicator_base("quarterly", quarter, asof)]
        quarters = [quarter]
    if with_design:
        items += [calibration_design(q, strategy) for q in quarters]
    return items


def results_dir(period: str, label: str) -> str:
    """Local results folder written by run_all.R, relative to the repository root."""
    return f"output/{'annual' if period == 'annual' else 'quarterly'}/{label}"


def precision_outputs(period: str, label: str, manifest: dict, asof: str | None = None) -> list[Item]:
    """Products published to gold/.../precision/: the manifest, then the files it declares
    under PUBLISHED_MANIFEST_FIELDS. Raises on an absolute or upward path."""
    root = f"enem/annual/{label}" if period == "annual" else f"enem/{label}"
    destination = f"{root}/{GOLD_PRECISION}{_suffix(asof)}"
    local_dir = results_dir(period, label)
    relatives = [f"manifest_{label}.json"]
    for field_name in PUBLISHED_MANIFEST_FIELDS:
        value = manifest.get(field_name)
        if not isinstance(value, str) or not value:
            continue
        relative = PurePosixPath(value.replace("\\", "/"))
        if relative.is_absolute() or ".." in relative.parts or ":" in value:
            raise ValueError(f"Unsafe file path in precision manifest: {value}")
        relatives.append(relative.as_posix())
    return [Item("gold", f"{destination}/{rel}", f"{local_dir}/{rel}") for rel in dict.fromkeys(relatives)]


def read_manifest(repository: Path, period: str, label: str) -> dict:
    path = repository / results_dir(period, label) / f"manifest_{label}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Precision manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))
