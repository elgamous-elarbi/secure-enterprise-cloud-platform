"""
Module d'authentification et de contrôle d'accès basé sur les rôles.

Deux rôles :
- "admin"   : accès complet (création, modification, suppression, export)
- "lecteur" : consultation seule (aucune route de modification ne lui est
              accessible, même en tapant l'URL directement)

Les comptes sont stockés dans data/utilisateurs.json, mots de passe hashés
(werkzeug.security — inclus avec Flask, aucune dépendance supplémentaire).
"""
from functools import wraps
from flask import redirect, url_for, flash, abort
from flask_login import LoginManager, UserMixin, current_user
from werkzeug.security import check_password_hash
from data_source import db

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Merci de vous connecter pour accéder au référentiel."
login_manager.login_message_category = "info"


class Utilisateur(UserMixin):
    """Adaptateur Flask-Login autour d'une entrée data/utilisateurs.json."""

    def __init__(self, data):
        self.data = data

    def get_id(self):
        return self.data["id"]

    @property
    def identifiant(self):
        return self.data["identifiant"]

    @property
    def nom_affiche(self):
        return self.data["nom_affiche"]

    @property
    def role(self):
        return self.data["role"]

    @property
    def is_admin(self):
        return self.role == "admin"


def init_login(app):
    login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    data = db.get_by_id("utilisateurs", user_id)
    return Utilisateur(data) if data else None


def verifier_identifiants(identifiant, mot_de_passe):
    """Retourne l'Utilisateur si les identifiants sont valides, sinon None."""
    for u in db.get_all("utilisateurs"):
        if u["identifiant"] == identifiant:
            if check_password_hash(u["mot_de_passe_hash"], mot_de_passe):
                return Utilisateur(u)
            return None
    return None


def admin_required(view_func):
    """
    Protège une route en écriture : accessible aux seuls comptes "admin".
    Un compte "lecteur" authentifié reçoit une 403 (Accès refusé), pas une
    redirection silencieuse — pour que la restriction soit visible et
    explicable en soutenance.
    """
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("login"))
        if not current_user.is_admin:
            abort(403)
        return view_func(*args, **kwargs)
    return wrapped
