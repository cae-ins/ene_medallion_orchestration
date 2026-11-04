# Journal du portage de la chaîne ENE-M en R

Une entrée par séance : constats, décisions, état de la parité, points ouverts.
Les décisions sont prises par Franck Migone. Le journal de l'environnement
(images, JupyterHub, registre) est tenu à part, dans `cae-ins/ene-images`
(`docs/JOURNAL.md`). Guide d'exécution : [`CHAINE_R_JUPYTERHUB.md`](CHAINE_R_JUPYTERHUB.md).

---

## 2026-11-04 — Audit de reproductibilité, puis portage complet sur T1-2026

### Audit (lecture seule)

Question : la chaîne du bureau peut-elle tourner dans une session JupyterHub
(image `ene-r-py`, Linux, sans Stata) ?

| Dépôt | Constat | Verdict |
|---|---|---|
| Orchestration | Python portable ; 4 tests sur 9 en échec (en retard sur le code) | tourne |
| Pondération | `library(excel.link)` sans condition ; `janitor`, `summarytools`, `gridExtra` absents de l'image ; dossiers `data/` non créés ; pas de renv.lock | presque |
| Précision | versions exactes exigées (`strict: true`) ; scripts 03-07 et repli lisant les dépôts voisins | presque |
| Tabulations | production 100 % Stata (~4 400 lignes) ; prototype R inutilisable ; base annuelle produite par aucun programme | non |
| Apurement | ~30 800 lignes de Stata ; `cmd.exe` + `robocopy` ; 226 chemins avec `\` ; `ssc install violin` | non |

### Décisions

| Sujet | Décision |
|---|---|
| Stata sous Linux | écarté : la copie disponible est pour Windows ; une image Stata Linux poserait en plus la question du nombre d'utilisateurs de la licence |
| Cible | toute la chaîne en R (Python pour l'orchestration) |
| Organisation | branche `feat/r-sans-stata` dans chacun des cinq dépôts ; `main` garde la version Stata comme référence ; fusion après validation |
| Recodages et corrections de l'apurement | sortis du code vers des tables CSV versionnées (`referentiels/`), appliquées par un code générique |
| Critère d'acceptation | parité chiffrée avec Stata, base par base et cellule par cellule ; aucun indicateur déclaré conforme sans comparaison |

### Réalisé et contrôlé (T1-2026, poste Windows, R 4.5.3)

| Dépôt | Travail | Parité |
|---|---|---|
| Orchestration | tests adaptés (9/9), `requirements.txt`, contrat `contrats/enem.yaml` versionné, `installer_ene.sh` | — |
| Pondération | `excel.link` et `rstudioapi` chargés seulement sous Windows en interactif ; dossiers de sortie créés | script lu sans erreur ; **pas exécuté** |
| Précision | entrées par `data/` ou `ENE_PRECISION_DATA_DIR`, repli vers les dépôts voisins supprimé, `ENE_PRECISION_STRICT`, `00_releve_versions.R`, section Linux du README | 72 estimations identiques (écart 0), CSV identique au MD5 |
| Tabulations | préparation et tabulation en R (`scripts/r/production/`), règles de Stata reproduites (`stata_compat.R`) | `Traite_26T1` : 912 variables × 31 939 individus identiques ; 16 indicateurs (18 onglets, 5 932 cellules), écart max 5e-8 |
| Apurement | chaîne complète en R, des exports bruts à `Fusion.do` | 77 bases identiques cellule par cellule |

Apurement, règles extraites : 13 839 `replace` actifs dans les do-files ; 13 797
extraits (`recodages_texte.csv` 13 066, `corrections_cas.csv` 743), 42 non traduits
(boucles sur `r(varlist)`, macros), 525 doublons. Un test vérifie, fichier par
fichier, que actifs = extraits + non traduits.

### Constats

- **`formalite_oit.do`** : la version non commitée du dépôt d'origine (26/10, 17:57)
  est postérieure au `Traite_26T1.dta` et au classeur de T1-2026 (17:23). Avec la
  version actuelle, l'informalité OIT change jusqu'à 1,9 point
  (`Formalite_secteur_OIT`, `Formalite_emploi_OIT`). La version R suit le do-file
  actuel. **À trancher : quelle version est officielle pour T1-2026.**
- **Plan de sondage des tabulations** : `tabulate_quarterly.do` n'utilise que
  `[pw=pmencor_ind]`, sans strate ni UPE ; le `svyset` de la préparation n'a pas
  d'effet sur les sorties. Le R reproduit ce plan.
- **Entrée réelle de l'apurement** : `datain/staging`. Stata modifie
  `datain/brute` en place.
- **Ordre des lignes** : le `merge`/`bysort` de Stata ne trie pas de façon stable
  dans un ménage ; R trie de façon stable. Les valeurs sont identiques, l'ordre
  diffère dans 12 bases.
- **4 `replace … in N`** dans `01-traitrement_autres.do` (lignes 6728, 6739, 6742,
  6955) visent des lignes par leur position dans cet ordre instable. Traduits en clés
  d'individu (`positions_in_resolues.csv`). Deux visent des individus dont `EP6_Aut`
  est vide : probable erreur du do-file.
- **Comportements Stata reproduits** : manquant = +∞ dans les comparaisons, `&` avant
  `|`, abréviations de noms de variables, `cap drop` sur une liste incomplète,
  libellés perdus entre `preserve`/`restore`, `round(-2.5) = -2`, `regexm` sur les
  octets, stockage `float`.
- Les clés MinIO présentes dans l'historique git de `enem_weight_nv` sont toujours
  valides : à changer.

### Ouvert

1. Trancher la version officielle de `formalite_oit.do` pour T1-2026.
2. Premier passage complet sous Linux dans une session `ene-r-py`, T1-2026 lu depuis MinIO.
3. Rejouer un second trimestre (T4-2025) : corrections au cas par cas et `in N` sont propres à T1-2026.
4. Apurement : aligner la sortie R (`sortie_r/<Q>`) sur ce que publie `upload-outputs` (`dataout/`).
5. Apurement : les 42 règles non traduites sont encore interprétées depuis les do-files de `program/` à l'exécution ; à porter en R pour retirer cette dépendance.
6. Apurement : listes d'anomalies Excel (~250) derrière `ENE_EXPORT_ANOMALIES=1`, non reproduites une à une.
7. Pondération : exécuter la chaîne complète (non lancée) ; ajouter un renv.lock ou figer les versions.
8. Précision : aligner `config/precision.yml` sur les versions de l'image (`00_releve_versions.R`) ; fusionner avec les modifications non commitées du poste (indicateurs annuels, scripts 03-07).
9. Tabulations : base annuelle, produite par aucun programme.
10. Changer les clés MinIO exposées dans l'historique git.
