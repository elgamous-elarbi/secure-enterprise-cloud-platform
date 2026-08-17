"""
Implémentation PostgreSQL de l'interface DataSource (cf. data_source.py).

Remplace JSONDataSource sans que app.py, risk_engine.py, auth.py ou les
templates n'aient à changer : ils ne connaissent que l'interface commune
get_all / get_by_id / add / update / delete.

Connexion configurée via variables d'environnement (voir .env.example) :
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
"""

import os
from datetime import date

import psycopg2
import psycopg2.extras
from psycopg2 import pool

from data_source import DataSource


# ----------------------------------------------------------------------
# Configuration déclarative des collections : table SQL, colonnes simples,
# et champs "liste" adossés à une table de jonction (relations n-n).
# ----------------------------------------------------------------------
COLLECTIONS_CONFIG = {
    "actifs": {
        "table": "actifs",
        "columns": ["id", "nom", "type", "service_it", "proprietaire", "criticite", "description", "date_ajout"],
        "id_prefix": "A",
    },
    "menaces": {
        "table": "menaces",
        "columns": ["id", "categorie", "libelle", "description"],
        "id_prefix": "M",
    },
    "vulnerabilites": {
        "table": "vulnerabilites",
        "columns": ["id", "categorie", "libelle", "description"],
        "id_prefix": "V",
    },
    "mesures": {
        "table": "mesures",
        "columns": ["id", "libelle", "type", "description"],
        "id_prefix": "S",
    },
    "informations": {
        "table": "informations",
        "columns": ["id", "processus_id", "nom", "description", "dic_disponibilite", "dic_integrite", "dic_confidentialite"],
        "id_prefix": "I",
    },
    "processus": {
        "table": "processus",
        "columns": ["id", "bloc", "nom", "description", "dic_disponibilite", "dic_integrite", "dic_confidentialite", "information_id"],
        "id_prefix": "P",
        "list_fields": {
            "actifs_support_ids": {"junction": "processus_actifs_support", "this": "processus_id", "other": "actif_id"},
        },
    },
    "risques": {
        "table": "risques",
        "columns": ["id", "actif_id", "menace_id", "vulnerabilite_id", "probabilite", "impact", "description_scenario", "statut", "commentaire"],
        "id_prefix": "R",
        "list_fields": {
            "mesures_appliquees": {"junction": "risques_mesures", "this": "risque_id", "other": "mesure_id"},
        },
    },
    "utilisateurs": {
        "table": "utilisateurs",
        "columns": ["id", "identifiant", "nom_affiche", "mot_de_passe_hash", "role"],
        "id_prefix": "U",
    },
}


class SQLDataSource(DataSource):
    """Implémentation PostgreSQL. Une collection = une table (+ tables de
    jonction pour les champs qui sont des listes d'ids)."""

    def __init__(self, host=None, port=None, dbname=None, user=None, password=None, minconn=1, maxconn=5):
        self._pool = psycopg2.pool.SimpleConnectionPool(
            minconn, maxconn,
            host=host or os.environ.get("DB_HOST", "localhost"),
            port=port or os.environ.get("DB_PORT", "5432"),
            dbname=dbname or os.environ.get("DB_NAME", "dgssi_app"),
            user=user or os.environ.get("DB_USER", "postgres"),
            password=password or os.environ.get("DB_PASSWORD", ""),
        )

    # ---------- gestion de connexion ----------

    def _get_conn(self):
        return self._pool.getconn()

    def _put_conn(self, conn):
        self._pool.putconn(conn)

    def close(self):
        self._pool.closeall()

    # ---------- config helper ----------

    def _config(self, collection):
        if collection not in COLLECTIONS_CONFIG:
            raise ValueError(f"Collection inconnue : {collection}")
        return COLLECTIONS_CONFIG[collection]

    # ---------- lecture des champs "liste" (tables de jonction) ----------

    def _attach_list_fields(self, cur, collection, rows):
        """Ajoute à chaque dict de `rows` les champs listes (ex :
        actifs_support_ids, mesures_appliquees) en interrogeant les tables
        de jonction correspondantes."""
        cfg = self._config(collection)
        list_fields = cfg.get("list_fields", {})
        if not list_fields or not rows:
            return rows

        ids = [r["id"] for r in rows]
        for field_name, jcfg in list_fields.items():
            mapping = {i: [] for i in ids}
            cur.execute(
                f"SELECT {jcfg['this']}, {jcfg['other']} FROM {jcfg['junction']} "
                f"WHERE {jcfg['this']} = ANY(%s)",
                (ids,),
            )
            for this_id, other_id in cur.fetchall():
                mapping.setdefault(this_id, []).append(other_id)
            for r in rows:
                r[field_name] = mapping.get(r["id"], [])
        return rows

    def _set_list_fields(self, cur, collection, item_id, item):
        """Remplace le contenu des tables de jonction pour cet item, à
        partir des listes présentes dans `item` (add/update)."""
        cfg = self._config(collection)
        for field_name, jcfg in cfg.get("list_fields", {}).items():
            cur.execute(f"DELETE FROM {jcfg['junction']} WHERE {jcfg['this']} = %s", (item_id,))
            values = item.get(field_name) or []
            for other_id in values:
                cur.execute(
                    f"INSERT INTO {jcfg['junction']} ({jcfg['this']}, {jcfg['other']}) "
                    f"VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (item_id, other_id),
                )

    # ---------- interface DataSource ----------

    def get_all(self, collection):
        cfg = self._config(collection)
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(f"SELECT * FROM {cfg['table']} ORDER BY id")
                rows = [dict(r) for r in cur.fetchall()]
                rows = self._normalize_dates(rows)
                self._attach_list_fields(cur, collection, rows)
            return rows
        finally:
            self._put_conn(conn)

    def get_by_id(self, collection, item_id):
        cfg = self._config(collection)
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(f"SELECT * FROM {cfg['table']} WHERE id = %s", (item_id,))
                row = cur.fetchone()
                if not row:
                    return None
                row = dict(row)
                row = self._normalize_dates([row])[0]
                self._attach_list_fields(cur, collection, [row])
            return row
        finally:
            self._put_conn(conn)

    def _normalize_dates(self, rows):
        """psycopg2 renvoie les colonnes DATE en objets `date` Python ;
        l'app (JSON à l'origine) attend des chaînes ISO ('2026-07-01')."""
        for r in rows:
            for k, v in r.items():
                if isinstance(v, date):
                    r[k] = v.isoformat()
        return rows

    def _next_id(self, cur, collection):
        cfg = self._config(collection)
        prefix = cfg["id_prefix"]
        cur.execute(f"SELECT id FROM {cfg['table']}")
        existing_nums = []
        for (item_id,) in cur.fetchall():
            if item_id.startswith(prefix):
                try:
                    existing_nums.append(int(item_id[len(prefix):]))
                except ValueError:
                    pass
        next_num = max(existing_nums, default=0) + 1
        return f"{prefix}{next_num}"

    def add(self, collection, item):
        cfg = self._config(collection)
        item = dict(item)  # ne pas modifier l'original en place
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                if not item.get("id"):
                    item["id"] = self._next_id(cur, collection)
                if collection == "actifs" and not item.get("date_ajout"):
                    item["date_ajout"] = date.today().isoformat()

                cols = cfg["columns"]
                values = [item.get(c) for c in cols]
                placeholders = ", ".join(["%s"] * len(cols))
                cur.execute(
                    f"INSERT INTO {cfg['table']} ({', '.join(cols)}) VALUES ({placeholders})",
                    values,
                )
                self._set_list_fields(cur, collection, item["id"], item)
            conn.commit()
            return item
        except Exception:
            conn.rollback()
            raise
        finally:
            self._put_conn(conn)

    def update(self, collection, item_id, item):
        cfg = self._config(collection)
        item = dict(item)
        item["id"] = item_id
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(f"SELECT 1 FROM {cfg['table']} WHERE id = %s", (item_id,))
                if not cur.fetchone():
                    return None

                cols = [c for c in cfg["columns"] if c != "id"]
                set_clause = ", ".join(f"{c} = %s" for c in cols)
                values = [item.get(c) for c in cols] + [item_id]
                cur.execute(
                    f"UPDATE {cfg['table']} SET {set_clause} WHERE id = %s",
                    values,
                )
                self._set_list_fields(cur, collection, item_id, item)
            conn.commit()
            return item
        except Exception:
            conn.rollback()
            raise
        finally:
            self._put_conn(conn)

    def delete(self, collection, item_id):
        cfg = self._config(collection)
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(f"DELETE FROM {cfg['table']} WHERE id = %s", (item_id,))
                deleted = cur.rowcount > 0
            conn.commit()
            return deleted
        except Exception:
            conn.rollback()
            raise
        finally:
            self._put_conn(conn)
