# Runbook opérationnel

Ce document est un **mode d'emploi** simple pour opérer le pipeline ELT YouTube au quotidien.

---

## Table des matières

1. [Démarrage initial](#1-démarrage-initial)
2. [Ajouter une nouvelle chaîne](#3-ajouter-une-nouvelle-chaîne)
3. [Arrêter ou réinitialiser le pipeline](#8-arrêter-ou-réinitialiser-le-pipeline)

---

## 1. Démarrage initial

**Quand l'utiliser :** premier lancement du projet.

### 1.1. Prérequis

- Docker Desktop.
- Une clé API YouTube Data v3 active.
- Un compte SMTP pour les notifications (Gmail avec mot de passe d'application convient).

### 1.2. Préparer le fichier `.env`

```bash
cp .env.example .env
```

Modifier `.env` :

- `YOUTUBE_API_KEY` — clé API YouTube.
- `AIRFLOW_FERNET_KEY` — génère avec (pour la rotation lire la documentation officielle Airflow, c'est important) :
  ```bash
  uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
- `AIRFLOW__API__SECRET_KEY` — génère avec `openssl rand -base64 32`.
- `AIRFLOW_API_AUTH_JWT_SECRET` — génère avec `openssl rand -base64 64`.

Les autres variables (utilisateurs/mots de passe Postgres, MinIO, Metabase) peuvent rester avec leurs valeurs par défaut
pour un environnement local.

### 1.3. Démarrer

```bash
docker compose up -d --build
```

Le premier démarrage prend 2 à 5 minutes.

### 1.4. Vérifier que les services sont healthy

```bash
docker compose ps
```

**Vérification :**

| Conteneur               | URL d'accès           | État attendu              |
|-------------------------|-----------------------|---------------------------|
| `pg_elt`                | localhost:5432        | healthy                   |
| `pg_airflow`            | localhost:5433        | healthy                   |
| `pg_metabase`           | localhost:5434        | healthy                   |
| `airflow_api_server`    | http://localhost:8080 | running                   |
| `airflow_scheduler`     | —                     | running                   |
| `airflow_dag_processor` | —                     | running                   |
| `minio`                 | http://localhost:9001 | healthy                   |
| `metabase`              | http://localhost:3000 | running                   |
| `airflow_init`          | —                     | exited (0) — c'est normal |
| `minio_init`            | —                     | exited (0) — c'est normal |

### 1.5. Configurer Airflow

Airflow UI sur http://localhost:8080 avec les credentials par défaut : le login et le mot de passe se trouvent dans
le fichier simple_auth_manager_passwords.json.generated à la racine du projet.

**Crée les Variables Airflow**:

| Variable           | Valeur             |
|--------------------|--------------------|
| `YOUTUBE_API_KEY`  | clé API YouTube    |
| `MINIO_ENDPOINT`   | identique à `.env` |
| `MINIO_ACCESS_KEY` | identique à `.env` |
| `MINIO_SECRET_KEY` | identique à `.env` |
| `MINIO_BUCKET`     | identique à `.env` |

**Crée les Connections Airflow** :

| Conn ID        | Type     | Host               | Schema             | Login              | Password                   | Port               |
|----------------|----------|--------------------|--------------------|--------------------|----------------------------|--------------------|
| `postgres_elt` | Postgres | identique à `.env` | identique à `.env` | identique à `.env` | identique à `.env`         | identique à `.env` |
| `smtp_default` | SMTP     | `smtp.gmail.com`   | —                  | adresse email      | mot de passe d'application | `587`              |

### 1.6. Premier déclenchement du DAG

1. Dans Airflow, activer `yt_elt_pipeline` car il est en pause par défaut.
2. Trigger DAG.

**Vérification :** au bout de **2 à 5 minutes**, toutes les tâches doivent être vertes dans la vue Graph et ensuite email avec "Success". Vérifier également la base de données.

Si on déclenche plusieurs runs dans la même journée, le pipeline est idempotent : extract_to_s3 réécrit le JSON du jour, le staging est tronqué+rechargé, le core fait des UPSERT, les marts sont reconstruits, les diagrammes sont mis à jour.

### 1.7. Configurer Metabase

1. Ouvrir **http://localhost:3000**.
2. Crée le compte.
3. **Add database** → Postgres :
    - Display name : choisir
    - Host : identique à `.env`
    - Port : identique à `.env`
    - Database name : identique à `.env`
    - Username / Password : identique à `.env`
4. Une fois la base ajoutée, Metabase introspecte automatiquement les schémas. Les marts apparaissent sous
   `pg_elt → marts`.
---

## 2. Ajouter une nouvelle chaîne

1. Récupérer le `channel_id` Youtube
2. Ajouter à [`src/youtube/channels.py`](../src/youtube/channels.py)

```python
{"channel_id": "UCxxxxxxxxxxxxxxxxxxxxxx", "channel_name": "Nom Affiché"},
```
Aucun rebuild n'est nécessaire parce que ./src est monté en volume (bind mount Airflow)

## 3. Arrêter ou réinitialiser le pipeline

Arrêter et conserver les données.
```bash
docker compose down
```


Arrêter et supprimer les données (reset complet).

```bash
docker compose down -v
```