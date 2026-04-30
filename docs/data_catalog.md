# Data Catalog — Couches Core & Marts

## 1. Vue d'ensemble

Ce catalog documente les deux couches SQL exposées aux consommateurs de données (analystes, outils BI, applications en aval) :

- **Couche Core (schema `core`)** — star schema typé et dédupliqué. Source unique de vérité. Deux dimensions, une table de faits. Upserts quotidiens.
- **Couche Marts (schema `marts`)** — tables analytiques dénormalisées, reconstruites intégralement à chaque run depuis la couche core.

Le schema `staging` (miroir brut de la réponse API, tout en `TEXT`) et la couche JSON brute en object storage sont intentionnellement exclus — ce sont des éléments internes au pipeline, non destinés aux consommateurs.

**Conventions :**

- Chaque dimension porte les colonnes techniques `dwh_loaded_at` (timestamp d'insertion) et `dwh_updated_at` (timestamp de dernière mise à jour).
- Les surrogate keys suivent le modèle `<table>_key`. Les natural keys (business keys issues de la source) sont conservées comme colonnes `UNIQUE`.
- Les boolean flags sont préfixés par `is_`.
- Tous les marts sont **reconstruits quotidiennement** (`DROP TABLE IF EXISTS` + `CREATE TABLE AS SELECT`) ; ils n'ont ni primary keys, ni contraintes, ni colonnes techniques. Leur contenu reflète toujours la dernière snapshot date.

---

## 2. Couche Core

### 2.1. `core.dim_channel`

- **Rôle :** Stocke une ligne par chaîne YouTube dans le périmètre, avec le nom courant, le nombre d'abonnés et la date de création. SCD Type 1 — écrasement en cas de conflit, aucun historique conservé.
- **Grain :** Une ligne par chaîne.
- **Natural key :** `channel_id` (identifiant YouTube de la chaîne).
- **Colonnes :**

| Colonne              | Type de donnée | Description                                                                                    |
|:---------------------|:---------------|:-----------------------------------------------------------------------------------------------|
| `channel_key`        | SERIAL         | Surrogate key (Primary Key) identifiant de façon unique chaque enregistrement. Généré par Postgres. |
| `channel_id`         | VARCHAR(24)    | Natural key — identifiant YouTube de la chaîne (ex. `UCj_iGliGCkLcHSZ8eqVNPDQ`). UNIQUE.      |
| `channel_name`       | TEXT           | Nom affiché de la chaîne, tel que retourné par l'API YouTube. Rafraîchi à chaque run.          |
| `subscribers_count`  | BIGINT         | Nombre d'abonnés courant. Rafraîchi à chaque run.                                             |
| `channel_start_date` | DATE           | Date de création de la chaîne sur YouTube (immuable).                                         |
| `dwh_loaded_at`      | TIMESTAMPTZ    | Timestamp technique de la première insertion dans le warehouse. Défaut : `NOW()`.              |
| `dwh_updated_at`     | TIMESTAMPTZ    | Timestamp technique de la dernière mise à jour. Défaut : `NOW()`, rafraîchi à chaque upsert.  |

---

### 2.2. `core.dim_video`

- **Rôle :** Stocke une ligne par vidéo extraite des playlists d'uploads des chaînes. SCD Type 1 sur le titre et la durée ; supporte le soft delete pour tracer les vidéos qui disparaissent de l'API.
- **Grain :** Une ligne par vidéo.
- **Natural key :** `video_id` (identifiant YouTube de la vidéo).
- **Colonnes :**

| Colonne            | Type de donnée | Description                                                                                                         |
|:-------------------|:---------------|:--------------------------------------------------------------------------------------------------------------------|
| `video_key`        | SERIAL         | Surrogate key (Primary Key) identifiant de façon unique chaque enregistrement. Généré par Postgres.                 |
| `video_id`         | VARCHAR(11)    | Natural key — identifiant YouTube de la vidéo (ex. `qznOtwiGudo`). UNIQUE.                                          |
| `channel_key`      | INT            | Foreign key vers `core.dim_channel(channel_key)`. Identifie la chaîne propriétaire de la vidéo.                    |
| `title`            | TEXT           | Titre de la vidéo tel que retourné par l'API YouTube. NOT NULL. Rafraîchi en cas de conflit.                        |
| `published_at`     | TIMESTAMPTZ    | Timestamp de publication de la vidéo sur YouTube. NOT NULL.                                                         |
| `duration_seconds` | INT            | Durée de la vidéo en secondes, dérivée de la durée ISO 8601 retournée par l'API.                                    |
| `is_active`        | BOOLEAN        | Flag de soft delete. `TRUE` si la vidéo était présente dans le dernier extrait, `FALSE` si elle a disparu.          |
| `deleted_at`       | TIMESTAMPTZ    | Timestamp auquel la vidéo a été marquée comme soft-deleted pour la première fois. `NULL` si encore active.          |
| `dwh_loaded_at`    | TIMESTAMPTZ    | Timestamp technique de la première insertion dans le warehouse. Défaut : `NOW()`.                                   |
| `dwh_updated_at`   | TIMESTAMPTZ    | Timestamp technique de la dernière mise à jour. Défaut : `NOW()`, rafraîchi à chaque upsert.                        |

---

### 2.3. `core.fct_video_daily_snapshot`

- **Rôle :** Stocke une ligne par vidéo et par snapshot date avec ses métriques d'engagement observées. La table de faits s'accumule jour après jour — l'évolution historique est préservée.
- **Grain :** Une ligne par `(video_key, snapshot_date)`. Clé primaire composite.
- **Colonnes :**

| Colonne          | Type de donnée | Description                                                                                                    |
|:-----------------|:---------------|:---------------------------------------------------------------------------------------------------------------|
| `video_key`      | INT            | Foreign key vers `core.dim_video(video_key)`. Partie de la clé primaire composite.                             |
| `channel_key`    | INT            | Foreign key vers `core.dim_channel(channel_key)`. Dénormalisé pour faciliter les requêtes.                     |
| `snapshot_date`  | DATE           | Date à laquelle les métriques ont été capturées (date du run du pipeline). Partie de la clé primaire composite.|
| `video_views`    | BIGINT         | Nombre total de vues de la vidéo observé à la `snapshot_date`. Cumulatif depuis la publication de la vidéo.    |
| `video_likes`    | BIGINT         | Nombre total de likes de la vidéo observé à la `snapshot_date`. Cumulatif depuis la publication de la vidéo.   |
| `video_comments` | BIGINT         | Nombre total de commentaires observé à la `snapshot_date`. Cumulatif depuis la publication de la vidéo.        |
| `dwh_loaded_at`  | TIMESTAMPTZ    | Timestamp technique d'insertion. NOT NULL. Rafraîchi lorsque la ligne est écrasée en cas de conflit.           |

- **Index :**
  - `idx_fct_channel` sur `(channel_key, snapshot_date)` — optimise les agrégations au niveau chaîne et les filtres temporels.
  - Index de clé primaire implicite sur `(video_key, snapshot_date)`.

---

## 3. Couche Marts

Tous les marts partagent le même cycle de vie : ils sont supprimés et recréés depuis `core` à chaque run du pipeline. Ils reflètent la dernière `snapshot_date` disponible dans la table de faits. Les marts n'ont ni primary keys, ni foreign keys, ni colonnes techniques.

### 3.1. `marts.mart_channel_top_views`

- **Rôle :** Classe toutes les chaînes par volume de vues agrégées — classement brut sans pondération.
- **Tri :** `total_views` décroissant.
- **Filtre :** Aucun.
- **Colonnes :**

| Colonne          | Type de donnée | Description                                                                              |
|:-----------------|:---------------|:-----------------------------------------------------------------------------------------|
| `channel_key`    | INT            | Surrogate key issue de `dim_channel`. Identifiant stable pour les jointures en aval.     |
| `channel_name`   | TEXT           | Nom affiché de la chaîne.                                                                |
| `total_videos`   | BIGINT         | Nombre de vidéos contribuant à la dernière snapshot pour cette chaîne.                   |
| `total_views`    | NUMERIC        | Somme des `video_views` sur toutes les vidéos de la chaîne à la dernière snapshot.       |
| `total_likes`    | NUMERIC        | Somme des `video_likes` sur toutes les vidéos de la chaîne à la dernière snapshot.       |
| `total_comments` | NUMERIC        | Somme des `video_comments` sur toutes les vidéos de la chaîne à la dernière snapshot.   |

---

### 3.2. `marts.mart_channel_top_subscribers`

- **Rôle :** Classe toutes les chaînes par nombre d'abonnés courant — classement brut par taille d'audience.
- **Tri :** `subscribers_count` décroissant.
- **Filtre :** Aucun.
- **Colonnes :**

| Colonne             | Type de donnée | Description                                                              |
|:--------------------|:---------------|:-------------------------------------------------------------------------|
| `channel_name`      | TEXT           | Nom affiché de la chaîne.                                                |
| `subscribers_count` | BIGINT         | Nombre d'abonnés courant.                                                |
| `total_views`       | NUMERIC        | Somme des `video_views` sur toutes les vidéos à la dernière snapshot.    |
| `total_videos`      | BIGINT         | Nombre de vidéos contribuant à la dernière snapshot pour cette chaîne.   |

---

### 3.3. `marts.mart_channel_top_likes_rate`

- **Rôle :** Classe les chaînes par ratio likes/vues — proxy d'approbation passive de l'audience.
- **Tri :** `likes_rate` décroissant.
- **Filtre :** Chaînes avec `total_views >= 10 000` (cohérent avec la règle du périmètre à 10k abonnés, exclut les chaînes sous-représentées).
- **Colonnes :**

| Colonne        | Type de donnée | Description                                                                    |
|:---------------|:---------------|:-------------------------------------------------------------------------------|
| `channel_name` | TEXT           | Nom affiché de la chaîne.                                                      |
| `total_views`  | NUMERIC        | Somme des `video_views` sur toutes les vidéos à la dernière snapshot.          |
| `total_likes`  | NUMERIC        | Somme des `video_likes` sur toutes les vidéos à la dernière snapshot.          |
| `likes_rate`   | NUMERIC        | `total_likes / total_views`, arrondi à 3 décimales. Borné entre `[0, 1]`.     |

---

### 3.4. `marts.mart_channel_size_distribution`

- **Rôle :** Distribution des chaînes par buckets de vues cumulées, avec l'engagement moyenné par bucket. Aide à calibrer les recommandations de partenariat par palier d'audience.
- **Tri :** Volume de bucket croissant (`< 1M` → `> 50M`).
- **Filtre :** Aucun.
- **Colonnes :**

| Colonne                  | Type de donnée | Description                                                                                   |
|:-------------------------|:---------------|:----------------------------------------------------------------------------------------------|
| `size_bucket`            | TEXT           | Label du bucket : `< 1M views`, `1M-10M views`, `10M-50M views`, `> 50M views`.              |
| `avg_subscribers_count`  | INT            | Nombre moyen d'abonnés des chaînes dans le bucket, casté en entier.                           |
| `channel_count`          | BIGINT         | Nombre de chaînes appartenant au bucket.                                                      |
| `avg_engagement_score`   | NUMERIC        | Score d'engagement moyen des chaînes dans le bucket, arrondi à 3 décimales. Borné `[0, 2]`.  |

---

### 3.5. `marts.mart_channel_subscribers_vs_engagement`

- **Rôle :** Compare la taille en abonnés à l'intensité d'engagement des chaînes actives — distingue les communautés fidèles des audiences passives.
- **Tri :** `engagement_per_subscriber` décroissant.
- **Filtre :** Chaînes actives uniquement (au moins une vidéo publiée dans les 30 derniers jours).
- **Colonnes :**

| Colonne                     | Type de donnée | Description                                                                                           |
|:----------------------------|:---------------|:------------------------------------------------------------------------------------------------------|
| `channel_name`              | TEXT           | Nom affiché de la chaîne.                                                                             |
| `subscribers_count`         | BIGINT         | Nombre d'abonnés courant.                                                                             |
| `total_views`               | NUMERIC        | Somme des `video_views` sur toutes les vidéos à la dernière snapshot.                                 |
| `engagement_score`          | NUMERIC        | `(likes + comments) / views`, arrondi à 3 décimales. Borné `[0, 2]`.                                 |
| `engagement_per_subscriber` | NUMERIC        | `(likes + comments) / subscribers_count`, arrondi à 3 décimales. Plus élevé = communauté plus engagée.|

---

### 3.6. `marts.mart_channel_latest_videos`

- **Rôle :** Vidéo active la plus récente par chaîne — contrôle de cohérence sur la fraîcheur des publications pour l'éligibilité au partenariat.
- **Tri :** `channel_key` croissant (une ligne par chaîne, ordonnée par surrogate key).
- **Filtre :** `is_active = TRUE` uniquement (exclut les vidéos soft-deleted).
- **Colonnes :**

| Colonne                 | Type de donnée | Description                                                               |
|:------------------------|:---------------|:--------------------------------------------------------------------------|
| `channel_name`          | TEXT           | Nom affiché de la chaîne.                                                 |
| `latest_title`          | TEXT           | Titre de la vidéo active la plus récente de la chaîne.                    |
| `latest_published_at`   | TIMESTAMPTZ    | Timestamp de publication de la vidéo active la plus récente.              |
| `days_since_last_video` | INT            | Nombre de jours entre la snapshot date et la date de publication la plus récente. |

---

### 3.7. `marts.mart_channel_engagement_active`

- **Rôle :** Classement d'engagement pour les chaînes actives — interactions par vue sur l'ensemble du catalogue de la chaîne.
- **Tri :** `engagement_score` décroissant.
- **Filtre :** Chaînes actives uniquement (au moins une vidéo publiée dans les 30 derniers jours).
- **Colonnes :**

| Colonne              | Type de donnée | Description                                                                                              |
|:---------------------|:---------------|:---------------------------------------------------------------------------------------------------------|
| `channel_name`       | TEXT           | Nom affiché de la chaîne.                                                                                |
| `channel_age_years`  | NUMERIC        | Nombre d'années complètes entre `channel_start_date` et la snapshot date. Contexte pour l'accumulation de vues. |
| `last_published`     | TIMESTAMPTZ    | Timestamp de publication de la vidéo la plus récente de la chaîne.                                       |
| `total_videos`       | BIGINT         | Nombre de vidéos contribuant à la dernière snapshot.                                                     |
| `total_views`        | NUMERIC        | Somme des `video_views` sur toutes les vidéos à la dernière snapshot.                                    |
| `total_likes`        | NUMERIC        | Somme des `video_likes` sur toutes les vidéos à la dernière snapshot.                                    |
| `total_comments`     | NUMERIC        | Somme des `video_comments` sur toutes les vidéos à la dernière snapshot.                                 |
| `engagement_score`   | NUMERIC        | `(likes + comments) / views`, arrondi à 3 décimales. Borné `[0, 2]`.                                    |

---

### 3.8. `marts.mart_channel_retention`

- **Rôle :** Classement de rétention pour les chaînes actives — commentaires par vue, isolant l'effort de l'audience au-delà des likes passifs.
- **Tri :** `retention_score` décroissant.
- **Filtre :** Chaînes actives uniquement (au moins une vidéo publiée dans les 30 derniers jours).
- **Colonnes :**

| Colonne            | Type de donnée | Description                                                              |
|:-------------------|:---------------|:-------------------------------------------------------------------------|
| `channel_name`     | TEXT           | Nom affiché de la chaîne.                                                |
| `total_videos`     | BIGINT         | Nombre de vidéos contribuant à la dernière snapshot.                     |
| `total_views`      | NUMERIC        | Somme des `video_views` sur toutes les vidéos à la dernière snapshot.    |
| `total_comments`   | NUMERIC        | Somme des `video_comments` sur toutes les vidéos à la dernière snapshot. |
| `retention_score`  | NUMERIC        | `comments / views`, arrondi à 3 décimales. Borné `[0, 1]`.              |
| `engagement_score` | NUMERIC        | `(likes + comments) / views`, arrondi à 3 décimales. Borné `[0, 2]`.    |

---

### 3.9. `marts.mart_video_top_views`

- **Rôle :** Top 10 des vidéos individuelles par nombre de vues absolu — contenu phare du périmètre.
- **Tri :** Classé avec `DENSE_RANK()` sur `video_views` décroissant ; lignes où `video_rank` est compris entre 1 et 10.
- **Filtre :** Aucun au-delà du seuil de rang.
- **Colonnes :**

| Colonne        | Type de donnée | Description                                              |
|:---------------|:---------------|:---------------------------------------------------------|
| `channel_name` | TEXT           | Nom affiché de la chaîne propriétaire de la vidéo.       |
| `title`        | TEXT           | Titre de la vidéo.                                       |
| `published_at` | TIMESTAMPTZ    | Timestamp de publication de la vidéo.                    |
| `video_views`  | BIGINT         | Nombre de vues de la vidéo à la dernière snapshot.       |
| `video_likes`  | BIGINT         | Nombre de likes de la vidéo à la dernière snapshot.      |

---

### 3.10. `marts.mart_video_format_engagement`

- **Rôle :** Engagement moyen par bucket de durée de vidéo — répond à la question "quelle longueur de vidéo performe le mieux".
- **Tri :** `avg_engagement_score` décroissant.
- **Filtre :** Aucun.
- **Colonnes :**

| Colonne                | Type de donnée | Description                                                                                      |
|:-----------------------|:---------------|:-------------------------------------------------------------------------------------------------|
| `duration_bucket`      | TEXT           | Label du bucket : `0-3 min`, `3-7 min`, `7-15 min`, `15-30 min`, `30+ min`.                     |
| `total_videos`         | BIGINT         | Nombre de vidéos dans le bucket à la dernière snapshot.                                          |
| `avg_views`            | NUMERIC        | Moyenne des `video_views` sur les vidéos du bucket, arrondie à la précision entière.             |
| `avg_engagement_score` | NUMERIC        | `(sum_likes + sum_comments) / sum_views` pour le bucket, arrondi à 3 décimales. Borné `[0, 2]`. |
