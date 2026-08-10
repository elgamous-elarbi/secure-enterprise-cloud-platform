# Secure Enterprise Cloud Platform

## Description

Application web de suivi des risques cyber (actifs, menaces, vulnérabilités,
mesures, registre) construite pour le projet PFA (PAM + ISO 27001, Medi 1 TV),
avec hébergement cloud sécurisé sur AWS — projet conçu pour apprendre le
Cloud Engineering, le DevOps et l'Infrastructure as Code.

## Technologies

- AWS
- Docker
- Kubernetes
- Terraform
- GitHub Actions
- Prometheus
- Grafana
- PostgreSQL

## Author

El Arbi Elgamous

## Status

🚧 In Progress

## Lancer l'application

```bash
pip install -r requirements.txt
python3 app.py
```

Puis ouvrir : http://localhost:5000

## Comptes de connexion (démo)

Deux comptes de démo sont créés à l'initialisation (`admin` / `auditeur`).
Voir `data/utilisateurs.json` en local — mots de passe hashés
(`werkzeug.security`), jamais commités en clair.

## Structure du projet

## Méthode de calcul (DGSSI simplifiée)

- Probabilité : Faible (1) / Moyenne (2) / Élevée (3)
- Impact : Faible (1) / Moyen (2) / Élevé (3) / Critique (4)
- Score = Probabilité × Impact
- Niveau : Faible (1-2) / Moyen (3-4) / Élevé (6-8) / Critique (9-12)

## Points à savoir avant la démo

- Les risques présents dans le registre reprennent les scénarios
  réellement traités pendant le stage (isolation réseau, MFA,
  chiffrement des secrets, SPOF du bastion, etc.) — à citer tels quels
  dans le mémoire.
- Le formulaire d'ajout d'actif est volontairement générique (pas de
  notion de "serveur PAM" en dur) pour illustrer la réutilisabilité de
  l'outil au-delà du périmètre du stage.
- L'export CSV du registre (`/registre/export.csv`) est prêt à être
  joint en annexe du mémoire.