# ENE medallion I/O

## Documentation d’architecture

Le flux complet entre les dépôts métier, les couches MinIO, les traitements
trimestriels et la combinaison annuelle de précision est décrit dans
[`docs/SCHEMA_ORCHESTRATION_PRECISION_ENE.md`](docs/SCHEMA_ORCHESTRATION_PRECISION_ENE.md).

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

silver/enem/annual/2025/poids/
gold/enem/annual/2025/base_ponderee/
gold/enem/annual/2025/base_indicateurs/
gold/enem/annual/2025/indicateurs/
gold/enem/annual/2025/precision/
```

Gold prefixes have distinct owners:

- `ENE_SURVEY_WEIGHTS` publishes final weighted survey files to
  `base_ponderee/`;
- `ENE_INDICATORS_TABULATIONS` publishes its prepared analysis base to
  `base_indicateurs/` and official tabulations to `indicateurs/`;
- `ENE_PRECISION_ESTIMATION` reads `base_indicateurs/` and publishes
  standard errors, CVs, confidence intervals and design effects to
  `precision/`.

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

The two merged apurement bases are also published with stable silver names:

```text
silver/enem/{quarter}/menage/menage_{quarter}.dta
silver/enem/{quarter}/individu/individu_{quarter}.dta
```

`03_download_weights_inputs.py` downloads only these two stable objects into
`data\02_cleaned`, rather than copying every technical silver artifact.

From the weights project root:

```powershell
python path\to\tools\ene_medallion_io\03_download_weights_inputs.py --quarter T1_2026 --base-dir C:\Users\f.migone\Desktop\ENE_SURVEY_WEIGHTS --dry-run
python path\to\tools\ene_medallion_io\04_upload_weights_outputs.py --quarter T1_2026 --base-dir C:\Users\f.migone\Desktop\ENE_SURVEY_WEIGHTS --dry-run
python path\to\tools\ene_medallion_io\04_upload_weights_outputs.py --period annual --year 2025 --base-dir C:\Users\f.migone\Desktop\ENE_SURVEY_WEIGHTS --dry-run
```

For a quarterly period, Gold receives only the two stable weighted survey
products expected by the Indicators pipeline:

```text
gold/enem/{quarter}/base_ponderee/individu_{quarter}_CAL.dta
gold/enem/{quarter}/base_ponderee/menage_{quarter}.dta
```

Diagnostics and intermediate weight files remain under `silver/.../poids/`.
For quarterly runs, the selected calibrated ReGenesees image is also published
as a reusable design artifact:

```text
silver/enem/{quarter}/poids/calibration_design/{strategy}/LFS_CALIBRATION_*_IMAGE.RData
```

The default strategy is `180X_1D`; use `--calibration-strategy` when another
calibration is the official one for the period.

For annual weights, the script looks for `LFS_WEIGHTS_{year}.parquet` and the
compatibility file `LFS_WEIGHTS_{year}.dta` under `data\04_weights\{year}` or
`data\04_weights\{year}\calibrated_weights`. Every available format is uploaded,
with Parquet treated as the primary product:

```text
silver/enem/annual/{year}/poids/
gold/enem/annual/{year}/base_ponderee/
```

Household weight helper files under `household_weights\` are not uploaded as
annual gold/silver outputs by this script.

From the tabulation project root:

```powershell
python path\to\tools\ene_medallion_io\05_download_tabulation_inputs.py --quarter T1_2026 --base-dir C:\Users\f.migone\Desktop\ENE_INDICATORS_TABULATIONS --dry-run
python path\to\tools\ene_medallion_io\06_upload_indicator_outputs.py --quarter T1_2026 --base-dir C:\Users\f.migone\Desktop\ENE_INDICATORS_TABULATIONS --dry-run
python path\to\tools\ene_medallion_io\05_download_tabulation_inputs.py --period annual --year 2025 --base-dir C:\Users\f.migone\Desktop\ENE_INDICATORS_TABULATIONS --dry-run
python path\to\tools\ene_medallion_io\06_upload_indicator_outputs.py --period annual --year 2025 --results-dir C:\path\to\annual\outputs --base-dir C:\Users\f.migone\Desktop\ENE_INDICATORS_TABULATIONS --dry-run
python path\to\tools\ene_medallion_io\07_upload_quarter_bases.py --quarter T1_2026 --base-dir C:\Users\f.migone\Desktop\ENE_INDICATORS_TABULATIONS --dry-run
```

`06_upload_indicator_outputs.py` excludes `Archive`, `Templates`, `graphs`,
template files, copies, tests, and `2024` files by default. Use
`--include-archives`, `--include-templates`, `--include-graphs`, or
`--include-drafts` only when those files are part of the intended delivery.

For indicator preparation, `05_download_tabulation_inputs.py` reads the final
weighted survey files from `gold/.../base_ponderee/` and writes them into the
standardized runtime folders of `ENE_INDICATORS_TABULATIONS`:

```text
data\inputs\quarterly\{quarter}
data\inputs\annual\{year}
```

`06_upload_indicator_outputs.py` publishes from:

```text
outputs\quarterly\{quarter}
outputs\annual\{year}
```

`--target-dir` and `--results-dir` remain available for explicit overrides.

From the precision project:

```powershell
python path\to\tools\ene_medallion_io\08_download_precision_inputs.py --quarter T1_2026 --base-dir C:\Users\f.migone\Desktop\ENE_PRECISION_ESTIMATION --dry-run
python path\to\tools\ene_medallion_io\09_upload_precision_outputs.py --quarter T1_2026 --base-dir C:\Users\f.migone\Desktop\ENE_PRECISION_ESTIMATION --dry-run
python path\to\tools\ene_medallion_io\08_download_precision_inputs.py --period annual --year 2025 --base-dir C:\Users\f.migone\Desktop\ENE_PRECISION_ESTIMATION --dry-run
python path\to\tools\ene_medallion_io\09_upload_precision_outputs.py --period annual --year 2025 --base-dir C:\Users\f.migone\Desktop\ENE_PRECISION_ESTIMATION --dry-run
```

The download reads `gold/.../base_indicateurs/`. For quarterly periods it also
retrieves the selected calibrated design from
`silver/.../poids/calibration_design/{strategy}/`. For annual periods it
retrieves the four quarterly calibrated designs T1--T4: the precision project
combines their Taylor variances and Berger--Priam covariances under the PSU
rotation scheme. Uploads go to `gold/.../precision/`. Both commands accept
`--asof` for an explicit immutable Gold version.

The precision upload is manifest-driven: only files declared by
`manifest_<period>.json` are published. This prevents an older canonical Excel
workbook from being uploaded when Windows forced the R pipeline to write a
timestamped replacement.

Use `--overwrite` only when you intentionally want to replace existing objects.
