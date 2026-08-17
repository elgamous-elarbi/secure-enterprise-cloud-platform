"""
Couche d'abstraction des données.

Aujourd'hui : lecture/écriture sur des fichiers JSON locaux (data/*.json).
Demain : bascule vers Google Sheets API en remplaçant uniquement les
méthodes _read() et _write() de la classe JSONDataSource ci-dessous —
le reste de l'application (routes Flask, moteur de risque) n'a pas
à changer, car il ne connaît que l'interface DataSource.
"""

import json
import os
from datetime import date
from abc import ABC, abstractmethod

from dotenv import load_dotenv

load_dotenv()  # lit .env s'il existe (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class DataSource(ABC):
    """Interface commune. Toute source de données (JSON, Sheets, DB...)
    doit implémenter ces méthodes pour être utilisable par l'application."""

    @abstractmethod
    def get_all(self, collection):
        ...

    @abstractmethod
    def get_by_id(self, collection, item_id):
        ...

    @abstractmethod
    def add(self, collection, item):
        ...

    @abstractmethod
    def update(self, collection, item_id, item):
        ...

    @abstractmethod
    def delete(self, collection, item_id):
        ...


class JSONDataSource(DataSource):
    """Implémentation locale sur fichiers JSON. Une collection = un fichier."""

    COLLECTIONS = ("actifs", "menaces", "vulnerabilites", "mesures", "risques", "processus", "informations", "utilisateurs")

    def _path(self, collection):
        if collection not in self.COLLECTIONS:
            raise ValueError(f"Collection inconnue : {collection}")
        return os.path.join(DATA_DIR, f"{collection}.json")

    def _read(self, collection):
        path = self._path(collection)
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, collection, data):
        path = self._path(collection)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_all(self, collection):
        return self._read(collection)

    def get_by_id(self, collection, item_id):
        for item in self._read(collection):
            if item.get("id") == item_id:
                return item
        return None

    def _next_id(self, collection, prefix):
        items = self._read(collection)
        existing_nums = []
        for item in items:
            item_id = item.get("id", "")
            if item_id.startswith(prefix):
                try:
                    existing_nums.append(int(item_id[len(prefix):]))
                except ValueError:
                    pass
        next_num = max(existing_nums, default=0) + 1
        return f"{prefix}{next_num}"

    def add(self, collection, item):
        prefix_map = {
            "actifs": "A", "menaces": "M", "vulnerabilites": "V",
            "mesures": "S", "risques": "R", "processus": "P", "informations": "I",
            "utilisateurs": "U"
        }
        items = self._read(collection)
        if "id" not in item or not item["id"]:
            item["id"] = self._next_id(collection, prefix_map[collection])
        if collection == "actifs" and "date_ajout" not in item:
            item["date_ajout"] = date.today().isoformat()
        items.append(item)
        self._write(collection, items)
        return item

    def update(self, collection, item_id, item):
        items = self._read(collection)
        for i, existing in enumerate(items):
            if existing.get("id") == item_id:
                item["id"] = item_id
                items[i] = item
                self._write(collection, items)
                return item
        return None

    def delete(self, collection, item_id):
        items = self._read(collection)
        filtered = [i for i in items if i.get("id") != item_id]
        if len(filtered) == len(items):
            return False
        self._write(collection, filtered)
        return True


# Point d'entrée unique utilisé par app.py.
#
# Bascule PostgreSQL (juillet 2026) : l'app utilise désormais SQLDataSource,
# qui respecte exactement la même interface DataSource que JSONDataSource
# ci-dessus. JSONDataSource est conservée dans ce fichier à titre de
# référence / repli (utile en soutenance pour expliquer la démarche), mais
# n'est plus l'implémentation active.
#
# Configuration de connexion via variables d'environnement (voir .env.example
# et README.md) : DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD.
#
# Pour revenir temporairement aux fichiers JSON (ex : démo hors-ligne sans
# base disponible), remplacer la ligne ci-dessous par : db = JSONDataSource()
from sql_data_source import SQLDataSource  # noqa: E402

db = SQLDataSource()
