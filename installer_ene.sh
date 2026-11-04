#!/usr/bin/env bash
# Installe la chaîne ENE-M dans une session JupyterHub (image ene-r-py).
# Clone les cinq dépôts côte à côte dans $ENE_DIR (défaut ~/ENE), sous les noms
# attendus par les lanceurs medallion.py (ENE_MEDALLION_ORCHESTRATION dans le dossier parent).
#   bash installer_ene.sh [branche]        # défaut : feat/r-sans-stata
# Relancé, il met à jour les dépôts déjà présents (git pull).
set -euo pipefail
BRANCHE="${1:-feat/r-sans-stata}"
ENE_DIR="${ENE_DIR:-$HOME/ENE}"
mkdir -p "$ENE_DIR"
declare -A DEPOTS=(
  [ENE_MEDALLION_ORCHESTRATION]=ene_medallion_orchestration
  [ENE_APUREMENT]=ene_apurement
  [ENE_SURVEY_WEIGHTS]=enem_weight_nv
  [ENE_INDICATORS_TABULATIONS]=ene_indicators_tabulations
  [ENE_PRECISION_ESTIMATION]=ENE_PRECISION_ESTIMATION
)
for dossier in ENE_MEDALLION_ORCHESTRATION ENE_APUREMENT ENE_SURVEY_WEIGHTS ENE_INDICATORS_TABULATIONS ENE_PRECISION_ESTIMATION; do
  cible="$ENE_DIR/$dossier"
  if [ -d "$cible/.git" ]; then
    echo "== $dossier : mise à jour"
    git -C "$cible" fetch origin && git -C "$cible" switch "$BRANCHE" && git -C "$cible" pull --ff-only
  else
    echo "== $dossier : clonage"
    git clone -b "$BRANCHE" "https://github.com/cae-ins/${DEPOTS[$dossier]}.git" "$cible"
  fi
done
# Identifiants MinIO : jamais dans un dépôt. Un seul fichier, lisible par soi seul.
if [ ! -f "$ENE_DIR/.env" ]; then
  cat > "$ENE_DIR/.env" <<'ENV'
MINIO_ENDPOINT=http://minio.mon-namespace.svc.cluster.local
MINIO_ACCESS_KEY=replace_me
MINIO_SECRET_KEY=replace_me
ENV
  chmod 600 "$ENE_DIR/.env"
  echo "A compléter : $ENE_DIR/.env (clés MinIO)"
fi
for dossier in ENE_APUREMENT ENE_SURVEY_WEIGHTS ENE_INDICATORS_TABULATIONS ENE_PRECISION_ESTIMATION; do
  ln -sf "$ENE_DIR/.env" "$ENE_DIR/$dossier/.env"
done
echo "== Chaîne ENE-M installée dans $ENE_DIR (branche $BRANCHE)"
