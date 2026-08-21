from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_ROOT = REPO_ROOT / "ene_medallion_io"
sys.path.insert(0, str(MODULE_ROOT))

from ene_minio import (  # noqa: E402
    GOLD_INDICATOR_BASE,
    GOLD_INDICATORS,
    GOLD_PRECISION,
    GOLD_WEIGHTED_BASE,
    ensure_ene_layout,
    ensure_ene_period_layout,
)


def load_numbered_script(filename: str):
    path = MODULE_ROOT / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeLayoutClient:
    def __init__(self) -> None:
        self.keep_keys: list[tuple[str, str]] = []

    def list_buckets(self):
        return {
            "Buckets": [
                {"Name": "staging"},
                {"Name": "bronze"},
                {"Name": "silver"},
                {"Name": "gold"},
            ]
        }

    def put_object(self, *, Bucket, Key, Body):
        self.keep_keys.append((Bucket, Key))


class GoldLayoutTests(unittest.TestCase):
    def test_quarterly_layout_declares_distinct_gold_products(self):
        client = FakeLayoutClient()
        ensure_ene_layout(client, "T1_2026")
        gold_keys = {key for bucket, key in client.keep_keys if bucket == "gold"}
        self.assertEqual(
            gold_keys,
            {
                f"enem/T1_2026/{GOLD_WEIGHTED_BASE}/.keep",
                f"enem/T1_2026/{GOLD_INDICATOR_BASE}/.keep",
                f"enem/T1_2026/{GOLD_INDICATORS}/.keep",
                f"enem/T1_2026/{GOLD_PRECISION}/.keep",
            },
        )

    def test_annual_layout_declares_distinct_gold_products(self):
        client = FakeLayoutClient()
        ensure_ene_period_layout(client, "annual", year="2025")
        gold_keys = {key for bucket, key in client.keep_keys if bucket == "gold"}
        self.assertEqual(
            gold_keys,
            {
                f"enem/annual/2025/{GOLD_WEIGHTED_BASE}/.keep",
                f"enem/annual/2025/{GOLD_INDICATOR_BASE}/.keep",
                f"enem/annual/2025/{GOLD_INDICATORS}/.keep",
                f"enem/annual/2025/{GOLD_PRECISION}/.keep",
            },
        )


class PipelineContractTests(unittest.TestCase):
    def test_annual_weights_publish_parquet_and_dta(self):
        module = load_numbered_script("04_upload_weights_outputs.py")
        upload_file = Mock(return_value={})
        annual_files = [
            Path("LFS_WEIGHTS_2025.parquet"),
            Path("LFS_WEIGHTS_2025.dta"),
        ]
        argv = [
            "04_upload_weights_outputs.py",
            "--period",
            "annual",
            "--year",
            "2025",
            "--base-dir",
            str(REPO_ROOT / "tests" / "_fixture_base"),
        ]
        with (
            patch.object(module, "connect_from_args", return_value=object()),
            patch.object(module, "ensure_ene_period_layout"),
            patch.object(
                module,
                "annual_lfs_weight_files",
                return_value=annual_files,
            ),
            patch.object(module, "upload_file", upload_file),
            patch.object(sys, "argv", argv),
        ):
            module.main()

        destinations = [
            (call.args[1].name, call.args[2], call.args[3])
            for call in upload_file.call_args_list
        ]
        self.assertEqual(
            destinations,
            [
                (
                    "LFS_WEIGHTS_2025.parquet",
                    "silver",
                    "enem/annual/2025/poids/LFS_WEIGHTS_2025.parquet",
                ),
                (
                    "LFS_WEIGHTS_2025.parquet",
                    "gold",
                    (
                        f"enem/annual/2025/{GOLD_WEIGHTED_BASE}/"
                        "LFS_WEIGHTS_2025.parquet"
                    ),
                ),
                (
                    "LFS_WEIGHTS_2025.dta",
                    "silver",
                    "enem/annual/2025/poids/LFS_WEIGHTS_2025.dta",
                ),
                (
                    "LFS_WEIGHTS_2025.dta",
                    "gold",
                    (
                        f"enem/annual/2025/{GOLD_WEIGHTED_BASE}/"
                        "LFS_WEIGHTS_2025.dta"
                    ),
                ),
            ],
        )

    def test_weights_find_the_requested_quarterly_calibration_image(self):
        module = load_numbered_script("04_upload_weights_outputs.py")
        base = Path("C:/fixture")
        image = (
            base
            / "data"
            / "07_QUARTERLY_WEIGHTING"
            / "2026"
            / "T1"
            / "180X_1D"
            / "LFS_CALIBRATION_2026_T1_180X_1D_IMAGE.RData"
        )
        with patch.object(Path, "is_file", return_value=True):
            found = module.quarterly_calibration_images(
                base,
                "T1_2026",
                "180X_1D",
            )

        self.assertEqual(found, [image])

    def test_weights_publish_weighted_bases_not_indicator_bases(self):
        module = load_numbered_script("04_upload_weights_outputs.py")
        upload_directory = Mock(return_value=[])
        upload_file = Mock(return_value={})
        argv = [
            "04_upload_weights_outputs.py",
            "--quarter",
            "T1_2026",
            "--base-dir",
            str(REPO_ROOT / "tests" / "_fixture_base"),
        ]
        with (
            patch.object(module, "connect_from_args", return_value=object()),
            patch.object(module, "ensure_ene_period_layout"),
            patch.object(module, "upload_directory", upload_directory),
            patch.object(module, "upload_file", upload_file),
            patch.object(sys, "argv", argv),
        ):
            module.main()

        self.assertEqual(
            (upload_directory.call_args.args[2], upload_directory.call_args.args[3]),
            ("silver", "enem/T1_2026/poids"),
        )
        gold_destinations = [
            (call.args[1].name, call.args[2], call.args[3])
            for call in upload_file.call_args_list
        ]
        self.assertEqual(
            gold_destinations,
            [
                (
                    "individu_T1_2026_CAL.dta",
                    "gold",
                    f"enem/T1_2026/{GOLD_WEIGHTED_BASE}/individu_T1_2026_CAL.dta",
                ),
                (
                    "menage_T1_2026.dta",
                    "gold",
                    f"enem/T1_2026/{GOLD_WEIGHTED_BASE}/menage_T1_2026.dta",
                ),
            ],
        )

    def test_weights_publish_calibrated_design_to_silver(self):
        module = load_numbered_script("04_upload_weights_outputs.py")
        upload_file = Mock(return_value={})
        image = Path("LFS_CALIBRATION_2026_T1_180X_1D_IMAGE.RData")
        argv = [
            "04_upload_weights_outputs.py",
            "--quarter",
            "T1_2026",
            "--base-dir",
            str(REPO_ROOT / "tests" / "_fixture_base"),
            "--calibration-strategy",
            "180X_1D",
        ]
        with (
            patch.object(module, "connect_from_args", return_value=object()),
            patch.object(module, "ensure_ene_period_layout"),
            patch.object(module, "upload_directory"),
            patch.object(
                module,
                "quarterly_calibration_images",
                return_value=[image],
            ),
            patch.object(module, "upload_file", upload_file),
            patch.object(sys, "argv", argv),
        ):
            module.main()

        silver_calls = [
            call
            for call in upload_file.call_args_list
            if call.args[2] == "silver"
        ]
        self.assertEqual(len(silver_calls), 1)
        self.assertEqual(
            silver_calls[0].args[3],
            (
                "enem/T1_2026/poids/calibration_design/180X_1D/"
                "LFS_CALIBRATION_2026_T1_180X_1D_IMAGE.RData"
            ),
        )

    def test_indicator_preparation_downloads_weighted_bases(self):
        module = load_numbered_script("05_download_tabulation_inputs.py")
        download_prefix = Mock(return_value=[])
        argv = [
            "05_download_tabulation_inputs.py",
            "--quarter",
            "T1_2026",
            "--base-dir",
            str(REPO_ROOT / "tests" / "_fixture_base"),
        ]
        with (
            patch.object(module, "connect_from_args", return_value=object()),
            patch.object(module, "download_prefix", download_prefix),
            patch.object(sys, "argv", argv),
        ):
            module.main()

        self.assertEqual(
            download_prefix.call_args.args[2],
            f"enem/T1_2026/{GOLD_WEIGHTED_BASE}",
        )

    def test_precision_reads_indicator_base_and_writes_precision(self):
        download_module = load_numbered_script("08_download_precision_inputs.py")
        upload_module = load_numbered_script("09_upload_precision_outputs.py")
        download_prefix = Mock(return_value=[])
        upload_file = Mock(return_value={})
        fixture_base = str(REPO_ROOT / "tests" / "_fixture_base")
        download_argv = [
            "08_download_precision_inputs.py",
            "--quarter",
            "T1_2026",
            "--base-dir",
            fixture_base,
            "--asof",
            "2026-06-26",
        ]
        with (
            patch.object(download_module, "connect_from_args", return_value=object()),
            patch.object(download_module, "download_prefix", download_prefix),
            patch.object(sys, "argv", download_argv),
        ):
            download_module.main()

        results_dir = REPO_ROOT / "tests" / "fixtures" / "precision_upload"
        upload_argv = [
            "09_upload_precision_outputs.py",
            "--quarter",
            "T1_2026",
            "--results-dir",
            str(results_dir),
            "--base-dir",
            fixture_base,
            "--asof",
            "2026-06-26",
        ]
        with (
            patch.object(
                upload_module,
                "connect_from_args",
                return_value=object(),
            ),
            patch.object(upload_module, "ensure_ene_period_layout"),
            patch.object(upload_module, "upload_file", upload_file),
            patch.object(sys, "argv", upload_argv),
        ):
            upload_module.main()

        download_prefixes = [call.args[2] for call in download_prefix.call_args_list]
        self.assertEqual(
            download_prefixes,
            [
                f"enem/T1_2026/{GOLD_INDICATOR_BASE}/asof=2026-06-26",
                "enem/T1_2026/poids/calibration_design/180X_1D",
            ],
        )
        uploaded_keys = [call.args[3] for call in upload_file.call_args_list]
        self.assertEqual(
            uploaded_keys,
            [
                f"enem/T1_2026/{GOLD_PRECISION}/asof=2026-06-26/manifest_T1_2026.json",
                f"enem/T1_2026/{GOLD_PRECISION}/asof=2026-06-26/precision_fixture.txt",
                f"enem/T1_2026/{GOLD_PRECISION}/asof=2026-06-26/workbook_approved.txt",
            ],
        )

    def test_annual_precision_downloads_base_and_four_quarterly_designs(self):
        module = load_numbered_script("08_download_precision_inputs.py")
        download_prefix = Mock(return_value=[])
        argv = [
            "08_download_precision_inputs.py",
            "--period",
            "annual",
            "--year",
            "2025",
            "--base-dir",
            str(REPO_ROOT / "tests" / "_fixture_base"),
        ]
        with (
            patch.object(module, "connect_from_args", return_value=object()),
            patch.object(module, "download_prefix", download_prefix),
            patch.object(sys, "argv", argv),
        ):
            module.main()

        self.assertEqual(download_prefix.call_count, 5)
        downloaded_prefixes = [
            call.args[2] for call in download_prefix.call_args_list
        ]
        self.assertEqual(
            downloaded_prefixes,
            [
                f"enem/annual/2025/{GOLD_INDICATOR_BASE}",
                "enem/T1_2025/poids/calibration_design/180X_1D",
                "enem/T2_2025/poids/calibration_design/180X_1D",
                "enem/T3_2025/poids/calibration_design/180X_1D",
                "enem/T4_2025/poids/calibration_design/180X_1D",
            ],
        )


if __name__ == "__main__":
    unittest.main()
