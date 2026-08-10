# Guide de démarrage — Application DGSSI (édition PostgreSQL)

Ce guide explique comment installer et lancer l'application de gestion des risques sur un **nouvel ordinateur**, à partir de zéro.

---

## 1. Prérequis à installer

| Outil | Pourquoi | Où le télécharger |
|---|---|---|
| **Python 3.10+** | Fait tourner l'application Flask | https://www.python.org/downloads/ |
| **PostgreSQL 14+** | Base de données de l'application | https://www.postgresql.org/download/ |
| **pgAdmin 4** (optionnel mais recommandé) | Interface graphique pour vérifier la base | https://www.pgadmin.org/download/ |

Pendant l'installation de PostgreSQL, **note bien le mot de passe** que tu définis pour l'utilisateur `postgres` — il sera redemandé plus loin.

---

## 2. Récupérer les fichiers de l'application

1. Copie le dossier complet de l'application (ou décompresse le zip) sur le nouvel ordinateur, par exemple dans :
   ```
   C:\Users\<toi>\Documents\dgssi-app
   ```
2. Ouvre un terminal (`cmd` ou PowerShell) **dans ce dossier** — vérifie que tu es au bon endroit :
   ```bash
   dir
   ```
   Tu dois voir `app.py`, `requirements.txt`, `schema.sql`, `migrate_json_to_sql.py`, `.env.example`, et les dossiers `data/`, `templates/`, `static/`.

---

## 3. Créer un environnement virtuel Python (recommandé)

Ça évite que les dépendances de ce projet entrent en conflit avec d'autres projets Python sur la machine.

```bash
python -m venv venv
```

Active-le :

- **Windows (cmd)** :
  ```bash
  venv\Scripts\activate
  ```
- **Windows (PowerShell)** :
  ```powershell
  venv\Scripts\Activate.ps1
  ```

Ton terminal doit maintenant afficher `(venv)` au début de la ligne.

---

## 4. Installer les dépendances Python

```bash
pip install -r requirements.txt
```

Si `requirements.txt` n'est pas présent ou incomplet, installe manuellement :

```bash
pip install flask psycopg2-binary python-dotenv reportlab
```

---

## 5. Créer la base de données PostgreSQL

Ouvre **pgAdmin 4** (ou l'invite `psql` en ligne de commande), connecte-toi au serveur PostgreSQL local, puis crée une nouvelle base de données vide :

**Via pgAdmin** : clic droit sur *Databases* → *Create* → *Database...* → nomme-la par exemple `dgssi_risques`.

**Via psql** :
```bash
psql -U postgres
```
puis, dans l'invite `psql` :
```sql
CREATE DATABASE dgssi_risques;
\q
```

---

## 6. Configurer la connexion à la base (fichier `.env`)

Dans le dossier de l'application, duplique le fichier d'exemple :

```bash
copy .env.example .env
```
*(sous Linux/Mac : `cp .env.example .env`)*

Ouvre `.env` avec un éditeur de texte et renseigne tes propres valeurs :

```ini
DB_HOST=localhost
DB_PORT=5432
DB_NAME=dgssi_risques
DB_USER=postgres
DB_PASSWORD=ton_mot_de_passe_postgres
```

---

## 7. Créer les tables (exécuter le schéma SQL)

```bash
psql -U postgres -d dgssi_risques -f schema.sql
```

Ça crée toutes les tables (actifs, menaces, vulnérabilités, mesures, risques, processus, informations, utilisateurs) avec leurs clés étrangères.

---

## 8. Importer les données existantes (migration JSON → PostgreSQL)

Si tu pars des données déjà préparées (fichiers JSON dans `data/`) :

```bash
python migrate_json_to_sql.py
```

Ce script lit les fichiers JSON du dossier `data/` et les insère dans la base PostgreSQL fraîchement créée. Il gère notamment le lien croisé entre processus et informations.

---

## 9. Lancer l'application

```bash
python app.py
```

Le terminal doit afficher quelque chose comme :
```
Running on http://127.0.0.1:5000
```

---

## 10. Ouvrir l'application dans le navigateur

Va sur : **http://localhost:5000**

Connecte-toi avec un compte existant (Administrateur ou Lecteur), créé lors de la migration ou directement en base.

---

## Dépannage — problèmes fréquents

| Symptôme | Cause probable | Solution |
|---|---|---|
| `ModuleNotFoundError: No module named 'flask'` | Dépendances non installées, ou environnement virtuel non activé | Relance `pip install -r requirements.txt` après avoir activé `venv` |
| `psycopg2.OperationalError: could not connect to server` | PostgreSQL n'est pas démarré, ou mauvais port/hôte dans `.env` | Vérifie que le service PostgreSQL tourne (Services Windows, ou `pg_ctl status`) |
| `FATAL: password authentication failed for user "postgres"` | Mauvais mot de passe dans `.env` | Corrige `DB_PASSWORD` dans le fichier `.env` |
| `relation "actifs" does not exist` | Le schéma SQL n'a pas été exécuté | Relance l'étape 7 (`psql -f schema.sql`) |
| Page blanche ou erreur 500 au lancement | Table vide (pas de migration faite) | Relance l'étape 8 (`python migrate_json_to_sql.py`) |
| `python` non reconnu | Python non ajouté au PATH à l'installation | Réinstalle Python en cochant "Add Python to PATH", ou utilise `python3` |

---

## Vérification rapide que tout fonctionne

Une fois l'application lancée, vérifie dans l'ordre :

1. **Dashboard** (`/`) : doit afficher les statistiques (nombre d'actifs, de processus, de risques)
2. **Actifs** (`/actifs`) : la liste doit être peuplée si la migration a réussi
3. **Registre** (`/registre`) : doit lister les risques, avec export CSV fonctionnel
4. **Export PDF** du dashboard : doit télécharger un fichier PDF sans erreur

Si les quatre points fonctionnent, l'installation est complète et opérationnelle.
