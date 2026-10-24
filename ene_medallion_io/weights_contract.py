"""Data contract of the ENE weighting pipeline (repository ENE_SURVEY_WEIGHTS).

Every file the weighting code reads is listed here with its MinIO location and
the place it lands under <repository>/data/. Downloading this list on any
computer gives the code everything it needs: data, compute and code are
independent of one another.

Shared by 03_download_weights_inputs.py (read) and 10_upload_weights_inputs.py
(publish the inputs that the weighting stage owns).
"""
from __future__ import annotations

from dataclasses import dataclass

FIRST_QUARTER = "T2_2024"             # start of the ENE-M collection
FIRST_MODELLED_NR_QUARTER = "T1_2026"  # modelled non-response from this quarter on
COHORT_OFFSETS = (1, 4, 5)             # rotation: interviews 2, 3, 4 started 1, 4, 5 quarters earlier
GOLD_INDICATOR_BASE = "base_indicateurs"


def quarter_index(quarter: str) -> int:
    code, year = quarter.split("_", maxsplit=1)
    return 4 * int(year) + int(code[1]) - 1


def quarter_label(index: int) -> str:
    return f"T{index % 4 + 1}_{index // 4}"


def short_label(quarter: str) -> str:
    code, year = quarter.split("_", maxsplit=1)
    return f"{year[2:]}{code}"   # T4_2025 -> 25T4


def quarters_until(quarter: str) -> list[str]:
    return [quarter_label(i) for i in range(quarter_index(FIRST_QUARTER), quarter_index(quarter) + 1)]


def cohort_quarters(quarter: str) -> list[str]:
    if quarter_index(quarter) < quarter_index(FIRST_MODELLED_NR_QUARTER):
        return []
    return [quarter_label(quarter_index(quarter) - offset) for offset in COHORT_OFFSETS]


@dataclass(frozen=True)
class Item:
    bucket: str
    key: str          # object key, or prefix when is_dir
    local: str        # path relative to <repository>/data
    is_dir: bool = False
    optional: bool = False   # may legitimately be empty (e.g. no enumeration update)


# Reference files, not specific to a quarter (published once, updated when they change).
REFERENCES = (
    Item("staging", "enem/references/rgph2021/nb_men_indivs_ZD.dta", "03_processed/RP_2021/nb_men_indivs_ZD.dta"),
    Item("staging", "enem/references/rgph2021/nb_men_reg_milieu.dta", "03_processed/RP_2021/nb_men_reg_milieu.dta"),
    Item("staging", "enem/references/rgph2021/nb_men_indiv_RP.dta", "03_processed/RP_2021/nb_men_indiv_RP.dta"),
    Item("staging", "enem/references/organisation/quarter_resurvey.xlsx", "01_raw/Organisation/quarter_resurvey.xlsx"),
    Item("staging", "enem/references/organisation/Fichier_Matrice_Trimestre.xlsx", "01_raw/Organisation/Fichier_Matrice_Trimestre.xlsx"),
    Item("staging", "enem/references/population/ANStat_Trimestre.xlsx", "01_raw/RpProj/ANStat_Trimestre.xlsx"),
    Item("staging", "enem/references/population/ANStat_Trimestre_2026.xlsx", "06_POPULATION_ESTIMATES/2026/ANStat_Trimestre_2026.xlsx"),
)


def quarter_inputs(quarter: str) -> list[Item]:
    """Inputs of one quarter owned by the weighting stage (enumeration, population totals)."""
    code, year = quarter.split("_", maxsplit=1)
    pop = f"POP_LFS_BY_REGION_SEX_2AGEGR_{year}_{code}.xlsx"
    return [
        Item("staging", f"enem/{quarter}/brutes/denombrement", f"01_raw/Denombrement/{quarter}", is_dir=True),
        Item("staging", f"enem/{quarter}/brutes/denombrement_update", f"01_raw/Denombrement_update/{quarter}",
             is_dir=True, optional=True),
        Item("staging", f"enem/{quarter}/population/{pop}", f"06_POPULATION_ESTIMATES/{year}/{code}/{pop}"),
    ]


def cleaned_survey(quarter: str) -> list[Item]:
    """Cleaned survey files of one quarter (owned by the apurement stage)."""
    return [
        Item("silver", f"enem/{quarter}/menage/menage_{quarter}.dta", f"02_cleaned/Menage/{quarter}/menage_{quarter}.dta"),
        Item("silver", f"enem/{quarter}/individu/individu_{quarter}.dta", f"02_cleaned/Individu/{quarter}/individu_{quarter}.dta"),
    ]


def cohort_inputs(quarter: str) -> list[Item]:
    """Inputs of the modelled non-response: first-interview data of each re-interviewed cohort."""
    items: list[Item] = []
    for cohort in cohort_quarters(quarter):
        traite = f"Traite_{short_label(cohort)}.dta"
        items += [
            Item("silver", f"enem/{cohort}/poids/base_weights/menage_{cohort}.dta",
                 f"04_weights/{cohort}/base_weights/menage_{cohort}.dta"),
            Item("gold", f"enem/{cohort}/{GOLD_INDICATOR_BASE}/{traite}",
                 f"03_processed/base_indicateurs/{cohort}/{traite}"),
        ]
    return items


def weights_inputs(quarter: str) -> list[Item]:
    """Everything the weighting code reads to process `quarter`: references, then the
    cleaned survey and enumeration of every quarter since the start (interview-key
    mapping and re-interviewed cohorts), then the cohort inputs."""
    items = list(REFERENCES)
    for q in quarters_until(quarter):
        items += cleaned_survey(q) + quarter_inputs(q)
    return items + cohort_inputs(quarter)
