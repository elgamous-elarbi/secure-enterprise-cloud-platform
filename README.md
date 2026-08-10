# Référentiel de gestion des risques — Méthode DGSSI

Application web de suivi des risques cyber (actifs, menaces, vulnérabilités,
mesures, registre) construite pour le projet PFA (PAM + ISO 27001, Medi 1 TV).

## Lancer l'application

```bash
pip install -r requirements.txt
python3 app.py
```

Puis ouvrir : http://localhost:5000

## \## Comptes de connexion (démo)

## 

## Deux comptes de démo sont créés à l'initialisation (`admin` / `auditeur`).

## Voir `data/utilisateurs.json` en local — mots de passe hashés

## (`werkzeug.security`), jamais commités en clair.Structure du projet

```
app.py              → routes Flask (dashboard, actifs, risques, registre, API)
risk\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_engine.py       → moteur de calcul du niveau de risque + recommandations
data\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_source.py       → couche d'abstraction des données (JSON aujourd'hui,
                        bascule vers Google Sheets API en changeant
                        uniquement ce fichier)
data/\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*.json           → référentiels (actifs, menaces, vulnérabilités,
                        mesures) et registre de risques pré-rempli avec
                        les scénarios réels du périmètre PAM/Wazuh
templates/\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*.html      → pages (Jinja2)
static/css/style.css  → design system (identité "régie de diffusion / SOC")
```

## Méthode de calcul (DGSSI simplifiée)

* Probabilité : Faible (1) / Moyenne (2) / Élevée (3)
* Impact : Faible (1) / Moyen (2) / Élevé (3) / Critique (4)
* Score = Probabilité × Impact
* Niveau : Faible (1-2) / Moyen (3-4) / Élevé (6-8) / Critique (9-12)

## Points à savoir avant la démo

* Les 8 risques déjà présents dans `data/risques.json` reprennent les
scénarios réellement traités pendant le stage (isolation réseau, MFA,
chiffrement des secrets, SPOF du bastion, etc.) — à citer tels quels
dans le mémoire.
* Le formulaire d'ajout d'actif est volontairement générique (pas de
notion de "serveur PAM" en dur) pour illustrer la réutilisabilité de
l'outil au-delà du périmètre du stage.
* L'export CSV du registre (`/registre/export.csv`) est prêt à être
joint en annexe du mémoire.

## Bascule vers Google Sheets (si le temps le permet)

Remplacer uniquement `data\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_source.py` par une implémentation
`SheetsDataSource` respectant la même interface (`get\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_all`, `get\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_by\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_id`,
`add`, `update`, `delete`) — aucune autre partie de l'application n'a
besoin d'être modifiée.

