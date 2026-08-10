"""
Tests du moteur de risque (risk_engine.py).

Volontairement limites aux fonctions pures (aucune dependance a la base de
donnees) : c'est ce qui permet de les lancer n'importe ou (poste local, CI
GitHub Actions) sans avoir besoin d'un Postgres demarre a cote.

Lancer avec :
    pytest tests/ -v
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import risk_engine


def test_score_risque_minimum():
    assert risk_engine.score_risque("Faible", "Faible") == 1


def test_score_risque_maximum():
    assert risk_engine.score_risque("Élevée", "Critique") == 12


def test_score_risque_valeur_inconnue_retombe_sur_faible():
    assert risk_engine.score_risque("Inconnu", "Inconnu") == 1


def test_niveau_risque_faible():
    assert risk_engine.niveau_risque("Faible", "Faible") == "Faible"
    assert risk_engine.niveau_risque("Faible", "Moyen") == "Faible"


def test_niveau_risque_moyen():
    assert risk_engine.niveau_risque("Moyenne", "Moyen") == "Moyen"


def test_niveau_risque_eleve():
    assert risk_engine.niveau_risque("Moyenne", "Élevé") == "Élevé"


def test_niveau_risque_critique():
    assert risk_engine.niveau_risque("Élevée", "Critique") == "Critique"
    assert risk_engine.niveau_risque("Élevée", "Élevé") == "Critique"


def test_niveau_risque_bornes_exactes():
    assert risk_engine.niveau_risque("Moyenne", "Faible") == "Faible"
    assert risk_engine.niveau_risque("Élevée", "Faible") == "Moyen"
    assert risk_engine.niveau_risque("Élevée", "Moyen") == "Élevé"


def test_couleur_niveau_connu():
    assert risk_engine.couleur_niveau("Critique") != ""
    assert risk_engine.couleur_niveau("Faible") != ""


def test_couleur_niveau_inconnu_ne_plante_pas():
    resultat = risk_engine.couleur_niveau("Valeur qui n'existe pas")
    assert isinstance(resultat, str)