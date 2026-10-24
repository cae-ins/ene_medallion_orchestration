"""Data contract of the ENE apurement pipeline (repository ENE_APUREMENT).

Every file the apurement code reads is listed here with its MinIO location and
the place it lands under <repository>/, and every file it publishes is listed
in `apurement_products()`. Downloading the inputs on any computer gives the
Stata code everything it needs: data, compute and code are independent.

Shared by 00_upload_raw_to_staging.py (publish the inputs owned by the
apurement stage), 01_download_apurement_inputs.py (read) and
02_upload_apurement_outputs.py (publish the products).

staging/enem/<T>/brutes/ also holds the enumeration (denombrement/,
denombrement_update/), owned by the weighting stage: the Survey Solutions
export is therefore listed file by file, never downloaded as a whole prefix.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

# Local layout of the apurement repository (relative to its root).
STAGING_DIR = "datain/staging"            # immutable snapshot; Stata mirrors it into datain/brute
CODIFICATION_DIR = "document/codification"
QUALITY_REPORTS_DIR = "document"          # Excel anomaly reports written by the do-files
QUALITY_REPORT_GLOBS = ("*.xls", "*.xlsx")
# Written by program/00-initialisation_brute_depuis_staging.do right after emptying
# dataout/: the quarter whose outputs dataout/ holds.
QUARTER_MARKER = "dataout/apurement_quarter.txt"

# Survey Solutions export files read by the do-files, besides the household export.
SURVEY_EXPORT_READ = (
    "membres.dta",
    "r_activite_s.dta",
    "emigration.dta",
    "r_revenu_h_emp.dta",
    "r_competence_quali.dta",
    "Activiteparent.dta",
    "Revenu.dta",
    "Revenu_es.dta",
)
# Rest of the export: not read by the code, kept so that the snapshot is complete.
SURVEY_EXPORT_OTHER = (
    "assignment__actions.dta",
    "couts_biens.dta",
    "disponibilite.dta",
    "interview__actions.dta",
    "interview__comments.dta",
    "interview__diagnostics.dta",
    "interview__errors.dta",
    "VISITE_IND.dta",
    "VISITE_ROOSTER.dta",
)
# Roster bases produced next to the merged bases (several rows per person).
ROSTERS = (
    "Activiteparent.dta",
    "r_activite_s.dta",
    "r_competence_quali.dta",
    "r_revenu_h_emp.dta",
    "Revenu.dta",
)


def menage_export_name(quarter: str) -> str:
    """Household export of Survey Solutions: ENE_MENAGE_EXPORT, else ENEM_<TX><YYYY>.dta
    (T1_2026 -> ENEM_T12026.dta; same rule as program/parentfile.do)."""
    return os.environ.get("ENE_MENAGE_EXPORT") or f"ENEM_{quarter.replace('_', '')}.dta"


@dataclass(frozen=True)
class Item:
    bucket: str
    key: str          # object key, or prefix when is_dir
    local: str        # path relative to <repository>/
    is_dir: bool = False
    optional: bool = False   # may legitimately be absent


def apurement_inputs(quarter: str) -> list[Item]:
    """Everything the apurement code reads to process `quarter`: the Survey Solutions
    export (into datain/staging) and the codification workbooks (CITP/CIAP)."""
    brutes = f"enem/{quarter}/brutes"
    items = [
        Item("staging", f"{brutes}/{name}", f"{STAGING_DIR}/{name}")
        for name in (menage_export_name(quarter), *SURVEY_EXPORT_READ)
    ]
    items += [
        Item("staging", f"{brutes}/{name}", f"{STAGING_DIR}/{name}", optional=True)
        for name in SURVEY_EXPORT_OTHER
    ]
    items.append(Item("staging", f"enem/{quarter}/codification", CODIFICATION_DIR, is_dir=True))
    return items


def apurement_products(quarter: str) -> list[Item]:
    """Published products of one quarter. The two merged bases are the inputs of the
    weighting stage (weights_contract.cleaned_survey). Section files under
    dataout/standard and datain/standard are intermediate and never published."""
    products = [
        Item("silver", f"enem/{quarter}/menage/menage_{quarter}.dta", "dataout/menage/qx_eec_vf.dta"),
        Item("silver", f"enem/{quarter}/individu/individu_{quarter}.dta", "dataout/individu/membres.dta"),
    ]
    products += [
        Item("silver", f"enem/{quarter}/individu/rosters/{name}", f"dataout/{name}") for name in ROSTERS
    ]
    return products


def quality_reports_prefix(quarter: str) -> str:
    return f"enem/{quarter}/quality_reports/apurement_errors"
