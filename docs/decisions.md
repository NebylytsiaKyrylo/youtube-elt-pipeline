# Décisions d'architecture et d'ingénierie

Ce document consigne les choix techniques que j'ai faits sur ce projet et pourquoi.

### D1 — PostgreSQL comme warehouse analytique

J'ai utilisé PostgreSQL 17 comme unique warehouse pour les couches staging, core et marts. Postgres couvre tout ce dont j'ai besoin (fonctions fenêtre, `ON CONFLICT`, arithmétique `INTERVAL`, index partiels) sans coût de licence et tourne nativement dans Docker. À ~20k vidéos et ~40 chaînes, je suis loin du seuil où un warehouse colonnaire ferait une différence.


### D2 — MinIO à la place d'AWS S3 pour la couche raw

J'ai choisi MinIO plutôt qu'AWS S3 pour garder le projet entièrement reproductible en local. MinIO parle exactement la même API boto3 qu'S3 — seule l'URL du endpoint change. Le code est donc portable vers S3 sans réécriture, sans credentials cloud et sans facture.


### D3 — Apache Airflow 3.2 avec LocalExecutor

J'ai utilisé Airflow avec le LocalExecutor. Pour un DAG quotidien avec ~15 tâches, je n'ai pas besoin de Redis ni de Celery. Le LocalExecutor exécute les tâches comme des sous-processus sur le même hôte — c'est suffisant et beaucoup plus simple à opérer.


### D4 — Soda Core pour la qualité des données

J'ai choisi Soda Core pour déclarer les contrôles qualité en YAML. La syntaxe est lisible, les contrôles sont versionnés aux côtés du SQL, et la bibliothèque s'exécute en in-process sans service externe à déployer.


### D5 — Metabase comme couche BI

J'ai connecté Metabase directement au schema `marts`. Metabase introspècte automatiquement les schemas Postgres, ne nécessite aucune configuration pour afficher des dashboards, et tourne dans un seul container. C'est la façon la plus rapide d'exposer les marts visuellement.

**Compromis :** Les définitions de dashboards sont stockées dans la base de données Metabase et ne sont pas versionnées dans Git. Acceptable pour une couche de démonstration.


### D6 — Trois instances PostgreSQL séparées

J'ai fait tourner trois containers Postgres distincts : `pg_elt` pour le warehouse, `pg_airflow` pour les métadonnées Airflow, `pg_metabase` pour les métadonnées Metabase. Mélanger tout dans une seule instance créerait des risques de contamination croisée et ne reflèterait pas ce qu'on retrouve en production.


### D8 — uv pour la gestion des dépendances Python

J'ai choisi `uv` plutôt que pip ou poetry. C'est beaucoup plus rapide (basé sur Rust), il produit un `uv.lock` déterministe, et il s'impose comme le standard moderne. L'installation en CI est nettement plus courte.


### D11 — ruff et sqlfluff pour le linting et le formatage

J'utilise `ruff` pour Python (lint + format en un seul outil) et `sqlfluff` pour SQL. Les deux s'exécutent en CI à chaque push pour garantir une qualité de code cohérente.



### D12 — ELT plutôt qu'ETL

J'ai choisi de stocker les données brutes en premier, puis de transformer à l'intérieur du warehouse avec du SQL. Cette approche me donne deux avantages : je peux rejouer n'importe quelle date passée depuis le fichier brut sans re-solliciter l'API, et les transformations métier sont auditables et versionnées en SQL plutôt que cachées dans du code Python.


### D13 — Quatre couches physiques (raw → staging → core → marts)

Chaque couche a une responsabilité unique et une stratégie de chargement dédiée. Une couche corrompue peut toujours être reconstruite depuis la couche en dessous, ce qui isole les pannes et simplifie le débogage.


### D14 — Star schema (Kimball) pour la couche core

J'ai modélisé le core en deux dimensions et une table de faits. Le star schema réduit le nombre de jointures par requête analytique et c'est le modèle pour lequel les outils BI sont optimisés.


### D15 — Full refresh avec atomic swap pour les marts

J'utilise TRUNCATE+INSERT pour le staging, UPSERT pour le core, et atomic swap pour les marts. À ce volume, un full refresh s'exécute en quelques secondes et l'idempotence est automatique.

Pour les marts, j'ai choisi l'**atomic swap** plutôt qu'un simple DROP+CREATE : chaque mart est construit dans une table `_new`, puis renommé instantanément en remplacement de la table active, et l'ancienne version est supprimée. Metabase ne voit jamais une table vide ou inexistante pendant la reconstruction.


### D16 — JSON plutôt que Parquet pour la couche raw

L'API YouTube retourne du JSON nativement — je le stocke tel quel. Cela préserve une fidélité parfaite de la réponse API, évite toute interprétation de schéma à la frontière, et reste lisible à l'œil pour déboguer.


### D17 — SCD Type 1 sur les dimensions

J'écrase les attributs des dimensions en cas de conflit (nom, abonnés, titre). Les questions métier ont besoin de l'état courant, pas de l'historique des dimensions. L'historique est conservé là où il est utile : dans la table de faits.


### D18 — Soft delete sur `dim_video`

Quand une vidéo disparaît de l'extraction du jour, je la marque `is_active = FALSE` plutôt que de la supprimer. Un hard delete orpheliserait toutes les lignes de faits historiques référençant cette vidéo et casserait les foreign keys.


### D19 — Grain daily snapshot sur la table de faits

La table de faits conserve une ligne par `(vidéo, snapshot_date)`. C'est le seul modèle qui permet de répondre à des questions comme "comment l'engagement a-t-il évolué dans le temps".


### D20 — Surrogate keys (`SERIAL`) sur les dimensions

Chaque dimension a une surrogate key entière (`channel_key`, `video_key`) et conserve la natural key YouTube en colonne `UNIQUE`. C'est la convention Kimball fondamentale — les jointures se font toujours sur la surrogate key, jamais sur la natural key. Cela isole le warehouse des changements de format côté YouTube et garantit des jointures rapides sur des entiers.



### D21 — Idempotence par conception

Ré-exécuter le pipeline sur la même date produit un état identique — aucun doublon, aucun état partiel. Les pipelines échouent et Airflow re-déclenche. Sans idempotence, chaque retry risque de créer des doublons qui nécessitent un nettoyage manuel.


### D22 — Contrôles qualité comme portes bloquantes

Les contrôles Soda s'exécutent après chaque couche et interrompent le run en cas d'échec. Il vaut mieux un pipeline arrêté que des chiffres faux dans les dashboards. J'utilise des seuils de ratio (`> 0.95`) pour absorber le bruit et éviter les faux positifs.


### D23 — Notifications email SMTP

J'envoie un email à chaque échec de tâche et à chaque succès du DAG. Un email d'échec remonte immédiatement le problème. Un email de succès sert de heartbeat quotidien — un email manquant est lui-même un signal d'alerte.


### D24 — Secrets dans les Variables et Connexions Airflow

Tous les secrets (clé API YouTube, credentials MinIO, connexion Postgres, SMTP) sont stockés dans les Variables et Connexions Airflow, jamais dans le code. Le DAG est versionné dans Git — un secret en dur serait exposé.