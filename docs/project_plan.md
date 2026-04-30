# Plan de projet — ELT Pipeline

> Feuille de route d'implémentation. Les phases reflètent l'ordre de développement idéal : conception → fondations → développement couche par couche → orchestration → livraison.

---

## Phase I — Conception

### 1. Périmètre & Exigences

- [ ] Lire et comprendre le cahier des charges (`requirements.md`)
- [ ] Identifier la source de données et ses contraintes (quota, pagination, endpoints)
- [ ] Définir la stratégie de rafraîchissement des données
- [ ] Valider la faisabilité technique

### 2. Architecture & Modélisation

- [ ] Définir le flux de données de bout en bout et créer un diagramme d'architecture
- [ ] Choisir l'architecture en couches et définir le rôle de chaque couche
- [ ] Choisir le modèle de données pour le core
- [ ] Définir les tables du core et leur grain
- [ ] Définir le pattern de gestion des suppressions
- [ ] Définir la stratégie de chargement par couche
- [ ] Définir les conventions de nommage (schémas, tables, colonnes, fichiers)
- [ ] Documenter les conventions dans `docs/naming_conventions.md`

---

## Phase II — Fondations

### 3. Mise en place du projet & outillage

- [ ] Créer le dépôt GitHub public
- [ ] Initialiser le repo local et le lier au remote
- [ ] Créer `.gitignore`
- [ ] Créer `.env.example` et `.env`
- [ ] Épingler la version Python
- [ ] Initialiser le gestionnaire de dépendances et le lockfile
- [ ] Ajouter les dépendances de production
- [ ] Ajouter les dépendances de développement
- [ ] Configurer le linter et le formateur Python
- [ ] Configurer le linter SQL
- [ ] Configurer pytest et les markers de test
- [ ] Créer la structure de dossiers du projet
- [ ] Vérifier la chaîne d'outils localement

### 4. CI/CD (GitHub Actions)

- [ ] Créer le workflow CI déclenché sur push et pull request
- [ ] Configurer les étapes : lint Python, format check, lint SQL, tests unitaires
- [ ] Valider que le workflow est vert avant tout code métier
- [ ] Ajouter un badge de statut CI dans le README

### 5. Infrastructure locale (Docker Compose)

- [ ] Créer le `Dockerfile`
- [ ] Créer `.dockerignore`
- [ ] Créer `docker-compose.yaml` avec les services nécessaires et leurs healthchecks
- [ ] Définir les volumes nommés pour les services stateful
- [ ] Vérifier le stack : `docker compose up -d`, `docker compose ps`
- [ ] Vérifier chaque service accessible (Airflow, MinIO, Metabase, Postgres)

---

## Phase III — Développement

### 6. Source de données — Exploration & Extraction

- [ ] Créer les credentials d'accès à l'API et les stocker dans `.env`
- [ ] Lire la documentation officielle des endpoints utilisés
- [ ] Tester les endpoints avec un client HTTP (Postman ou équivalent)
- [ ] Cartographier la chaîne d'extraction complète
- [ ] Valider le coût en quota par exécution
- [ ] Définir la liste statique des entités à extraire
- [ ] Implémenter le client HTTP avec gestion des erreurs et retry
- [ ] Implémenter l'extracteur par entité et l'extracteur global
- [ ] Ajouter des logs structurés
- [ ] Écrire les tests unitaires (client + extracteur)
- [ ] Valider la couverture de tests

### 7. Couche de stockage brut

- [ ] Implémenter la classe de lecture/écriture vers le stockage objet
- [ ] Écrire les tests unitaires
- [ ] Vérifier manuellement le round-trip écriture → lecture

### 8. Schémas de base de données (DDL)

- [ ] Implémenter le DDL staging (schéma + table)
- [ ] Implémenter le DDL core (schéma + dimensions + table de faits + index)
- [ ] Implémenter le DDL marts (schéma uniquement)
- [ ] Valider l'idempotence de chaque DDL
- [ ] Valider le lint SQL

### 9. Chargement staging

- [ ] Implémenter le client base de données
- [ ] Implémenter le loader staging (truncate + insert dans une transaction)
- [ ] Écrire les tests unitaires

### 10. Transformations core & Soft Delete

- [ ] Implémenter le DML core (upserts dimensions + insert faits)
- [ ] Implémenter le DML soft delete
- [ ] Valider l'idempotence
- [ ] Valider le lint SQL

### 11. Marts

- [ ] Implémenter chaque mart (pattern DROP + CREATE TABLE AS SELECT)
  - [ ] `mart_channel_top_views`
  - [ ] `mart_channel_top_subscribers`
  - [ ] `mart_channel_top_likes_rate`
  - [ ] `mart_channel_size_distribution`
  - [ ] `mart_channel_subscribers_vs_engagement`
  - [ ] `mart_channel_latest_videos`
  - [ ] `mart_channel_engagement_active`
  - [ ] `mart_channel_retention`
  - [ ] `mart_video_top_views`
  - [ ] `mart_video_format_engagement`
- [ ] Valider le lint SQL

### 12. Qualité des données (Soda Core)

- [ ] Créer la configuration de la datasource
- [ ] Créer les checks staging (volume, nulls, doublons)
- [ ] Créer les checks core (cardinalités, invariants métier, fraîcheur)
- [ ] Créer les checks marts (row count, bornes des scores)
- [ ] Valider chaque suite de checks localement avec la CLI Soda

---

## Phase IV — Orchestration & Validation

### 13. DAG Airflow

- [ ] Créer le DAG avec le schedule, le timeout et les tags
- [ ] Configurer `default_args` (retries, délai, backoff, timeout par tâche)
- [ ] Implémenter chaque tâche et groupe de tâches, y compris les tâches de quality check Soda
- [ ] Câbler les dépendances dans l'ordre correct
- [ ] Créer les templates HTML pour les notifications email (succès et échec)
- [ ] Configurer les notifications email sur le DAG et sur les tâches
- [ ] Créer la connexion `postgres_elt` dans l'interface Airflow
- [ ] Créer la connexion `smtp_default`
- [ ] Créer les Variables Airflow pour les secrets
- [ ] Déclencher le DAG manuellement et confirmer que toutes les tâches sont vertes

### 14. Tests d'intégration

- [ ] Créer la base de données ou le schéma de test dédié
- [ ] Définir les fixtures pytest (engine, création/suppression des schémas, seed de données)
- [ ] Écrire les tests d'intégration : loader, upserts core, soft delete, marts
- [ ] Exécuter les tests d'intégration localement
- [ ] Décider si les tests d'intégration sont inclus ou exclus de la CI

### 15. Validation end-to-end

- [ ] Vider l'entrepôt et le stockage objet
- [ ] Déclencher le DAG sur une date fraîche et vérifier toutes les tâches
- [ ] Vérifier les comptages dans chaque couche
- [ ] Re-déclencher sur la même date et confirmer l'idempotence
- [ ] Simuler un échec et vérifier la réception de l'email d'alerte
- [ ] Vérifier la réception de l'email de succès

---

## Phase V — Livraison

### 16. Visualisation (Metabase)

- [ ] Configurer la connexion Metabase vers l'entrepôt
- [ ] Vérifier que les marts sont détectés
- [ ] Construire les dashboards sur les données réelles
- [ ] Valider que chaque carte s'affiche sans erreur

### 17. Documentation

- [ ] Rédiger `README.md` (français) : pitch, architecture, stack, démarrage rapide, modèle de données, structure du dépôt, badge CI
- [ ] Rédiger `README_en.md` (anglais, synthétique)
- [ ] Documenter les décisions architecturales dans `docs/decisions.md`
- [ ] Documenter le runbook opérationnel
- [ ] Ajouter des captures d'écran (Airflow, Metabase, MinIO)
- [ ] Documenter ce qui est hors périmètre (roadmap)

---

## Définition de Done

Le projet est terminé lorsque chacun des points suivants est vérifié :

- [ ] `git clone` + `.env` renseigné + `docker compose up -d` → stack entier healthy, sans intervention manuelle
- [ ] `docker compose ps` : tous les services healthy
- [ ] Airflow, MinIO, Metabase et Postgres accessibles
- [ ] Connexions et Variables Airflow configurées
- [ ] Déclenchement manuel du DAG → toutes les tâches vertes, y compris les 3 portes qualité Soda
- [ ] Comptages corrects dans `dim_channel`, `dim_video`, `fct_video_daily_snapshot`
- [ ] Re-déclenchement sur la même date → idempotence confirmée
- [ ] Chaque mart a `row_count > 0` et les checks de bornes passent
- [ ] Email d'échec et email de succès reçus
- [ ] `pytest tests/unit/` vert
- [ ] `pytest -m integration` vert
- [ ] `ruff check` et `ruff format --check` verts
- [ ] `sqlfluff lint sql/` vert
- [ ] GitHub Actions CI vert sur master
- [ ] Metabase : tous les dashboards affichés sans erreur
- [ ] `README.md` complet
