# Décisions d'architecture et d'ingénierie

Ce document consigne les choix techniques non évidents faits sur ce projet. Chaque entrée suit la même structure : **Décision** (ce qui a été choisi), **Contexte** (la contrainte ou la question), **Raisonnement** (pourquoi ce choix), **Approche alternative** (ce qui a été écarté et pourquoi — uniquement pour les choix de paradigme), **Compromis** (ce à quoi on renonce).

Les détails d'exécution purs (quelle bibliothèque gère le HTTP, comment une fonction est nommée) ne sont pas consignés ici. Seuls les choix qu'un autre ingénieur pourrait légitimement questionner sont documentés.

---

## 1. Stack & Outillage

### D1 — PostgreSQL comme warehouse analytique

- **Décision :** Utiliser PostgreSQL 17 comme unique warehouse relationnel pour les couches staging, core et marts.
- **Contexte :** Le projet nécessite un warehouse SQL capable de supporter des upserts quotidiens, des jointures, des fonctions fenêtre et des agrégations analytiques sur des dizaines de milliers de lignes.
- **Raisonnement :** Postgres couvre toutes les exigences du projet (fonctions fenêtre, `ON CONFLICT`, arithmétique `INTERVAL`, index partiels, colonnes générées) sans coût de licence et s'exécute nativement dans Docker. Les volumes concernés (~15k vidéos, ~40 chaînes, snapshots quotidiens) sont bien en dessous du seuil où un warehouse colonnaire ferait une différence.
- **Compromis :** Une charge OLAP réelle à grande échelle bénéficierait du stockage colonnaire. La migration vers un moteur colonnaire reste simple car le SQL demeure portable.

---

### D2 — MinIO à la place d'un S3 cloud réel pour la couche raw

- **Décision :** Utiliser MinIO comme object store auto-hébergé, compatible S3, pour les fichiers JSON bruts.
- **Contexte :** Le pipeline nécessite une couche raw immuable, replayable et découplée du warehouse. AWS S3 est la cible production-réaliste.
- **Raisonnement :** MinIO parle exactement la même API boto3 qu'AWS S3. Le code écrit pour MinIO est portable bit-à-bit vers S3 — seule l'URL du endpoint change. L'exécution locale ne coûte rien, ne requiert pas de credentials cloud et s'intègre dans Docker Compose. Le code de la couche raw est donc production-réaliste sans la facture cloud.
- **Approche alternative :**
  - Système de fichiers local — plus simple, mais rompt l'abstraction "object storage" et nécessiterait une réécriture pour un déploiement cloud.
  - AWS S3 réel — production-réaliste mais ajoute des coûts, la gestion des credentials, et empêche une reproduction entièrement locale.
- **Compromis :** Pas d'exposition aux comportements cloud spécifiques (cohérence éventuelle, IAM, règles de cycle de vie). Documenté comme hors périmètre.

---

### D3 — Apache Airflow 3.x avec LocalExecutor

- **Décision :** Utiliser Airflow 3.x avec le LocalExecutor pour l'orchestration.
- **Contexte :** Le pipeline exécute un seul DAG une fois par jour avec ~15 tâches séquentielles ou groupées. Un parallélisme important, une exécution distribuée et une haute concurrence ne sont pas nécessaires.
- **Raisonnement :** Airflow est l'orchestrateur de référence qu'un Data Engineer est attendu à maîtriser. Le LocalExecutor exécute les tâches comme des sous-processus sur le même hôte — suffisant pour un DAG quotidien, sans Redis ni Celery à opérer. Airflow 3 apporte les décorateurs modernes `@dag` / `@task`, les TaskGroups, et la séparation API server / scheduler / dag-processor.
- **Compromis :** Le LocalExecutor ne peut pas scaler horizontalement. Acceptable pour le volume du projet ; documenté comme un choix de périmètre délibéré.

---

### D4 — Soda Core pour la qualité des données

- **Décision :** Utiliser Soda Core (bibliothèque Python) pour les contrôles automatisés de qualité des données, déclarés en YAML et invoqués depuis les tâches Airflow.
- **Contexte :** Chaque couche du warehouse doit avoir une porte de qualité bloquante avant que la couche suivante ne s'exécute. Les contrôles doivent être lisibles, versionnables et faciles à étendre.
- **Raisonnement :** La syntaxe YAML de Soda Core exprime les contrôles les plus courants (nombre de lignes, taux de nulls/doublons, bornes de valeurs) de façon déclarative. Des contrôles SQL personnalisés restent possibles pour les invariants métier complexes (`likes <= views`, ratio aujourd'hui/hier). La bibliothèque s'exécute en in-process — aucun service externe à déployer, aucun container supplémentaire.
- **Compromis :** L'édition open-source de Soda Core manque des fonctionnalités de lineage et de reporting de Soda Cloud. Suffisant pour ce périmètre.

---

### D5 — Metabase comme couche BI

- **Décision :** Utiliser Metabase, connecté directement au schema marts dans `pg_elt`.
- **Contexte :** Les marts doivent être exposés dans des dashboards interactifs sur des données réelles du pipeline, principalement à des fins de démonstration.
- **Raisonnement :** Metabase introspècte automatiquement les schemas Postgres, ne nécessite aucune configuration pour afficher des dashboards, s'exécute dans un seul container et stocke ses propres métadonnées dans une instance Postgres dédiée. C'est la façon la moins coûteuse en effort d'exposer les marts visuellement pour une démo portfolio.
- **Compromis :** Les définitions de dashboards Metabase sont stockées dans sa propre base de données et ne sont pas versionnées dans Git par défaut. Acceptable pour une couche de démonstration.

---

### D6 — Trois instances PostgreSQL physiquement séparées

- **Décision :** Faire tourner trois containers Postgres : `pg_elt` (données du warehouse), `pg_airflow` (métadonnées Airflow), `pg_metabase` (métadonnées Metabase).
- **Contexte :** Airflow et Metabase nécessitent tous les deux un backend Postgres pour leur état interne.
- **Raisonnement :** Isoler les métadonnées de chaque système des données du warehouse évite la contamination croisée, permet des politiques de backup/restore indépendantes, et correspond à ce à quoi ressemblerait un déploiement production réel. Un Postgres partagé unique couplerait des cycles de vie sans rapport (une migration du warehouse pourrait perturber Airflow).
- **Approche alternative :**
  - Un seul Postgres avec trois bases de données — possible mais couple le démarrage, les mises à niveau de version et le dimensionnement des ressources de systèmes sans rapport.
  - SQLite pour les métadonnées Airflow — officiellement déprécié par Airflow pour tout usage non-trivial ; incompatible avec LocalExecutor.
- **Compromis :** Trois containers Postgres consomment plus de mémoire qu'un seul. Acceptable sur un laptop de développeur ; le gain en isolation le justifie.

---

### D7 — Docker Compose pour la stack locale

- **Décision :** Définir l'ensemble de la stack dans un seul `docker-compose.yaml` avec des YAML anchors.
- **Contexte :** Un relecteur ou recruteur doit pouvoir cloner le dépôt et lancer le projet de bout en bout avec une seule commande.
- **Raisonnement :** Compose orchestre les 9 services (3 Postgres, MinIO + init, 3 services Airflow + init, Metabase) avec des healthchecks, des volumes nommés et un ordonnancement explicite des dépendances. Les YAML anchors dédupliquent les blocs build/env/volumes/depends-on partagés par Airflow. La reproductibilité est la fonctionnalité principale pour un projet portfolio.
- **Compromis :** Compose est un outil d'orchestration locale, pas un outil de déploiement production. Le README documente cela comme une limite de périmètre connue.

---

### D8 — uv pour la gestion des dépendances Python

- **Décision :** Utiliser `uv` (`pyproject.toml` + `uv.lock`) à la place de pip / poetry / pipenv.
- **Contexte :** Le projet nécessite une résolution déterministe des dépendances pour les groupes production et dev, ainsi que des installations rapides en CI.
- **Raisonnement :** `uv` est significativement plus rapide que pip (basé sur Rust), produit un `uv.lock` déterministe, supporte les groupes de dépendances nativement, et s'impose comme le standard moderne. L'étape d'installation en CI est nettement plus courte, ce qui se cumule sur l'ensemble des runs.
- **Compromis :** `uv` est plus récent que les alternatives ; certaines intégrations IDE rattrapent encore leur retard. Acceptable.

---

### D9 — `requests` + `urllib3.Retry` pour le client API

- **Décision :** Construire un client léger sur `requests.Session` avec `urllib3.Retry` pour l'API YouTube.
- **Contexte :** L'API YouTube Data peut throttler (429) ou échouer de façon transitoire (5xx). Le client doit retry de façon intelligente.
- **Raisonnement :** Une `Session` réutilise les connexions TCP, et `urllib3.Retry` gère les codes 429/5xx avec un backoff exponentiel en ~10 lignes de configuration. Écrire un client léger permet de garder le code minimal, transparent et facile à mocker en tests unitaires.
- **Compromis :** Le client personnalisé ne supporte que les trois endpoints utilisés. Hors périmètre.

---

### D10 — `pandas.to_sql` pour le chargement en staging

- **Décision :** Utiliser `pandas.DataFrame.to_sql` (avec `method="multi"`, `chunksize=500`) dans une transaction SQLAlchemy pour le chargement en staging.
- **Contexte :** La table staging reçoit un TRUNCATE + un bulk insert complet par run.
- **Raisonnement :** `pandas` est déjà dans l'arbre de dépendances et est bien maîtrisé. `to_sql` avec `method="multi"` produit des instructions INSERT multi-lignes, ce qui est suffisant pour les volumes concernés (~15k lignes). Le TRUNCATE + INSERT s'exécute dans une seule transaction, donc la table staging n'est jamais vide en cours de run.
- **Compromis :** Au-delà de quelques centaines de milliers de lignes par chargement, `COPY` serait mesurable plus rapide. Documenté comme une limite de passage à l'échelle.

---

### D11 — ruff et sqlfluff pour le linting et le formatage

- **Décision :** Utiliser ruff pour Python (lint + format) et sqlfluff pour SQL.
- **Contexte :** La qualité du code doit être appliquée de façon cohérente en CI.
- **Raisonnement :** ruff remplace flake8 + isort + black en un seul outil rapide, configuré entièrement dans `pyproject.toml`. sqlfluff lint l'ensemble de l'arbre SQL (y compris le DML Jinja-templated) et impose une capitalisation, un aliasing et des virgules finales cohérents. Les deux sont suffisamment rapides pour s'exécuter à chaque build CI.
- **Compromis :** Le Jinja templater de sqlfluff nécessite un contexte placeholder dans `pyproject.toml` ; inconvénient mineur.

---

## 2. Architecture

### D12 — ELT plutôt qu'ETL

- **Décision :** Atterrir les données brutes en premier, puis transformer à l'intérieur du warehouse avec SQL.
- **Contexte :** Deux patterns sont possibles : transformer puis charger (ETL — nettoyer en Python avant stockage) ou charger puis transformer (ELT — stocker d'abord, transformer en SQL).
- **Raisonnement :** Stocker le JSON brut immédiatement rend le pipeline **replayable** : n'importe quel jour passé peut être retraité depuis le fichier brut sans toucher à l'API ni brûler du quota. Pousser les transformations dans SQL les rend auditables, versionnées, et exécutables indépendamment de Python — un Data Analyst peut reproduire un mart avec une seule commande `psql`. Les warehouses modernes (et même Postgres à cette échelle) traitent les jointures/agrégations plus vite que des pipelines pandas équivalents.
- **Approche alternative :**
  - ETL — transformations Python avant stockage. Perd la replayabilité des données brutes et intègre la logique métier dans du code plus difficile à auditer que SQL.
- **Compromis :** L'ELT nécessite une destination capable de SQL. C'est déjà le cas ici.

---

### D13 — Trois couches SQL (staging → core → marts) plus un raw lake

- **Décision :** Utiliser quatre couches physiques : object storage raw, schema staging, schema core, schema marts.
- **Contexte :** Une seule table dénormalisée cible est la solution la plus simple mais confond les responsabilités. Une architecture multi-couches sépare l'ingestion, la modélisation et l'agrégation.
- **Raisonnement :** Chaque couche a une responsabilité et une stratégie de chargement uniques. Le staging est un miroir TRUNCATE+INSERT — robuste aux dérives de schéma dans l'API. Le core est la source de vérité typée et dédupliquée — la seule couche avec de l'intégrité référentielle. Les marts sont des agrégats jetables — reconstruits quotidiennement, jamais la source de vérité. Les pannes sont isolées : un mart corrompu peut être reconstruit depuis le core ; un core corrompu peut être reconstruit depuis le raw.
- **Approche alternative :**
  - API directe → table unique — plus rapide à implémenter, aucune isolation entre les responsabilités, difficile à déboguer.
  - Deux couches (raw + marts) — saute la source de vérité typée ; chaque mart ré-implémente la déduplication et le casting.
- **Compromis :** Plus de tables à maintenir. La convention se justifie dès la première fois qu'un bug doit être tracé d'un dashboard jusqu'à l'API.

---

### D14 — Star schema (Kimball) pour la couche core

- **Décision :** Modéliser le core en deux dimensions (`dim_channel`, `dim_video`) et une table de faits (`fct_video_daily_snapshot`).
- **Contexte :** Un modèle normalisé (3NF) et un star schema sont tous les deux viables.
- **Raisonnement :** Le star schema est le pattern dominant pour les warehouses analytiques. Il réduit le nombre de jointures par requête analytique, simplifie les plans de requête, et est le modèle pour lequel les outils BI (Metabase, Superset, Tableau) sont optimisés. La granularité est sans ambiguïté : une ligne par `(vidéo, snapshot_date)` dans la table de faits.
- **Approche alternative :**
  - Modèle 3NF normalisé — réduit la redondance dans les dimensions mais multiplie les jointures pour chaque requête analytique.
  - One Big Table — plus rapide à requêter, mais la redondance et les anomalies de mise à jour la rendent impossible à maintenir au-delà des projets jouets.
- **Compromis :** Les star schemas dupliquent les attributs des dimensions. Acceptable ; les cardinalités des dimensions sont minuscules.

---

### D15 — Full refresh plutôt que chargements incrémentaux

- **Décision :** TRUNCATE+INSERT pour le staging ; UPSERT pour les dimensions core ; INSERT-with-conflict-update pour la table de faits core ; DROP+CREATE pour les marts.
- **Contexte :** Le traitement incrémental (seulement les lignes modifiées) est le choix textbook efficace ; le full refresh est le choix textbook simple.
- **Raisonnement :** À ~15k vidéos et ~40 chaînes, un full refresh s'exécute en quelques secondes. L'idempotence est automatique — ré-exécuter la même date écrase les mêmes lignes. Pas de table watermark, pas de logique high-water-mark, pas de récupération de "run manqué". Le pipeline est trivialement replayable depuis n'importe quel fichier raw passé.
- **Approche alternative :**
  - Chargement incrémental par watermark — nécessaire pour des volumes bien plus importants ; sur-complexe ici et source fréquente de bugs.
  - Append-only avec déduplication à la lecture — reporte la complexité de l'écriture vers la lecture ; mauvais pour les outils BI qui ne dédupliquent pas.
- **Compromis :** Du compute est gaspillé à retraiter des lignes inchangées. À ce volume, négligeable. Documenté comme une limite de passage à l'échelle.

---

### D16 — JSON plutôt que Parquet pour la couche raw

- **Décision :** Persister les extraits bruts comme fichiers JSON (un par jour) dans l'object store.
- **Contexte :** Deux formats sont courants pour les raw lakes : JSON orienté lignes ou Parquet colonnaire.
- **Raisonnement :** L'API YouTube retourne du JSON nativement. Stocker la réponse brute telle quelle préserve une fidélité parfaite — aucune interprétation de schéma à la frontière, aucun risque de perdre des champs imbriqués. Les fichiers sont lus une seule fois par jour pour charger le staging ; les performances de scan colonnaire sont sans pertinence à ce volume. Le JSON est aussi lisible par un humain, ce qui facilite le débogage.
- **Approche alternative :**
  - Parquet — colonnaire, compressé, schéma imposé. Ajoute une étape de sérialisation, nécessite de s'engager sur un schéma à l'écriture, rompt le principe "le raw est exactement ce que l'API a retourné".
  - JSON compressé (gzip) — réduirait le stockage, mais les volumes sont suffisamment faibles pour que la compression ajoute de la complexité sans bénéfice réel.
- **Compromis :** Parquet serait le bon choix à l'échelle de millions d'enregistrements par jour. Documenté comme une limite de passage à l'échelle.

---

## 3. Modélisation des données

### D17 — SCD Type 1 sur les dimensions

- **Décision :** Écraser les attributs des dimensions en cas de conflit (`channel_name`, `subscribers_count`, `title`, `duration_seconds`). Aucun historique n'est conservé sur les dimensions.
- **Contexte :** Slowly Changing Dimensions Type 1 (écrasement) versus Type 2 (historique avec valid_from / valid_to).
- **Raisonnement :** Les questions métier nécessitent uniquement l'état **courant** de chaque chaîne et vidéo. Une chaîne renommée ou un titre mis à jour ne casse pas l'analytique historique — les lignes de faits restent ancrées à la surrogate key. Le SCD Type 2 ajouterait les colonnes `valid_from`, `valid_to`, `is_current` et un pattern d'upsert plus complexe, pour une valeur analytique qu'aucun mart n'utilise réellement.
- **Approche alternative :**
  - SCD Type 2 — préserve l'historique des dimensions mais ajoute de la complexité et du stockage sans consommateur.
  - SCD Type 0 (ne jamais mettre à jour) — gèlerait définitivement les noms de chaînes obsolètes.
- **Compromis :** Perte de la capacité à répondre "comment s'appelait cette chaîne il y a 6 mois ?". Pas un besoin métier actuel ; peut être ajouté sur `dim_channel` plus tard sans toucher à la table de faits.

---

### D18 — Soft delete sur `dim_video`, jamais de hard delete

- **Décision :** Marquer les vidéos absentes de l'extrait du jour comme `is_active = FALSE` avec `deleted_at = NOW()`. Ne jamais faire de `DELETE` dans `dim_video`.
- **Contexte :** Des vidéos peuvent disparaître d'une chaîne (supprimées par le créateur, rendues privées, retirées par YouTube). Le pipeline doit en rendre compte.
- **Raisonnement :** Un hard delete dans `dim_video` orpheliserait toutes les lignes de faits historiques référençant cette vidéo, cassant les foreign keys et effaçant les analytics passés. Le soft delete préserve l'intégrité référentielle, permet aux requêtes de marts historiques de résoudre les jointures `dim_video`, et supporte la réactivation si une vidéo réapparaît (`is_active = TRUE`, `deleted_at = NULL` au prochain upsert). Un index partiel sur `WHERE is_active = FALSE` maintient les requêtes de soft delete rapides.
- **Approche alternative :**
  - Hard delete — détruit les analytics historiques, casse les foreign keys.
  - Pas de suppression — les lignes de faits s'accumulent indéfiniment pour des vidéos qui n'existent plus ; les métriques sur le "catalogue actif" deviennent bruitées.
- **Compromis :** `dim_video` croît de façon monotone. À la cardinalité YouTube de ce projet, c'est négligeable.

---

### D19 — Grain daily snapshot sur la table de faits, historique conservé

- **Décision :** La table de faits a une ligne par `(vidéo, snapshot_date)`. Clé primaire composite `(video_key, snapshot_date)`. L'historique s'accumule jour après jour.
- **Contexte :** La table de faits pourrait être cumulative (une ligne par vidéo, écrasée quotidiennement — seul "aujourd'hui" est queryable) ou snapshot (une ligne par vidéo par jour — chaque jour passé est queryable).
- **Raisonnement :** Les snapshots quotidiens sont le seul modèle qui supporte les questions métier "comment l'engagement a-t-il évolué dans le temps" et "quelles vidéos ont perdu des vues entre deux jours". Un fait cumulatif effacerait toute l'évolution historique. Stocker une ligne par vidéo par jour à cette échelle (~15k vidéos × N jours) est peu coûteux.
- **Approche alternative :**
  - Fait cumulatif (écrasement par vidéo) — perd toute analyse temporelle.
  - Journal d'événements append-only (une ligne par changement de métrique) — granularité plus fine que nécessaire, plus difficile à requêter pour les agrégats quotidiens.
- **Compromis :** Le stockage croît linéairement dans le temps. Négligeable à ce volume ; documenté comme une limite de passage à l'échelle.

---

### D20 — Surrogate keys (`SERIAL`) sur les dimensions

- **Décision :** Chaque dimension a une surrogate key `SERIAL` (`channel_key`, `video_key`) ; les natural keys (`channel_id`, `video_id`) sont conservées comme colonnes `UNIQUE`.
- **Contexte :** Les jointures peuvent utiliser soit la natural key (TEXT) soit une surrogate key générée (INT).
- **Raisonnement :** Les jointures INT sont plus rapides que les jointures TEXT et produisent des index plus petits. Les surrogates isolent aussi le schéma des changements de clés en amont (si YouTube migrait un jour le format des identifiants de chaîne). Conserver la natural key en `UNIQUE` permet à la logique d'upsert d'identifier les lignes depuis les données source.
- **Approche alternative :**
  - Natural keys comme PK — fonctionne, mais jointures plus lentes et couplage fort à la stratégie de clés du système source.
  - UUIDs comme surrogates — distribution aléatoire qui nuit à la localité des index, empreinte de clé plus large, aucun avantage dans un Postgres mono-instance.
- **Compromis :** Les surrogates nécessitent que la logique d'upsert fasse une jointure contre la dimension pour résoudre la foreign key. Le coût est une recherche indexée ; trivial à cette échelle.

---

## 4. Opérations

### D21 — Idempotence par conception sur toutes les couches

- **Décision :** La stratégie de chargement de chaque couche (TRUNCATE+INSERT, UPSERT with conflict, INSERT with conflict-update on composite key, DROP+CREATE) est choisie de façon à ce que ré-exécuter le pipeline sur la même date produise un état identique.
- **Contexte :** Les pipelines échouent. Les contrôles qualité bloquent des runs. Les opérateurs re-déclenchent. Le pipeline doit tolérer les retries sans produire de doublons ni d'état partiel.
- **Raisonnement :** L'idempotence élimine des classes entières de bugs : pas de nettoyage manuel après les pannes, pas de travail de détective "ce DAG a-t-il tourné aujourd'hui ?", pas de lignes de faits dupliquées suite à des re-déclenchements accidentels. Combinée avec la replayabilité de la couche raw, n'importe quel jour passé peut être retraité en toute sécurité depuis le JSON original.
- **Approche alternative :**
  - Append-only avec déduplication en aval — reporte la complexité vers chaque consommateur.
  - Verrouillage manuel / flags "is_running" — fragile, contourne la sémantique de retry d'Airflow.
- **Compromis :** Certaines stratégies idempotentes (DROP+CREATE sur les marts) sont coûteuses à grande échelle. Acceptable ici.

---

### D22 — Contrôles qualité comme portes bloquantes dans le DAG

- **Décision :** Les contrôles Soda s'exécutent comme tâches Airflow après chaque couche du warehouse. Un contrôle échoué lève une `ValueError` et interrompt le run.
- **Contexte :** Les contrôles qualité peuvent s'exécuter en mode **bloquant** (faire échouer le DAG) ou **non-bloquant** (logger des avertissements uniquement).
- **Raisonnement :** Un contrôle d'intégrité échoué signifie presque toujours des données corrompues. Laisser cela se propager vers les marts et les dashboards est pire qu'un run échoué. Les portes bloquantes surfacent le problème immédiatement, passent par la notification d'échec SMTP standard, et empêchent les parties prenantes de voir des chiffres erronés. Le coût d'un faux positif (run légitime bloqué) est bien plus faible que le coût d'un faux négatif (mauvaises données dans les dashboards).
- **Approche alternative :**
  - Avertissements non-bloquants — des logs que personne ne lit.
  - Contrôles qualité à la source (avant upsert) — laisserait quand même des données incorrectes entrer dans staging ; moins observable qu'une tâche dédiée.
- **Compromis :** Un contrôle instable arrête le pipeline. Mitigation : seuils de ratio (`> 0.95` plutôt que `= 1.0`) pour absorber le bruit.

---

### D23 — Notifications email SMTP en succès et en échec

- **Décision :** Configurer `SmtpNotifier` pour le `on_failure_callback` (par tâche) et le `on_success_callback` (au niveau DAG), avec des emails HTML templatés.
- **Contexte :** Les résultats du pipeline nécessitent un canal push à faible friction.
- **Raisonnement :** L'email est universel, ne nécessite pas d'infrastructure supplémentaire, et arrive là où les opérateurs se trouvent déjà. Un email d'échec remonte immédiatement les incidents ; un email de succès fonctionne comme un heartbeat quotidien (un email de succès manquant est lui-même un signal). Les templates HTML produisent des notifications lisibles et bien présentées. Le callback d'échec par tâche permet d'identifier directement la tâche défaillante.
- **Compromis :** Le volume d'emails (un succès par jour + des échecs occasionnels) est confortable. Les credentials SMTP doivent être configurés comme une connexion Airflow.

---

### D24 — Secrets via les Variables et Connexions Airflow, jamais en dur dans les DAGs

- **Décision :** Stocker la clé API YouTube et les credentials MinIO comme Variables Airflow ; stocker la connexion au warehouse comme Connexion Airflow (`postgres_elt`) et les credentials SMTP comme `smtp_default`.
- **Contexte :** Le code du DAG est versionné dans Git. Coder les secrets en dur est un anti-pattern connu.
- **Raisonnement :** Les Variables et Connexions Airflow sont chiffrées au repos avec la clé Fernet, gérées centralement dans l'UI, et ne sont jamais sérialisées dans le source du DAG. Faire tourner un secret signifie mettre à jour un enregistrement dans Airflow, pas patcher du code. Le fichier DAG reste sûrement committable.
- **Compromis :** Les Variables et Connexions doivent être créées manuellement après le premier `docker compose up`. Documenté dans le runbook du README.
