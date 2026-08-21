# ENE medallion I/O

Python scripts for moving ENE files between local Stata/R projects and the
MinIO medallion buckets.

The business pipelines remain in Stata/R. These scripts only handle I/O.

## Buckets and prefixes

```text
staging/enem/T1_2026/brutes/
staging/enem/T1_2026/codification/
staging/enem/references/

bronze/enem/T1_2026/menage/
bronze/enem/T1_2026/individu/

silver/enem/T1_2026/menage/
silver/enem/T1_2026/individu/
silver/enem/T1_2026/poids/

gold/enem/T1_2026/base_ponderee/
gold/enem/T1_2026/base_indicateurs/
gold/enem/T1_2026/indicateurs/
gold/enem/T1_2026/precision/
```

Ownership is explicit: Survey Weights writes `base_ponderee`, Indicators writes
`base_indicateurs` and `indicateurs`, and the precision component writes
`precision`.

## Credentials

No credentials are stored in this folder.

The scripts read credentials from environment variables:

```powershell
$env:MINIO_ENDPOINT = "http://127.0.0.1:9000"
$env:MINIO_ACCESS_KEY = "..."
$env:MINIO_SECRET_KEY = "..."
```

By default, the module also discovers the sibling secrets file without printing
its contents:

```text
../ENE_SECRETS/ENE_SURVEY_WEIGHTS_credentials.json
```

Set `ENE_CREDENTIALS_FILE` to select a specific file or `ENE_SECRETS_DIR` to
select another secrets directory. The legacy fallback remains:

```text
C:\tmp\minio-server\MINIO_LOCAL_CREDENTIALS.txt
```

## Typical commands

From the apurement project root:

```powershell
python tools\ene_medallion_io\00_upload_raw_to_staging.py --quarter T1_2026 --dry-run
python tools\ene_medallion_io\00_upload_raw_to_staging.py --quarter T1_2026
python tools\ene_medallion_io\02_upload_apurement_outputs.py --quarter T1_2026 --dry-run
```

`document/` is not uploaded to `staging/codification` by default. In the ENE
apurement projects it contains Excel observation/error reports produced by
Stata error-identification dofiles. Those files are uploaded by
`02_upload_apurement_outputs.py` to:

```text
silver/enem/{quarter}/quality_reports/apurement_errors/
```

True raw codification or "autres a preciser" files must be passed explicitly
to `00_upload_raw_to_staging.py` with `--codification-dir` or
`--other-raw-file`.

From the weights project root:

```powershell
python path\to\tools\ene_medallion_io\03_download_weights_inputs.py --quarter T1_2026 --base-dir C:\Users\f.migone\Desktop\ENE_SURVEY_WEIGHTS --dry-run
python path\to\tools\ene_medallion_io\04_upload_weights_outputs.py --quarter T1_2026 --base-dir C:\Users\f.migone\Desktop\ENE_SURVEY_WEIGHTS --dry-run
```

Quarterly Gold publication is restricted to
`individu_{quarter}_CAL.dta` and `menage_{quarter}.dta` under
`gold/.../base_ponderee/`. Technical weight artifacts stay in
`silver/.../poids/`.

Annual publication uploads `LFS_WEIGHTS_{year}.parquet` as the primary product
and `LFS_WEIGHTS_{year}.dta` as its compatibility copy to both
`silver/.../poids/` and `gold/.../base_ponderee/` when they are available.

From the tabulation project root:

```powershell
python path\to\tools\ene_medallion_io\05_download_tabulation_inputs.py --quarter T1_2026 --base-dir C:\Users\f.migone\Desktop\ENE_INDICATORS_TABULATIONS --dry-run
python path\to\tools\ene_medallion_io\06_upload_indicator_outputs.py --quarter T1_2026 --base-dir C:\Users\f.migone\Desktop\ENE_INDICATORS_TABULATIONS --dry-run
python path\to\tools\ene_medallion_io\05_download_tabulation_inputs.py --period annual --year 2025 --base-dir C:\Users\f.migone\Desktop\ENE_INDICATORS_TABULATIONS --dry-run
python path\to\tools\ene_medallion_io\06_upload_indicator_outputs.py --period annual --year 2025 --base-dir C:\Users\f.migone\Desktop\ENE_INDICATORS_TABULATIONS --dry-run
python path\to\tools\ene_medallion_io\07_upload_quarter_bases.py --quarter T1_2026 --base-dir C:\Users\f.migone\Desktop\ENE_INDICATORS_TABULATIONS --dry-run
```

Default local directories:

```text
data\inputs\quarterly\{quarter}
data\inputs\annual\{year}
outputs\quarterly\{quarter}
outputs\annual\{year}
```

`06_upload_indicator_outputs.py` excludes `Archive`, `Templates`, `graphs`,
template files, copies, tests, and `2024` files by default. Use
`--include-archives`, `--include-templates`, `--include-graphs`, or
`--include-drafts` only when those files are part of the intended delivery.

From the precision project root:

```powershell
python path\to\tools\ene_medallion_io\08_download_precision_inputs.py --quarter T1_2026 --base-dir C:\Users\f.migone\Desktop\ENE_PRECISION_ESTIMATION --dry-run
python path\to\tools\ene_medallion_io\09_upload_precision_outputs.py --quarter T1_2026 --base-dir C:\Users\f.migone\Desktop\ENE_PRECISION_ESTIMATION --dry-run
python path\to\tools\ene_medallion_io\08_download_precision_inputs.py --period annual --year 2025 --base-dir C:\Users\f.migone\Desktop\ENE_PRECISION_ESTIMATION --dry-run
python path\to\tools\ene_medallion_io\09_upload_precision_outputs.py --period annual --year 2025 --base-dir C:\Users\f.migone\Desktop\ENE_PRECISION_ESTIMATION --dry-run
```

Precision inputs come from `gold/.../base_indicateurs/`. Calibrated designs
come from `silver/.../poids/calibration_design/180X_1D/`; select another one
with `--calibration-strategy`. Annual runs download the T1--T4 calibrated
designs so the precision project can account for PSU rotation rather than
assuming independent quarterly samples. Local results under
`output/quarterly/{quarter}` or `output/annual/{year}` are published to
`gold/.../precision/`. Publication reads `manifest_<period>.json` and uploads
only the files explicitly declared there, so stale locked workbooks are never
sent accidentally.

Use `--overwrite` only when you intentionally want to replace existing objects.
