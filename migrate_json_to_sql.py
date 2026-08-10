"""
Migration unique des données data/*.json vers la base PostgreSQL.

Usage :
    python migrate_json_to_sql.py

Prérequis : la base doit déjà exister et schema.sql doit avoir été exécuté
(voir README pour les commandes exactes).

Ce script est idempotent dans la mesure du raisonnable : il vide les tables
avant de réinsérer (TRUNCATE ... CASCADE), donc on peut le relancer sans
craindre les doublons. À utiliser une seule fois pour la migration initiale,
ou pour resynchroniser la base depuis les JSON si besoin de repartir de zéro.
"""

import json
import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Ordre important : les tables filles doivent être vidées avant/avec CASCADE
# des tables parentes. TRUNCATE ... CASCADE gère les tables de jonction
# automatiquement, donc on truncate tout d'un coup dans le bon sens.
TABLES_ORDRE_TRUNCATE = [
    "risques_mesures", "processus_actifs_support",
    "risques", "informations", "processus",
    "mesures", "vulnerabilites", "menaces", "actifs", "utilisateurs",
]

# collection JSON -> (table, colonnes simples, champs liste -> table de jonction)
COLLECTIONS = {
    "utilisateurs": ("utilisateurs", ["id", "identifiant", "nom_affiche", "mot_de_passe_hash", "role"], {}),
    "actifs": ("actifs", ["id", "nom", "type", "service_it", "proprietaire", "criticite", "description", "date_ajout"], {}),
    "menaces": ("menaces", ["id", "categorie", "libelle", "description"], {}),
    "vulnerabilites": ("vulnerabilites", ["id", "categorie", "libelle", "description"], {}),
    "mesures": ("mesures", ["id", "libelle", "type", "description"], {}),
    "processus": (
        "processus",
        ["id", "bloc", "nom", "description", "dic_disponibilite", "dic_integrite", "dic_confidentialite"],
        {"actifs_support_ids": ("processus_actifs_support", "processus_id", "actif_id")},
    ),
    "informations": ("informations", ["id", "processus_id", "nom", "description", "dic_disponibilite", "dic_integrite", "dic_confidentialite"], {}),
    "risques": (
        "risques",
        ["id", "actif_id", "menace_id", "vulnerabilite_id", "probabilite", "impact", "description_scenario", "statut", "commentaire"],
        {"mesures_appliquees": ("risques_mesures", "risque_id", "mesure_id")},
    ),
}

# processus référence informations.id (information_id) : colonne ajoutée
# après coup, une fois que la ligne informations existe.
PROCESSUS_INFORMATION_ID_APRES_COUP = True


def connect():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME", "dgssi_app"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", ""),
    )


def load_json(collection):
    path = os.path.join(DATA_DIR, f"{collection}.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    conn = connect()
    conn.autocommit = False
    cur = conn.cursor()

    print("→ Nettoyage des tables existantes (TRUNCATE ... CASCADE)...")
    cur.execute(f"TRUNCATE TABLE {', '.join(TABLES_ORDRE_TRUNCATE)} CASCADE")

    totaux = {}

    # 1) utilisateurs, actifs, menaces, vulnerabilites, mesures (aucune dépendance)
    for collection in ["utilisateurs", "actifs", "menaces", "vulnerabilites", "mesures"]:
        table, cols, _ = COLLECTIONS[collection]
        items = load_json(collection)
        for item in items:
            values = [item.get(c) for c in cols]
            placeholders = ", ".join(["%s"] * len(cols))
            cur.execute(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})", values)
        totaux[collection] = len(items)
        print(f"  {collection}: {len(items)} lignes insérées")

    # 2) processus SANS information_id d'abord (informations n'existe pas encore)
    processus_items = load_json("processus")
    table, cols, list_fields = COLLECTIONS["processus"]
    for item in processus_items:
        values = [item.get(c) for c in cols]
        placeholders = ", ".join(["%s"] * len(cols))
        cur.execute(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})", values)
    print(f"  processus: {len(processus_items)} lignes insérées (sans information_id pour l'instant)")

    # 3) informations (référence processus.id, qui existe maintenant)
    informations_items = load_json("informations")
    table, cols, _ = COLLECTIONS["informations"]
    for item in informations_items:
        values = [item.get(c) for c in cols]
        placeholders = ", ".join(["%s"] * len(cols))
        cur.execute(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})", values)
    totaux["informations"] = len(informations_items)
    print(f"  informations: {len(informations_items)} lignes insérées")

    # 4) mise à jour de processus.information_id maintenant que informations existe
    for item in processus_items:
        info_id = item.get("information_id")
        if info_id:
            cur.execute("UPDATE processus SET information_id = %s WHERE id = %s", (info_id, item["id"]))
    totaux["processus"] = len(processus_items)

    # 5) table de jonction processus_actifs_support
    for item in processus_items:
        for actif_id in item.get("actifs_support_ids", []):
            cur.execute(
                "INSERT INTO processus_actifs_support (processus_id, actif_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (item["id"], actif_id),
            )

    # 6) risques + table de jonction risques_mesures
    risques_items = load_json("risques")
    table, cols, _ = COLLECTIONS["risques"]
    for item in risques_items:
        values = [item.get(c) for c in cols]
        placeholders = ", ".join(["%s"] * len(cols))
        cur.execute(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})", values)
        for mesure_id in item.get("mesures_appliquees", []):
            cur.execute(
                "INSERT INTO risques_mesures (risque_id, mesure_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (item["id"], mesure_id),
            )
    totaux["risques"] = len(risques_items)
    print(f"  risques: {len(risques_items)} lignes insérées")

    conn.commit()
    cur.close()
    conn.close()

    print("\n✅ Migration terminée avec succès.")
    print("Récapitulatif :", totaux)


if __name__ == "__main__":
    main()
