# **Conventions de nommage**

Ce document décrit les conventions de nommage utilisées pour les schemas, tables, colonnes et fichiers du pipeline YouTube ELT.

## **Table des matières**

1. [Principes généraux](#principes-généraux)
2. [Nommage des schemas](#nommage-des-schemas)
3. [Conventions de nommage des tables](#conventions-de-nommage-des-tables)
   - [Règles Staging](#règles-staging)
   - [Règles Core](#règles-core)
   - [Règles Marts](#règles-marts)
4. [Conventions de nommage des colonnes](#conventions-de-nommage-des-colonnes)
   - [Surrogate Keys](#surrogate-keys)
   - [Business Keys](#business-keys)
   - [Colonnes techniques](#colonnes-techniques)
   - [Boolean Flags](#boolean-flags)
   - [Colonnes Soft Delete](#colonnes-soft-delete)
5. [Conventions de nommage des fichiers](#conventions-de-nommage-des-fichiers)
   - [Fichiers SQL](#fichiers-sql)
   - [Fichiers Python](#fichiers-python)
   - [Fichiers Soda](#fichiers-soda)
   - [Fichiers Template](#fichiers-template)

---

## **Principes généraux**

- **Casse** : Utiliser le `snake_case` — lettres minuscules séparées par des underscores (`_`).
- **Langue** : L'anglais pour tous les noms d'objets.
- **Mots réservés** : Ne pas utiliser de mots réservés SQL comme noms d'objets.

---

## **Nommage des schemas**

Le pipeline est organisé en trois schemas, chacun représentant une couche du processus ELT.

| Schema    | Rôle                                                              | Exemples de tables                        |
|-----------|-------------------------------------------------------------------|-------------------------------------------|
| `staging` | Données brutes chargées directement depuis l'API YouTube          | `yt_video_snapshot`                       |
| `core`    | Données nettoyées et modélisées (dimensions et tables de faits)   | `dim_channel`, `fct_video_daily_snapshot` |
| `marts`   | Tables agrégées, prêtes pour le reporting                         | `mart_channel_top_subscribers`            |

---

## **Conventions de nommage des tables**

### **Règles Staging**

- Tous les noms doivent commencer par le préfixe du système source, suivi du nom de l'entité.
- **`<source>_<entity>`**
  - `<source>` : Identifiant court du système source. Dans ce projet : `yt` (YouTube).
  - `<entity>` : Décrit le type de données extraites.
  - Exemple : `yt_video_snapshot` → snapshot brut des données vidéo extraites depuis l'API YouTube.

### **Règles Core**

- Tous les noms doivent commencer par un préfixe de catégorie indiquant le type de table.
- **`<category>_<entity>`**
  - `<category>` : Décrit le rôle de la table (`dim` pour dimension, `fct` pour fait).
  - `<entity>` : Nom descriptif de l'objet métier.
  - Exemples :
    - `dim_channel` → Table de dimension contenant les attributs d'une chaîne.
    - `dim_video` → Table de dimension contenant les attributs d'une vidéo.
    - `fct_video_daily_snapshot` → Table de faits stockant les métriques quotidiennes des vidéos (vues, likes, commentaires).

#### **Glossaire des préfixes de catégorie (Core)**

| Préfixe | Signification   | Exemple(s)                         |
|---------|-----------------|------------------------------------|
| `dim_`  | Table dimension | `dim_channel`, `dim_video`         |
| `fct_`  | Table de faits  | `fct_video_daily_snapshot`         |

### **Règles Marts**

- Tous les noms doivent commencer par le préfixe `mart_`, suivi du domaine métier et d'un qualificatif descriptif.
- **`mart_<domain>_<metric>`**
  - `mart_` : Préfixe fixe pour identifier les tables de reporting.
  - `<domain>` : Le sujet métier analysé (`channel`, `video`).
  - `<metric>` : Ce qui est mesuré ou classé.
  - Exemples :
    - `mart_channel_top_subscribers` → Chaînes classées par nombre d'abonnés.
    - `mart_channel_engagement_active` → Métriques d'engagement pour les chaînes actives.
    - `mart_video_format_engagement` → Engagement ventilé par format de durée des vidéos.

---

## **Conventions de nommage des colonnes**

### **Surrogate Keys**

- Toutes les clés primaires des tables `core` doivent utiliser le suffixe `_key`.
- **`<entity>_key`**
  - `<entity>` : Nom de la table ou de l'objet métier auquel appartient la clé.
  - Exemple : `channel_key` → surrogate key dans `dim_channel`.

### **Business Keys**

- Les identifiants naturels provenant du système source utilisent le suffixe `_id`.
- **`<entity>_id`**
  - Exemple : `video_id` → Identifiant natif YouTube d'une vidéo (chaîne de 11 caractères).
  - Exemple : `channel_id` → Identifiant natif YouTube d'une chaîne (chaîne de 24 caractères).

### **Colonnes techniques**

- Toutes les colonnes techniques doivent commencer par le préfixe `dwh_`, suivi d'un nom descriptif indiquant leur rôle.
- **`dwh_<column_name>`**
  - `dwh` : Préfixe réservé aux métadonnées générées par le système.
  - `<column_name>` : Nom descriptif indiquant le rôle de la colonne.

| Colonne          | Type          | Description                                                      | Utilisé dans                                                   |
|------------------|---------------|------------------------------------------------------------------|----------------------------------------------------------------|
| `dwh_loaded_at`  | `TIMESTAMPTZ` | Timestamp d'insertion initiale de la ligne                       | `dim_channel`, `dim_video`, `fct_video_daily_snapshot`         |
| `dwh_updated_at` | `TIMESTAMPTZ` | Timestamp de la dernière mise à jour (`ON CONFLICT DO UPDATE`)   | `dim_channel`, `dim_video`                                     |

### **Boolean Flags**

- Les colonnes booléennes doivent commencer par le préfixe `is_`.
- **`is_<state>`**
  - Exemple : `is_active` → indique si une vidéo est actuellement suivie (flag de soft delete).

### **Colonnes Soft Delete**

Les soft deletes sont gérés avec deux colonnes dédiées dans `dim_video` :

| Colonne      | Type          | Description                                          |
|--------------|---------------|------------------------------------------------------|
| `is_active`  | `BOOLEAN`     | `TRUE` si la vidéo est encore suivie                 |
| `deleted_at` | `TIMESTAMPTZ` | Timestamp auquel la vidéo a été marquée comme inactive |

---

## **Conventions de nommage des fichiers**

> Les fichiers de configuration avec des noms imposés par l'industrie (`Dockerfile`, `docker-compose.yaml`, `pyproject.toml`, `.env`) ne sont pas couverts ici — leurs noms sont dictés par les outils qui les utilisent.

### **Fichiers SQL**

| Modèle                       | Rôle                                                    | Exemple                               |
|------------------------------|---------------------------------------------------------|---------------------------------------|
| `ddl_<schema>.sql`           | Création des schemas et tables (DDL)                    | `ddl_core.sql`, `ddl_staging.sql`     |
| `dml_<entity>.sql`           | Chargement et transformations des données (DML)         | `dml_core.sql`, `dml_soft_delete.sql` |
| `alter_<schema>.sql`         | Migrations de colonnes ou de schemas (ALTER TABLE)      | `alter_core.sql`                      |
| `mart_<domain>_<metric>.sql` | Définition d'une table mart (CREATE AS SELECT)          | `mart_channel_top_views.sql`          |

### **Fichiers Python**

| Modèle                     | Rôle                                                              | Exemple                                    |
|----------------------------|-------------------------------------------------------------------|--------------------------------------------|
| `<noun>.py`                | Module source — nommé d'après sa responsabilité                   | `client.py`, `loader.py`, `extractor.py`   |
| `<source>_<type>_dag.py`   | DAG Airflow — préfixé par le système source et le type de pipeline | `yt_elt_dag.py`                           |
| `test_<module>.py`         | Test unitaire — miroir du module testé                            | `test_loader.py`, `test_client.py`         |

### **Fichiers Soda**

| Modèle                | Rôle                                                         | Exemple                                   |
|-----------------------|--------------------------------------------------------------|-------------------------------------------|
| `checks_<schema>.yml` | Contrôles qualité des données, limités à une couche du schema | `checks_core.yml`, `checks_staging.yml`   |
| `configuration.yml`   | Configuration de connexion Soda (fichier unique)             | `configuration.yml`                       |

### **Fichiers Template**

| Modèle               | Rôle                                             | Exemple                                      |
|----------------------|--------------------------------------------------|----------------------------------------------|
| `email_<event>.html` | Template d'e-mail de notification par événement  | `email_failure.html`, `email_success.html`   |
