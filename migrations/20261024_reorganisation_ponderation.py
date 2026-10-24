"""One-off migration of 2026-10-24: bring the ENE MinIO layout in line with the data contract.

1. Publish the indicator bases Traite_<YYTq>.dta of the published quarters (T2 2024 to
   T4 2025) to gold/enem/<T>/base_indicateurs/. They are produced by
   ENE_INDICATORS_TABULATIONS and read by the modelled non-response of the weighting
   (first-interview data of the re-interviewed cohorts). Never replaces an object.
2. Remove from gold/enem/T1_2026/base_indicateurs/ the weighting files published there on
   2026-06-06 and 2026-06-25, before the base_ponderee prefix existed (orchestration
   d41158f). Done only once gold/enem/T1_2026/base_ponderee/ holds the calibrated file.
   A manifest records what was removed and why.

Usage (from ene_medallion_io/, MinIO variables loaded as in the PowerShell wrappers):
    python ../migrations/20261024_reorganisation_ponderation.py --tabulation-root <path> [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ene_medallion_io"))
from ene_minio import add_common_args, connect_from_args, head_exists, timestamp_id, upload_file  # noqa: E402
from weights_contract import short_label  # noqa: E402

PUBLISHED_QUARTERS = ("T2_2024", "T3_2024", "T4_2024", "T1_2025", "T2_2025", "T3_2025", "T4_2025")
MISPLACED = (
    "enem/T1_2026/base_indicateurs/individu_T1_2026_CAL.dta",
    "enem/T1_2026/base_indicateurs/menage_T1_2026.dta",
    "enem/T1_2026/base_indicateurs/probabilities_gt1_T1_2026.dta",
)


def traite_source(tabulation_data: Path, quarter: str) -> Path | None:
    name = f"Traite_{short_label(quarter)}.dta"
    for candidate in (tabulation_data / "work" / "quarterly" / quarter / name,
                      tabulation_data / "legacy" / "bulletin_trimestriel" / "Temp" / name):
        if candidate.is_file():
            return candidate
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_common_args(parser)
    parser.add_argument("--tabulation-root", type=Path, required=True)
    args = parser.parse_args()
    client = connect_from_args(args)
    tabulation_data = args.tabulation_root.resolve() / "data"

    print("== 1. Bases Traite_ des trimestres publiés ==")
    for quarter in PUBLISHED_QUARTERS:
        source = traite_source(tabulation_data, quarter)
        if source is None:
            print(f"absent localement : Traite de {quarter}")
            continue
        key = f"enem/{quarter}/base_indicateurs/{source.name}"
        record = upload_file(client, source, "gold", key, dry_run=args.dry_run, overwrite=False)
        if record and not args.dry_run:
            manifest = {
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "migration": "20261024_reorganisation_ponderation",
                "reason": "Entrée de la non-réponse modélisée (cohortes réinterrogées)",
                "files": [record],
            }
            client.put_object(
                Bucket="gold",
                Key=f"enem/{quarter}/base_indicateurs/_manifests/upload_{timestamp_id()}.json",
                Body=json.dumps(manifest, indent=2).encode("utf-8"),
            )

    print("\n== 2. Poids T1 2026 rangés dans base_indicateurs ==")
    if not head_exists(client, "gold", "enem/T1_2026/base_ponderee/individu_T1_2026_CAL.dta"):
        print("base_ponderee/individu_T1_2026_CAL.dta absent : rien n'est retiré.")
        return
    removed = [key for key in MISPLACED if head_exists(client, "gold", key)]
    for key in removed:
        print(f"{'DRY-RUN ' if args.dry_run else ''}remove s3://gold/{key}")
        if not args.dry_run:
            client.delete_object(Bucket="gold", Key=key)
    if removed and not args.dry_run:
        manifest = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "migration": "20261024_reorganisation_ponderation",
            "reason": (
                "Fichiers de pondération publiés avant le préfixe base_ponderee (contrat "
                "orchestration d41158f). Le préfixe base_indicateurs appartient au dépôt de "
                "tabulation. Version courante : gold/enem/T1_2026/base_ponderee/ "
                "(non-réponse modélisée) ; historique : silver/enem/T1_2026/poids/."
            ),
            "removed": removed,
        }
        client.put_object(
            Bucket="gold",
            Key=f"enem/T1_2026/base_indicateurs/_manifests/migration_{timestamp_id()}.json",
            Body=json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8"),
        )


if __name__ == "__main__":
    main()
