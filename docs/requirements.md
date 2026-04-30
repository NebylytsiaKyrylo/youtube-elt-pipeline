# Cahier des charges — YouTube ELT Pipeline

---

## 1. Contexte du projet

Une agence marketing française spécialisée dans la tech souhaite identifier les chaînes YouTube francophones les plus influentes dans le domaine technique — Data, IA, Développement Web, DevOps, Cybersécurité, Génie Logiciel — afin de conseiller ses clients sur leurs partenariats et leurs formats de contenu.

L'agence fournit une liste curatée de chaînes (collectée manuellement, environ 40 chaînes, minimum 10 000 abonnés chacune). Les métadonnées des chaînes et des vidéos doivent être actualisées automatiquement chaque jour via l'API YouTube Data.

L'objectif final : **classer les chaînes et les vidéos pour alimenter des recommandations de partenariats**, en combinant engagement, rétention, taille d'audience, activité de publication et format vidéo. L'équipe data doit livrer un entrepôt analytique basé sur Postgres, des tables analytiques rafraîchies quotidiennement (marts), ainsi qu'une couche BI interactive pour démontrer les données sur des valeurs réelles.

---

## 2. Spécifications métier

### Périmètre

L'équipe data doit livrer **10 tables analytiques rafraîchies quotidiennement** (marts) couvrant cinq familles de questions métier :

1. **Volume & portée** — qui domine en vues absolues et en abonnés
2. **Engagement & rétention** — qui transforme des vues en interactions
3. **Efficacité d'audience** — qui a la communauté la plus engagée relativement à sa taille
4. **Activité de publication** — qui est encore actif et depuis quand
5. **Performance par format** — quelles durées de vidéo génèrent le meilleur engagement

Chaque mart est reconstruit depuis zéro à chaque exécution (`DROP + CREATE TABLE AS`) à partir de la couche core de l'entrepôt. Les métriques sont calculées sur le dernier snapshot journalier.

### Spécifications des marts

Chaque mart est décrit du point de vue de l'analyste data : question métier, définition des métriques, filtres, résultat attendu et contrat de colonnes.

---

#### M1 — `mart_channel_top_views`

> **Question métier :** Quelles chaînes dominent le périmètre en volume de vues absolu, sans pondération ?
> **Définition :** Somme des `video_views`, `video_likes`, `video_comments` et nombre de vidéos par chaîne, sur le dernier snapshot.
> **Filtre :** Aucun.
> **Résultat attendu :** Toutes les chaînes, triées par `total_views` décroissant.
> **Colonnes :** `channel_key`, `channel_name`, `total_videos`, `total_views`, `total_likes`, `total_comments`.

#### M2 — `mart_channel_top_subscribers`

> **Question métier :** Quelles chaînes ont la plus grande portée d'audience, indépendamment de l'engagement ?
> **Définition :** Nombre d'abonnés et agrégats vues/vidéos par chaîne.
> **Filtre :** Aucun.
> **Résultat attendu :** Toutes les chaînes, triées par `subscribers_count` décroissant.
> **Colonnes :** `channel_name`, `subscribers_count`, `total_views`, `total_videos`.

#### M3 — `mart_channel_top_likes_rate`

> **Question métier :** Quelles chaînes génèrent le taux d'approbation passive (likes par vue) le plus élevé ?
> **Définition :** `likes_rate = total_likes / total_views`.
> **Filtre :** Chaînes avec `total_views >= 10 000` pour exclure les chaînes sous-représentées en données (cohérent avec le critère d'entrée des 10 000 abonnés).
> **Résultat attendu :** Chaînes éligibles triées par `likes_rate` décroissant.
> **Colonnes :** `channel_name`, `total_views`, `total_likes`, `likes_rate`.
> **Critère d'acceptation :** `likes_rate ∈ [0, 1]`.

#### M4 — `mart_channel_size_distribution`

> **Question métier :** Comment les chaînes se répartissent-elles par tranche de vues cumulées, et comment l'engagement varie-t-il selon les tranches ?
> **Définition :** Tranches sur `total_views` : `< 1M`, `1M–10M`, `10M–50M`, `> 50M` (échelle logarithmique — les vues YouTube suivent une loi de puissance). Pour chaque tranche : nombre de chaînes, abonnés moyens, score d'engagement moyen.
> **Filtre :** Aucun.
> **Résultat attendu :** Une ligne par tranche, triée par volume croissant.
> **Colonnes :** `size_bucket`, `avg_subscribers_count`, `channel_count`, `avg_engagement_score`.
> **Critère d'acceptation :** `avg_engagement_score ∈ [0, 2]`.

#### M5 — `mart_channel_subscribers_vs_engagement`

> **Question métier :** Quelles chaînes actives ont une communauté fidèle (fort engagement relatif aux abonnés) par opposition à une audience passive (beaucoup d'abonnés, peu d'interactions) ?
> **Définition :** `engagement_score = (likes + comments) / views` ; `engagement_per_subscriber = (likes + comments) / subscribers_count`.
> **Filtre :** Chaînes actives uniquement — au moins une vidéo publiée dans les 30 derniers jours. Une chaîne inactive avec un ancien pic d'engagement fausserait la comparaison.
> **Résultat attendu :** Toutes les chaînes actives, triées par `engagement_per_subscriber` décroissant.
> **Colonnes :** `channel_name`, `subscribers_count`, `total_views`, `engagement_score`, `engagement_per_subscriber`.
> **Critère d'acceptation :** `engagement_score ∈ [0, 2]`, `engagement_per_subscriber >= 0`.

#### M6 — `mart_channel_latest_videos`

> **Question métier :** Quand chaque chaîne a-t-elle publié pour la dernière fois — est-elle encore assez active pour être candidate à un partenariat ?
> **Définition :** Dernière vidéo active par chaîne ; nombre de jours écoulés depuis la publication.
> **Filtre :** `is_active = TRUE` uniquement (exclut les vidéos en soft delete).
> **Résultat attendu :** Une ligne par chaîne.
> **Colonnes :** `channel_name`, `latest_title`, `latest_published_at`, `days_since_last_video`.
> **Critère d'acceptation :** `days_since_last_video >= 0`.

#### M7 — `mart_channel_engagement_active`

> **Question métier :** Quelles chaînes actives génèrent le plus d'interactions par vue ?
> **Définition :** `engagement_score = (likes + comments) / views`. Le score est calculé sur l'intégralité du catalogue de la chaîne (pas uniquement les vidéos récentes) afin de représenter l'ensemble de la communauté. `channel_age_years` est fourni pour contexte (les chaînes anciennes accumulent davantage de vues passives).
> **Filtre :** Chaînes actives uniquement — au moins une vidéo publiée dans les 30 derniers jours.
> **Résultat attendu :** Une ligne par chaîne active, triée par `engagement_score` décroissant.
> **Colonnes :** `channel_name`, `channel_age_years`, `last_published`, `total_videos`, `total_views`, `total_likes`, `total_comments`, `engagement_score`.
> **Critère d'acceptation :** `engagement_score ∈ [0, 2]`, `channel_age_years >= 0`.

#### M8 — `mart_channel_retention`

> **Question métier :** Quelles chaînes actives ont une communauté qui interagit activement (commentaires) par opposition aux chaînes qui n'accumulent que des vues passives ?
> **Définition :** `retention_score = comments / views` (un commentaire demande un effort — signal plus fort qu'un like). `engagement_score` est fourni en complément pour comparaison.
> **Filtre :** Chaînes actives uniquement — au moins une vidéo publiée dans les 30 derniers jours.
> **Résultat attendu :** Une ligne par chaîne active, triée par `retention_score` décroissant.
> **Colonnes :** `channel_name`, `total_videos`, `total_views`, `total_comments`, `retention_score`, `engagement_score`.
> **Critère d'acceptation :** `retention_score ∈ [0, 1]`, `engagement_score ∈ [0, 2]`.

#### M9 — `mart_video_top_views`

> **Question métier :** Quelles vidéos individuelles ont le plus marqué le périmètre en nombre de vues absolu ?
> **Définition :** Top 10 vidéos par `video_views` sur le dernier snapshot, classées avec `DENSE_RANK` pour gérer les ex-æquo.
> **Filtre :** Aucun.
> **Résultat attendu :** Top 10 vidéos.
> **Colonnes :** `channel_name`, `title`, `published_at`, `video_views`, `video_likes`.

#### M10 — `mart_video_format_engagement`

> **Question métier :** Quelle durée de vidéo génère le meilleur engagement ? L'agence doit-elle recommander des contenus courts ou longs ?
> **Définition :** Tranches sur `duration_seconds / 60` : `0–3 min`, `3–7 min`, `7–15 min`, `15–30 min`, `30+ min`. Pour chaque tranche : nombre de vidéos, vues moyennes, score d'engagement moyen.
> **Filtre :** Aucun.
> **Résultat attendu :** Une ligne par tranche, triée par `avg_engagement_score` décroissant.
> **Colonnes :** `duration_bucket`, `total_videos`, `avg_views`, `avg_engagement_score`.
> **Critère d'acceptation :** `avg_engagement_score ∈ [0, 2]`.

### Couche BI

Un outil BI auto-hébergé doit exposer les marts dans des tableaux de bord interactifs, sur des données réelles issues du pipeline, afin de démontrer la valeur métier de bout en bout. Les tableaux de bord sont illustratifs — les marts constituent le contrat.

---

## 3. Spécifications techniques

### Architecture

Le pipeline suit un flux **ELT** (Extract → Load → Transform) en quatre couches :

```
YouTube API → Stockage objet brut (JSON) → SQL staging → SQL core → SQL marts → BI
```

* **Couche brute (raw)** — fichiers JSON immuables dans un stockage objet compatible S3, un fichier par date d'extraction. Le pipeline doit être **rejouable** depuis n'importe quel fichier brut passé sans re-solliciter l'API.
* **Couche staging** — miroir brut du JSON en SQL, toutes les colonnes typées `TEXT`, **tronquée et rechargée** à chaque exécution (full refresh).
* **Couche core** — schéma en étoile typé et dédupliqué (Kimball) : deux dimensions et une table de faits. Source unique de vérité.
* **Couche marts** — tables analytiques dénormalisées, **reconstruites depuis zéro** à chaque exécution (`DROP + CREATE TABLE AS`).

### Modélisation des données

* **`dim_channel`** — une ligne par chaîne. **SCD Type 1** : les attributs métier (nom, nombre d'abonnés) sont écrasés en cas de conflit. Aucun historique conservé — seul l'état courant compte.
* **`dim_video`** — une ligne par vidéo. SCD Type 1 sur le titre et la durée. Implémente le **soft delete** : une vidéo absente de l'extraction du jour est marquée `is_active = FALSE` avec `deleted_at` renseigné, plutôt que physiquement supprimée. Une vidéo qui réapparaît est réactivée. Le soft delete préserve les lignes historiques de la table de faits référençant cette vidéo.
* **`fct_video_daily_snapshot`** — **l'historique est conservé au niveau de la table de faits**. Grain : une ligne par `(video, snapshot_date)`. Clé primaire composite `(video_key, snapshot_date)`. Métriques journalières : vues, likes, commentaires. Les faits s'accumulent dans le temps ; rejouer la même date écrase uniquement les lignes de ce jour.
* **Clés de substitution** (`SERIAL`) sur les dimensions pour la performance des jointures ; clés naturelles (`channel_id`, `video_id`) conservées en contraintes `UNIQUE`.
* **Index :** `(channel_key, snapshot_date)` sur les faits pour les agrégations par chaîne ; index partiel sur `dim_video` `WHERE is_active = FALSE` pour les requêtes de soft delete.
* **Colonnes techniques** sur chaque dimension : `dwh_loaded_at`, `dwh_updated_at`. Colonne technique sur les faits : `dwh_loaded_at NOT NULL`.

### Stratégie de chargement

| Couche | Stratégie | Justification |
|---|---|---|
| Brute (raw) | Ajout (un fichier par date) | Rejouabilité |
| Staging | TRUNCATE + INSERT | Full refresh, aucune logique de conflit |
| Core dims | UPSERT (`ON CONFLICT DO UPDATE`) | Préserve les clés de substitution entre les exécutions |
| Core fact | INSERT avec mise à jour en conflit sur `(video_key, snapshot_date)` | Rejouer la même date est idempotent |
| Marts | DROP + CREATE TABLE AS | Stratégie idempotente la plus simple |

### Exigences non fonctionnelles

* **Idempotence** — rejouer le pipeline sur la même date doit produire un état identique dans chaque couche.
* **Rejouabilité** — n'importe quelle date passée peut être rechargée depuis le fichier brut sans re-solliciter l'API.
* **Résilience** — l'échec d'une seule chaîne ne doit pas interrompre l'extraction globale ; le pipeline échoue uniquement si **toutes** les chaînes retournent vide.
* **Respect du quota** — l'extraction doit respecter le quota quotidien de l'API YouTube avec une marge suffisante.
* **Stack conteneurisée** — l'ensemble du système doit démarrer avec une seule commande sur n'importe quelle machine disposant de Docker.
* **Secrets** — toutes les credentials doivent vivre dans des variables d'environnement, jamais dans le code source ni dans des fichiers versionnés.
* **Observabilité** — logs structurés au niveau INFO à chaque étape clé ; notifications email en cas de succès et d'échec.
* **Reproductibilité** — un clone frais + `.env` renseigné + `docker compose up` doit amener la stack à un état fonctionnel.

### Orchestration

* **Planifié quotidiennement** à une heure UTC fixe. `catchup=False` (pas de backfill historique).
* **DAG linéaire** avec des portes qualité après chaque couche. Un échec de contrôle qualité **bloque** les tâches en aval.
* **Retries par tâche** avec backoff exponentiel en cas d'échec transitoire.
* **Timeout au niveau du DAG** pour éviter les exécutions bloquées.
* **Dépendances câblées de sorte que la création des DDL s'exécute en parallèle** (une tâche par schéma de couche), et que **tous les marts s'exécutent en parallèle** à l'étape marts.

### Qualité des données

Des contrôles automatisés doivent s'exécuter comme **portes bloquantes** dans le DAG, après chaque couche de l'entrepôt :

* **Porte staging** — sanité du volume de lignes (ratio aujourd'hui/hier), absence de nulls sur les champs obligatoires, absence de doublons sur `video_id`.
* **Porte core** — nombre de lignes attendu par dimension, invariants métier sur les dimensions (`min(subscribers_count) >= 10k`, `dwh_updated_at >= dwh_loaded_at`), intégrité des faits (métriques non négatives, `likes <= views`, `comments <= views`, absence de doublon sur la clé composite, lignes présentes pour la date du jour, date de snapshot maximale égale à la date du jour).
* **Porte marts** — `row_count > 0` pour chaque mart, bornes des scores (engagement `∈ [0, 2]`, rétention `∈ [0, 1]`, likes_rate `∈ [0, 1]`), deltas temporels non négatifs.

### CI/CD

Un workflow d'intégration continue doit s'exécuter à chaque push et pull request sur la branche principale :

* Lint + vérification de format Python
* Lint SQL
* Tests unitaires

La CI doit être verte avant tout merge.

### Tests

* **Tests unitaires** — couvrent le client API (HTTP mocké), l'extracteur (client mocké), la couche de stockage brut (S3 mocké) et le loader staging (SQL mocké). Exécutés en CI.
* **Tests d'intégration** — couvrent le loader staging, les upserts core, le soft delete et les marts contre une vraie instance Postgres. Marqués avec un marker `pytest` pour pouvoir être exclus de la CI.
* **Validation end-to-end** — déclenchement manuel du DAG sur une base vide confirme le flux complet, y compris les portes qualité et les notifications email.

### Stack retenue

| Domaine | Technologie |
|---|---|
| Langage | Python 3.12 |
| Gestion des dépendances | uv |
| Lint / format (Python) | ruff |
| Lint (SQL) | sqlfluff |
| Tests | pytest, pytest-cov |
| Client HTTP | requests + urllib3 retry |
| Stockage objet | MinIO (compatible S3, local) |
| Entrepôt de données | PostgreSQL 17 |
| ORM / exécution SQL | SQLAlchemy + psycopg2 + pandas (chargement staging) |
| Orchestrateur | Apache Airflow 3.x (LocalExecutor) |
| Qualité des données | Soda Core |
| BI / tableaux de bord | Metabase |
| Conteneurisation | Docker, Docker Compose |
| CI | GitHub Actions |
| Notifications | SMTP (templates HTML pour succès / échec) |

---

## 4. Qualité des données & fiabilité

### Objectif

Garantir que les consommateurs en aval (tableaux de bord BI, parties prenantes métier) ne voient que des données ayant passé des contrôles d'intégrité automatisés. Un contrôle échoué doit remonter immédiatement via l'orchestrateur et via les alertes email.

### Spécifications

* **Couverture** — chaque couche de l'entrepôt (staging, core, marts) dispose de sa propre suite de contrôles. Aucune couche n'est exempte.
* **Blocage** — les contrôles qualité sont des portes strictes dans le DAG. Un échec interrompt l'exécution et empêche la propagation de données corrompues vers les marts et les tableaux de bord.
* **Catégories de contrôles par couche :**
  * *Volume* — nombre de lignes, ratios aujourd'hui/hier.
  * *Complétude* — absence de nulls sur les champs obligatoires, absence de doublons sur les clés métier.
  * *Intégrité* — cohérence référentielle, ordre des timestamps techniques.
  * *Invariants métier* — métriques non négatives, `likes <= views`, `comments <= views`, bornes des scores.
  * *Fraîcheur* — les faits contiennent des lignes pour la date courante, la date de snapshot maximale est égale à la date d'exécution.
* **Alerting** — un échec déclenche un email SMTP à l'équipe data avec les contrôles échoués et l'identifiant de l'exécution.
* **Reproductibilité** — les contrôles sont versionnés en YAML aux côtés des transformations SQL.

---

## 5. Documentation & reproductibilité

### Objectif

Un nouveau contributeur — ou le recruteur qui examine ce projet — doit pouvoir comprendre le projet, le reproduire localement et l'opérer sans contacter l'auteur.

### Spécifications

* **README** — `README.md` (français, principal) : présentation du projet, schéma d'architecture, tableau de la stack, démarrage rapide (`docker compose up`), résumé du modèle de données, structure du dépôt, badge CI.
* **Décisions architecturales documentées** — chaque choix technique non évident (architecture en couches, soft delete, full refresh plutôt qu'incrémental, pourquoi MinIO, pourquoi Soda Core, pourquoi Airflow LocalExecutor, SCD Type 1 sur les dims avec historique sur les faits) expliqué avec sa justification dans `docs/decisions.md`.
* **Conventions de nommage documentées** — `docs/naming_conventions.md` décrit les préfixes de colonnes, les préfixes de tables, les conventions de nommage des fichiers et l'organisation des schémas.
* **Runbook opérationnel** — comment ajouter une chaîne, comment rejouer une date passée depuis le stockage brut, comment faire tourner les secrets, comment récupérer d'une exécution échouée.
* **Preuves visuelles** — captures d'écran de la vue Graph d'Airflow, des tableaux de bord Metabase et de la console MinIO incluses dans le README.
* **Hors périmètre, rendu explicite** — une section « Roadmap / Prochaines étapes » listant ce qui n'est intentionnellement pas construit (chargements incrémentaux, migration vers dbt, extraction via dlt, vrai cloud S3, déploiement Kubernetes, promotion multi-environnement).
