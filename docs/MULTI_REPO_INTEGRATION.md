# Integration multi-depots ENE

Le systeme ENE ne doit pas etre pense comme un seul projet local. Il couvre
plusieurs depots Git avec des responsabilites distinctes.

## Depots a prendre en compte

### ENE_APUREMENT

Role metier:

- ingestion des sorties Survey Solutions;
- apurement Stata;
- standardisation menage/individu;
- production des bases apurees.

Responsabilite medallion:

```text
download: staging/enem/{quarter}/...
upload:   bronze/enem/{quarter}/...
upload:   silver/enem/{quarter}/...
```

Scripts concernes:

```text
00_upload_raw_to_staging.py
01_download_apurement_inputs.py
02_upload_apurement_outputs.py
```

### ENE_SURVEY_WEIGHTS

Role metier:

- preparation des inputs de ponderation;
- calcul des poids;
- calibration;
- export des bases ponderees.

Responsabilite medallion:

```text
download: silver/enem/{quarter}/menage/
download: silver/enem/{quarter}/individu/
download: staging/enem/{quarter}/brutes/denombrement/
upload:   silver/enem/{quarter}/poids/
upload:   gold/enem/{quarter}/base_indicateurs/
upload:   silver/enem/annual/{year}/poids/
upload:   gold/enem/annual/{year}/base_indicateurs/
```

Scripts concernes:

```text
03_download_weights_inputs.py
04_upload_weights_outputs.py
```

### ENE_INDICATORS_TABULATIONS

Role metier:

- preparation Stata des bases d'indicateurs;
- tabulations officielles;
- production Excel/Word/PDF des indicateurs.

Important:

- Les tabulations effectivement utilisees sont les dofiles Stata.
- Le code R existant peut rester, mais il ne doit pas remplacer la source de
  verite Stata tant que l'usage metier reste Stata.

Responsabilite medallion:

```text
download: gold/enem/{quarter}/base_indicateurs/
upload:   gold/enem/{quarter}/indicateurs/
download: gold/enem/annual/{year}/base_indicateurs/
upload:   gold/enem/annual/{year}/indicateurs/
```

Scripts concernes:

```text
05_download_tabulation_inputs.py
06_upload_indicator_outputs.py
```

## Regle Git

Chaque depot conserve:

- son historique Git;
- ses scripts metier;
- ses conventions locales existantes quand elles ne bloquent pas le pipeline;
- ses tests ou validations propres.

La couche MinIO ne doit pas melanger les responsabilites Git. Elle sert
uniquement d'interface de donnees entre les depots.

## Organisation recommandee

Deux options sont possibles.

### Option recommandee: depot commun d'orchestration

Creer un depot dedie, par exemple:

```text
ENE_MEDALLION_ORCHESTRATION
```

Il contiendrait:

```text
ene_medallion_io/
  ene_minio.py
  scripts/
  docs/
```

Chaque depot metier appelle ces scripts via un chemin configurable ou installe
le module en editable mode.

Avantage:

- une seule implementation MinIO;
- pas de duplication entre depots;
- meilleure coherence quand le serveur final remplacera l'instance locale.

### Option transitoire: copie controlee dans chaque depot

Chaque depot recoit seulement les wrappers dont il a besoin:

```text
ENE_APUREMENT/scripts/minio/
ENE_SURVEY_WEIGHTS/scripts/minio/
ENE_INDICATORS_TABULATIONS/scripts/minio/
```

Avantage:

- plus simple a executer localement.

Risque:

- divergence rapide des scripts entre depots.

## Regle de versionnement

Ne jamais versionner:

```text
credentials.json
.env
MINIO_LOCAL_CREDENTIALS.txt
__pycache__/
*.pyc
```

Versionner:

```text
scripts I/O
README d'execution
exemples de configuration sans secrets
manifests de specification, pas manifests avec chemins locaux sensibles si non souhaites
```

## Implication pour le systeme actuel

Le module cree actuellement dans:

```text
ENE-M_T1_2026/apurement/tools/ene_medallion_io
```

est une premiere implementation fonctionnelle, mais il doit etre traite comme
un prototype commun. La prochaine etape propre est de le deplacer ou recopier
dans un emplacement d'orchestration partage, puis de creer des wrappers dans
les trois depots metier.
