# Migration vers PostgreSQL — Guide d'installation

Ce document explique comment faire tourner l'application avec une vraie base
PostgreSQL au lieu des fichiers `data/*.json`. **Aucun fichier `app.py`,
`risk_engine.py`, `auth.py` ou template n'a été modifié** : seule la couche
d'accès aux données change, exactement comme prévu par l'architecture
d'origine (`data_source.py`).

## Ce qui a été ajouté

| Fichier | Rôle |
|---|---|
| `schema.sql` | Crée les tables PostgreSQL (avec vraies clés étrangères) |
| `sql_data_source.py` | Implémentation `SQLDataSource`, respecte l'interface `DataSource` |
| `migrate_json_to_sql.py` | Copie une fois tes données JSON actuelles dans PostgreSQL |
| `.env.example` | Modèle du fichier de config de connexion (à copier en `.env`) |

`data_source.py` a été modifié d'une seule ligne : `db = SQLDataSource()` au
lieu de `db = JSONDataSource()`. La classe `JSONDataSource` reste dans le
fichier, inutilisée mais gardée pour référence (utile en soutenance pour
expliquer la démarche de bascule).

## Étapes d'installation

### 1. Installer PostgreSQL (si pas déjà fait)

Sous Windows : télécharger l'installeur sur https://www.postgresql.org/download/windows/
et suivre l'assistant (retenir le mot de passe du compte `postgres`).

### 2. Créer la base et l'utilisateur

Ouvrir `psql` (ou pgAdmin) et exécuter :

```sql
CREATE DATABASE dgssi_app;
```

(Tu peux réutiliser l'utilisateur `postgres` par défaut, ou en créer un
dédié — dans ce cas adapte `.env` en conséquence.)

### 3. Créer les tables

```bash
psql -U postgres -d dgssi_app -f schema.sql
```

### 4. Installer les nouvelles dépendances Python

```bash
pip install -r requirements.txt
```

(Ajoute `psycopg2-binary` pour parler à PostgreSQL, et `python-dotenv` pour
lire le fichier `.env`.)

### 5. Configurer la connexion

```bash
copy .env.example .env
```

Puis éditer `.env` avec tes vraies valeurs (mot de passe notamment).

### 6. Migrer les données JSON existantes

```bash
python migrate_json_to_sql.py
```

Ce script vide les tables (si elles contenaient déjà quelque chose) puis
réinsère tous tes actifs, menaces, vulnérabilités, mesures, processus,
informations, risques (R1 à R11) et utilisateurs depuis les fichiers JSON
actuels. Il affiche un récapitulatif du nombre de lignes insérées par table.

### 7. Lancer l'application normalement

```bash
python app.py
```

Rien ne change côté navigateur : toutes les pages, le dashboard, l'export
PDF, l'import CSV, le CRUD des processus, tout fonctionne à l'identique —
sauf que les données vivent maintenant dans PostgreSQL au lieu des fichiers
JSON.

## Ce qui a changé "sous le capot" (utile pour le mémoire)

- **Vraies clés étrangères** : `risques.actif_id` référence désormais
  réellement `actifs.id`, etc. — la base garantit l'intégrité référentielle,
  ce que les fichiers JSON ne faisaient pas.
- **Relations n-n en tables de jonction** : les listes d'ids qui vivaient
  dans un champ JSON (`processus.actifs_support_ids`,
  `risques.mesures_appliquees`) sont maintenant des tables de jonction
  classiques (`processus_actifs_support`, `risques_mesures`) — modélisation
  standard d'une relation many-to-many en base relationnelle.
- **Suppression cohérente** : supprimer un actif ne supprime pas les
  risques qui le référencent (ils restent dans le registre, avec un actif
  "manquant"), comportement identique à l'ancienne version JSON.
- **Pool de connexions** (`psycopg2.pool.SimpleConnectionPool`) plutôt
  qu'une connexion par requête HTTP, pour éviter d'ouvrir/fermer une
  connexion PostgreSQL à chaque clic.

## Revenir aux fichiers JSON (dépannage / démo hors-ligne)

Dans `data_source.py`, remplacer la dernière ligne :

```python
db = SQLDataSource()
```

par :

```python
db = JSONDataSource()
```

Les fichiers `data/*.json` n'ont pas été touchés, donc ce retour arrière
est immédiat et sans perte.

## ⚠️ Limite de cet environnement de développement

Ce travail a été écrit et relu avec soin (schéma cohérent avec les JSON
réels de ton app, interface respectée, code compilé sans erreur), mais je
n'ai pas pu lancer un vrai serveur PostgreSQL dans cet environnement pour
tester la connexion de bout en bout (pas d'accès réseau ici). Teste donc les
étapes ci-dessus chez toi avant la soutenance, et dis-moi si tu rencontres
une erreur — je pourrai la corriger directement.
