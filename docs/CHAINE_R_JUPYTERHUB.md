# Faire tourner la chaîne ENE-M en R dans JupyterHub

Ce guide décrit l'exécution de la chaîne ENE-M **sans Stata**, depuis une session
JupyterHub de la Data Platform. Il s'applique à la branche `feat/r-sans-stata` des
cinq dépôts. La version Stata reste sur `main` et sert de référence tant que la
version R n'est pas validée sur plusieurs trimestres (voir
[`JOURNAL_PORTAGE_R.md`](JOURNAL_PORTAGE_R.md)).

## 1. Prérequis

- Session JupyterHub ouverte avec le profil **« ENE-M : R + VS Code + RStudio +
  paquets ENE »** (image `ghcr.io/datalab-registry/ene-r-py:0.2.2` ou plus
  récente ; dépôt `cae-ins/ene-images`). Contrôle : `ene-smoke-test` dans un terminal.
- Accès en lecture aux dépôts `cae-ins` : jeton GitHub (lecture seule, limité aux
  dépôts ENE) enregistré avec `git config --global credential.helper store`, ou
  clé SSH dans `~/.ssh`.
- Clés MinIO de l'agent. L'adresse dans le cluster est
  `http://minio.mon-namespace.svc.cluster.local` (déjà définie par le profil).

## 2. Installation

```bash
git clone -b feat/r-sans-stata https://github.com/cae-ins/ene_medallion_orchestration.git /tmp/orch
bash /tmp/orch/installer_ene.sh          # clone les 5 dépôts dans ~/ENE
nano ~/ENE/.env                          # remplacer les deux replace_me par les clés MinIO
```

Résultat :

```text
~/ENE/
├── .env                          clés MinIO (droits 600, lien dans chaque dépôt métier)
├── ENE_MEDALLION_ORCHESTRATION/  lanceurs MinIO, contrats de données
├── ENE_APUREMENT/
├── ENE_SURVEY_WEIGHTS/
├── ENE_INDICATORS_TABULATIONS/
└── ENE_PRECISION_ESTIMATION/
```

Les lanceurs `scripts/medallion/medallion.py` trouvent l'orchestration dans le dossier
parent. Mise à jour ultérieure : relancer `bash ~/ENE/ENE_MEDALLION_ORCHESTRATION/installer_ene.sh`.

Toujours lancer R avec `Rscript --vanilla` depuis la racine du dépôt :
`--vanilla` évite que le `.Rprofile` de certains dépôts active renv et masque les
paquets de l'image.

## 3. Ordre d'exécution d'un trimestre

Exemple pour T1_2026 (`Q=T1_2026`). Chaque étape lit ses entrées dans MinIO et y
publie ses sorties ; aucune ne lit le dossier d'un autre dépôt.

### 3.1 Apurement (`ENE_APUREMENT`)

```bash
cd ~/ENE/ENE_APUREMENT
python scripts/medallion/medallion.py download --quarter $Q          # staging -> datain/staging
export ENE_DATA_DIR=$PWD ENE_OUT_DIR=$PWD/sortie_r/$Q
Rscript --vanilla R/run_apurement.R --quarter $Q --ecrire
python scripts/medallion/medallion.py upload-outputs --quarter $Q    # voir point ouvert ci-dessous
```

Les règles de recodage, les corrections au cas par cas et les doublons sont dans
`referentiels/*.csv`. Après une modification d'un do-file : 
`Rscript --vanilla R/extraction/extraire_regles.R --quarter $Q`.

**Point ouvert** : le R écrit dans `sortie_r/<Q>/`, alors que `upload-outputs`
publie `dataout/`. Tant que ce n'est pas aligné, ne pas publier depuis la version R.

### 3.2 Pondération (`ENE_SURVEY_WEIGHTS`)

```bash
cd ~/ENE/ENE_SURVEY_WEIGHTS
export ENE_QUARTER=$Q
python scripts/medallion/medallion.py download --quarter $Q
# ordre réel : voir CLAUDE.md du dépôt (01_utils -> 02_base_weights -> 03_nonresponse
# -> 04_calibration/QUARTERLY_WEIGHTING/<année>/<T>/180X_1D/00_Master_Calibration_180X_1D.R)
Rscript --vanilla scripts/04_calibration/QUARTERLY_WEIGHTING/2026/T1/180X_1D/00_Master_Calibration_180X_1D.R
python scripts/medallion/medallion.py upload-outputs --quarter $Q
```

Pour un nouveau trimestre, le dossier du master de calage est d'abord copié depuis le
trimestre précédent (MANUEL du dépôt, étape 7).

### 3.3 Tabulations (`ENE_INDICATORS_TABULATIONS`)

```bash
cd ~/ENE/ENE_INDICATORS_TABULATIONS
python scripts/medallion/medallion.py download --quarter $Q          # bases pondérées + base empilée T-1
Rscript --vanilla scripts/r/production/generate_quarterly.R --quarter $Q
python scripts/medallion/medallion.py upload-indicators --quarter $Q
python scripts/medallion/medallion.py upload-bases --quarter $Q
```

Option `--base-complete` : produit aussi la base empilée complète
`Base_Travail_BT_vf_<AATq>.dta` (charge la base T-1, environ 4 Go, en mémoire).

### 3.4 Précision (`ENE_PRECISION_ESTIMATION`)

```bash
cd ~/ENE/ENE_PRECISION_ESTIMATION
python scripts/medallion/medallion.py download --quarter $Q
Rscript --vanilla scripts/R/run_all.R --period $Q
python scripts/medallion/medallion.py upload --quarter $Q
```

Le contrôle des versions (`config/precision.yml`, `strict: true`) arrête le calcul
si les versions des paquets diffèrent de celles qui ont produit les chiffres publiés.
Relevé des versions de l'image : `Rscript --vanilla scripts/R/00_releve_versions.R`.
Contournement explicite, enregistré dans le manifeste : `ENE_PRECISION_STRICT=false`.

## 4. Vérifier la parité avec Stata

Chaque dépôt porté contient un banc de comparaison R/Stata :

| Dépôt | Commande | Référence |
|---|---|---|
| Apurement | `Rscript --vanilla R/run_apurement.R --quarter $Q --parite` | sorties Stata (`ENE_DATA_DIR`, `ENE_REF_DIR`) |
| Tabulations | `generate_quarterly.R --quarter $Q --comparer-stata <dossier>` | `Traite_<AATq>.dta` et classeur Stata |
| Précision | non-régression sur `output/quarterly/<Q>` | sorties publiées |

Les références Stata intermédiaires se produisent sur un poste disposant de Stata
(`R/reference/ref_brute.do` pour l'apurement,
`scripts/r/production/reference_stata/` pour les tabulations).

## 5. Variables d'environnement

| Variable | Dépôt | Rôle |
|---|---|---|
| `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` | tous | accès MinIO (`~/ENE/.env`) |
| `ENE_ORCHESTRATION_ROOT` | tous | emplacement de l'orchestration s'il n'est pas dans le dossier parent |
| `ENE_QUARTER` | apurement, pondération | trimestre (`TX_YYYY`) |
| `ENE_DATA_DIR`, `ENE_OUT_DIR`, `ENE_REF_DIR` | apurement | données d'entrée, sorties R, références Stata |
| `ENE_EXPORT_ANOMALIES=1` | apurement | écrit les listes d'anomalies Excel |
| `ENE_BASE_DIR`, `ENE_DATA_DIR`, `ENE_STATA_REF_DIR` | tabulations | racine, entrées, référence Stata |
| `ENE_PRECISION_DATA_DIR`, `ENE_PRECISION_STRICT` | précision | racine des entrées, sévérité du contrôle des versions |
