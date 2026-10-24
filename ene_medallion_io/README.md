# ENE medallion I/O

Python scripts that move ENE files between the business repositories (Stata/R)
and the MinIO medallion buckets. The business pipelines remain in Stata/R; these
scripts only handle I/O.

**Principle: data, code and compute are independent.** The code (git) holds no
path of a given computer; every file a stage reads is on MinIO and is
downloaded into its repository; every product is published back to MinIO, by an
explicit list (never a blind copy of a folder). Repositories never exchange
files directly. Any computer with the repositories and a MinIO access can rerun
any stage.

## Buckets and prefixes

```text
staging/enem/{T}/brutes/                 Survey Solutions export (apurement), denombrement*/ (weighting)
staging/enem/{T}/codification/           codification workbooks (apurement)
staging/enem/{T}/population/             calibration totals (weighting)
staging/enem/references/                 RGPH 2021, rotation table, ANStat projections (weighting)

silver/enem/{T}/menage/  individu/       cleaned files (apurement)
silver/enem/{T}/quality_reports/         apurement error reports
silver/enem/{T}/poids/                   weighting products and calibration_design/

gold/enem/{T}/base_ponderee/             weighted bases (weighting)
gold/enem/{T}/base_indicateurs/          Traite_{YYTq}.dta, pooled base (tabulation)
gold/enem/{T}/indicateurs/               indicator tables (tabulation)
gold/enem/{T}/precision/                 precision results (precision)
gold/enem/annual/{Y}/...                 same products for a year
```

Each prefix has a single owner: apurement writes `staging/.../brutes` (export),
`codification` and `silver/{menage,individu}`; weighting writes the enumeration,
references, population totals, `poids` and `base_ponderee`; tabulation writes
`base_indicateurs` and `indicateurs`; precision writes `precision`.

## Data contracts

One module per stage lists every file the stage reads (MinIO location and local
place) and every product it publishes:

| Stage | Repository | Contract | Download | Publication |
|---|---|---|---|---|
| Apurement | ENE_APUREMENT | `apurement_contract.py` | 01 | 00 (export, codification), 02 (products, quarter marker, manifest) |
| Weighting | ENE_SURVEY_WEIGHTS | `weights_contract.py` | 03 | 10 (inputs), 04 (`QUARTERLY_WEIGHT_PRODUCTS`, annual weights) |
| Tabulation | ENE_INDICATORS_TABULATIONS | `tabulation_contract.py` | 05 | 07 (`base_products`), 06 (`indicator_products`) |
| Precision | ENE_PRECISION_ESTIMATION | `precision_contract.py` | 08 | 09 (fields of the run manifest) |

Every download lists the missing objects at the end and returns a non-zero code
when a mandatory input is absent.

## Launchers

Each business repository has a short `scripts/medallion/medallion.py` built on
`launcher.py`: it loads the `.env` files (current folder, business repository,
this repository; never overriding a variable already set), adds the MinIO host
to `NO_PROXY` and runs the script with `--base-dir <repository>`. Windows and
Linux; this repository is found next to the business repository or in
`ENE_ORCHESTRATION_ROOT`. The former PowerShell wrappers are removed.

```bash
# ENE_APUREMENT
python scripts/medallion/medallion.py download --quarter T1_2026 --dry-run
python scripts/medallion/medallion.py upload-raw --quarter T1_2026 --dry-run
python scripts/medallion/medallion.py upload-outputs --quarter T1_2026 --dry-run

# ENE_SURVEY_WEIGHTS
python scripts/medallion/medallion.py download --quarter T1_2026 --dry-run
python scripts/medallion/medallion.py upload-inputs --quarter T1_2026 --dry-run
python scripts/medallion/medallion.py upload-outputs --quarter T1_2026 --dry-run
python scripts/medallion/medallion.py upload-outputs --period annual --year 2025 --dry-run

# ENE_INDICATORS_TABULATIONS
python scripts/medallion/medallion.py download --quarter T1_2026 --dry-run
python scripts/medallion/medallion.py upload-bases --quarter T1_2026 --dry-run
python scripts/medallion/medallion.py upload-indicators --quarter T1_2026 --dry-run

# ENE_PRECISION_ESTIMATION
python scripts/medallion/medallion.py download --period annual --year 2025 --dry-run
python scripts/medallion/medallion.py upload --period annual --year 2025 --dry-run
```

Use `--overwrite` only to replace existing objects on purpose. Without it, an
existing object is never replaced. `--asof <date>` writes or reads an immutable
version of the tabulation bases and precision results.

## Credentials

No credentials are stored in the code. They come from environment variables or
`.env` (`MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`), or from the
sibling secrets file, read without printing its contents:

```text
../ENE_SECRETS/ENE_SURVEY_WEIGHTS_credentials.json
```

`ENE_CREDENTIALS_FILE` selects a specific file, `ENE_SECRETS_DIR` another
secrets folder.

## Migrations

One-off reorganisations of the buckets are kept in `../migrations/` (for example
`20261024_reorganisation_ponderation.py`), with a manifest written next to what
they change.
