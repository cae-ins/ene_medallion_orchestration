"""Data contract of the ENE tabulation stage (repository ENE_INDICATORS_TABULATIONS).

Every file the tabulation code reads is listed here with its MinIO location and
the place it lands in the repository (paths relative to the repository root,
because the tabulation also writes under outputs/). Downloading this list on any
computer gives the code everything it needs: data, compute and code are
independent of one another.

Publication uses explicit product lists, never a blind copy of a folder:
QUARTERLY_BASE_PRODUCTS / ANNUAL_BASE_PRODUCTS (07_upload_quarter_bases.py) and
QUARTERLY_INDICATOR_PRODUCTS / ANNUAL_INDICATOR_PRODUCTS (06_upload_indicator_outputs.py).

Shared by 05_download_tabulation_inputs.py (read), 06 and 07 (publish).
See also docs/CONTRAT_DONNEES.md in ENE_INDICATORS_TABULATIONS.
"""
from __future__ import annotations

from dataclasses import dataclass

from weights_contract import FIRST_QUARTER, quarter_index, quarter_label, short_label

GOLD_WEIGHTED_BASE = "base_ponderee"
GOLD_INDICATOR_BASE = "base_indicateurs"
GOLD_INDICATORS = "indicateurs"


@dataclass(frozen=True)
class Item:
    bucket: str
    key: str          # object key
    local: str        # path relative to the repository root
    optional: bool = False


def previous_quarter(quarter: str) -> str:
    return quarter_label(quarter_index(quarter) - 1)


def pooled_base(quarter: str) -> Item:
    """Pooled work base published for `quarter` (every quarter since FIRST_QUARTER)."""
    code = short_label(quarter)
    name = f"Base_Travail_BT_vf_{code}.dta"
    return Item("gold", f"enem/{quarter}/{GOLD_INDICATOR_BASE}/{name}", f"data/work/quarterly/{quarter}/{name}")


def quarterly_inputs(quarter: str) -> list[Item]:
    """Everything prepare_quarterly.do and tabulate_quarterly.do read for `quarter`:
    the calibrated weighted bases and the pooled base of the previous quarter, which
    the preparation extends with the current quarter (see paths.do, Pooled_Base)."""
    items = [
        Item("gold", f"enem/{quarter}/{GOLD_WEIGHTED_BASE}/individu_{quarter}_CAL.dta",
             f"data/inputs/quarterly/{quarter}/individu_{quarter}_CAL.dta"),
        Item("gold", f"enem/{quarter}/{GOLD_WEIGHTED_BASE}/menage_{quarter}.dta",
             f"data/inputs/quarterly/{quarter}/menage_{quarter}.dta"),
    ]
    if quarter_index(quarter) > quarter_index(FIRST_QUARTER):
        items.append(pooled_base(previous_quarter(quarter)))
    return items


def annual_inputs(year: str, pooled_quarter: str | None = None) -> list[Item]:
    """Inputs of the annual precision base: official annual weights and a pooled base
    that contains the four quarters of `year` (default: the one of T4_<year>)."""
    root = f"enem/annual/{year}/{GOLD_WEIGHTED_BASE}"
    return [
        Item("gold", f"{root}/LFS_WEIGHTS_{year}.parquet", f"data/inputs/annual/{year}/LFS_WEIGHTS_{year}.parquet"),
        Item("gold", f"{root}/LFS_WEIGHTS_{year}.dta", f"data/inputs/annual/{year}/LFS_WEIGHTS_{year}.dta",
             optional=True),
        pooled_base(pooled_quarter or f"T4_{year}"),
    ]


# Products, relative to data/work/quarterly/<T>/ ({code} = 26T1) -> gold/enem/<T>/base_indicateurs/.
QUARTERLY_BASE_PRODUCTS = (
    "Traite_{code}.dta",              # quarter alone; read by ENE_SURVEY_WEIGHTS (modelled non-response)
    "Base_Travail_BT_vf_{code}.dta",  # pooled base; read by the next quarter, diagnostics, precision
)
# Relative to data/work/annual/<a>/ -> gold/enem/annual/<a>/base_indicateurs/.
ANNUAL_BASE_PRODUCTS = (
    "base_indicateurs_precision_{year}.parquet",
    "base_indicateurs_precision_{year}_manifest.json",
    "base_indicateurs_precision_{year}_quality.csv",
)
# Relative to outputs/quarterly/<T>/ and outputs/annual/<a>/ -> gold/<period>/indicateurs/.
QUARTERLY_INDICATOR_PRODUCTS = ("Tableaux_Indicateurs_ENEM.xlsx",)
ANNUAL_INDICATOR_PRODUCTS = ("Tableaux_Indicateurs_ENEM1.xlsx",)


def base_products(period: str, label: str) -> list[str]:
    if period == "annual":
        return [p.format(year=label) for p in ANNUAL_BASE_PRODUCTS]
    return [p.format(code=short_label(label)) for p in QUARTERLY_BASE_PRODUCTS]


def indicator_products(period: str, label: str) -> list[str]:
    return list(ANNUAL_INDICATOR_PRODUCTS if period == "annual" else QUARTERLY_INDICATOR_PRODUCTS)
