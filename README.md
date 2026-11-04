# ENE medallion I/O

## Documentation d’architecture

Le flux complet entre les dépôts métier, les couches MinIO, les traitements
trimestriels et la combinaison annuelle de précision est décrit dans
[`docs/SCHEMA_ORCHESTRATION_PRECISION_ENE.md`](docs/SCHEMA_ORCHESTRATION_PRECISION_ENE.md).

Python scripts for moving ENE files between the business repositories and the
MinIO medallion buckets. These scripts only handle I/O.

## Chaîne ENE-M en R (branche `feat/r-sans-stata`)

Sur la branche `feat/r-sans-stata` des cinq dépôts, la chaîne tourne sans Stata
(R pour le traitement, Python pour l'orchestration), à parité avec Stata sur
T1-2026. Sur `main`, l'apurement et les tabulations restent en Stata.

- [`docs/CHAINE_R_JUPYTERHUB.md`](docs/CHAINE_R_JUPYTERHUB.md) : installation dans
  une session JupyterHub (`installer_ene.sh`) et ordre d'exécution d'un trimestre ;
- [`docs/JOURNAL_PORTAGE_R.md`](docs/JOURNAL_PORTAGE_R.md) : décisions, état de la
  parité, points ouverts ;
- [`contrats/enem.yaml`](contrats/enem.yaml) : contrat de données de l'ENE-M (jeux,
  emplacements MinIO, clés), lu par `anstat.io` (R et Python, `cae-ins/anstat-io`).

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

Linux / JupyterHub: the launcher also reads a `.env` file (current folder, business
repository, orchestration) without overriding variables already set.
`installer_ene.sh` creates `~/ENE/.env` (mode 600) and links it into each business
repository:

```bash
MINIO_ENDPOINT=http://minio.mon-namespace.svc.cluster.local
MINIO_ACCESS_KEY=...
MINIO_SECRET_KEY=...
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

Each business repository runs its I/O through its Python launcher
`scripts/medallion/medallion.py` (built on `ene_medallion_io/launcher.py`; Windows
and Linux). The data contracts, the product lists and the commands of the four
stages (apurement, weighting, tabulation, precision) are described in
[`ene_medallion_io/README.md`](ene_medallion_io/README.md).

```bash
python scripts/medallion/medallion.py download --quarter T1_2026 --dry-run
```

Use `--overwrite` only when you intentionally want to replace existing objects.
