from dotenv import load_dotenv
import os
import sys

# Déterminer le dossier de base (compatible PyInstaller)
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Charger les variables d'environnement (.env)
load_dotenv(os.path.join(BASE_DIR, ".env"))

from flask import Flask, render_template, request, redirect, url_for, jsonify, Response, flash
from flask_login import login_user, logout_user, login_required, current_user

from data_source import db
import risk_engine
import auth
import csv
import io
import secrets
from datetime import date, datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT

# Création de l'application Flask
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)
# Clé de session : générée aléatoirement à chaque démarrage. Suffisant pour
# un usage local/démo ; à fixer via une variable d'environnement si l'app
# devait un jour tourner sur un serveur partagé (cf. limites, doc de l'app).
# Environnement d'exécution (development / production) et niveau de log,
# pilotables sans toucher au code — utile pour différencier local/EKS.
APP_ENV = os.environ.get("APP_ENV", "development")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

import logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)

# Clé de session : DOIT être fixe et identique sur tous les pods en
# production (sinon un utilisateur est déconnecté à chaque fois que le
# load balancer le bascule sur un autre pod). En développement local,
# on retombe sur une valeur aléatoire si FLASK_SECRET_KEY n'est pas
# défini — pratique, mais jamais acceptable en production.
_secret_key = os.environ.get("FLASK_SECRET_KEY")
if not _secret_key:
    if APP_ENV == "production":
        raise RuntimeError(
            "FLASK_SECRET_KEY doit être défini en production "
            "(APP_ENV=production) — sessions non fiables sinon."
        )
    logger.warning(
        "FLASK_SECRET_KEY non défini : clé de session aléatoire générée "
        "pour ce démarrage (OK en dev local uniquement)."
    )
    _secret_key = secrets.token_hex(32)
app.secret_key = _secret_key
auth.init_login(app)
# ---------- HEALTH CHECKS (probes Kubernetes) ----------
#
# /health/live  : l'appli tourne-t-elle ? (pas de dépendance externe testée)
#                  → utilisé par livenessProbe : si ça échoue, K8s redémarre le pod.
# /health/ready : l'appli peut-elle servir du trafic ? (vérifie la DB)
#                  → utilisé par readinessProbe : si ça échoue, K8s retire le pod
#                    du Service sans le redémarrer (le temps que la DB revienne).

@app.route("/health/live")
def health_live():
    return jsonify(status="ok"), 200


@app.route("/health/ready")
def health_ready():
    try:
        conn = db._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        finally:
            db._put_conn(conn)
        return jsonify(status="ok", db="ok"), 200
    except Exception as e:
        return jsonify(status="error", db="unreachable", detail=str(e)), 503
# Listes de référence proposées dans les formulaires (l'utilisateur garde
# toujours la possibilité de saisir une valeur libre via l'option "Autre").
TYPES_ACTIFS_STANDARDS = ["Matériel", "Logiciel", "Données", "Réseau", "Personnel", "Site physique", "Service tiers"]
SERVICES_STANDARDS = ["Diffusion", "Infrastructure", "Production", "Rédaction", "Sécurité"]
BLOCS_STANDARDS = ["Production audiovisuelle", "Diffusion", "Gestion des contenus", "Information / Rédaction", "Infrastructure IT", "Cybersécurité"]
NIVEAUX_DIC = ["Faible", "Moyen", "Élevé", "Critique"]

# Statuts de traitement d'un risque — alignés sur les 4 décisions du guide
# DGSSI (§4 Traitement du risque) : Réduction, Maintien (Acceptation),
# Évitement, Transfert.
STATUTS_RISQUE = ["Réduire", "Accepter", "Éviter", "Transférer"]

# Colonnes attendues pour l'import CSV des actifs (mêmes champs que le
# formulaire manuel, dans le même ordre que le modèle téléchargeable).
CSV_ACTIFS_COLONNES = ["nom", "type", "service_it", "proprietaire", "criticite", "description"]


def get_risques_enrichis():
    risques = db.get_all("risques")
    return [risk_engine.enrichir_risque(r, db) for r in risques]


# ---------- AUTHENTIFICATION ----------

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    erreur = None
    if request.method == "POST":
        identifiant = request.form.get("identifiant", "").strip()
        mot_de_passe = request.form.get("mot_de_passe", "")
        utilisateur = auth.verifier_identifiants(identifiant, mot_de_passe)
        if utilisateur:
            login_user(utilisateur)
            suivant = request.args.get("next")
            return redirect(suivant or url_for("dashboard"))
        erreur = "Identifiant ou mot de passe incorrect."
    return render_template("login.html", erreur=erreur)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.before_request
def exiger_authentification():
    """Toutes les routes sont protégées par défaut, sauf login et les
    fichiers statiques. Centralisé ici plutôt que route par route, pour
    ne jamais risquer d'oublier un @login_required sur une nouvelle route."""
    endpoints_libres = {"login", "static", "health_live", "health_ready"}
    if request.endpoint in endpoints_libres or request.endpoint is None:
        return None
    if not current_user.is_authenticated:
        return redirect(url_for("login", next=request.path))


@app.context_processor
def injecter_utilisateur_courant():
    return {"current_user": current_user}


@app.errorhandler(403)
def acces_refuse(e):
    return render_template("403.html"), 403


@app.route("/")
def dashboard():
    risques = get_risques_enrichis()
    stats = risk_engine.stats_globales(risques)
    actifs = db.get_all("actifs")
    processus = db.get_all("processus")
    risques_tries = sorted(risques, key=lambda r: r["score"], reverse=True)
    total_risques = len(risques)
    repartition_types = risk_engine.repartition_par_type(actifs)

    ordre_niveaux = ["Critique", "Élevé", "Moyen", "Faible"]
    couleurs_niveaux = {
        "Critique": "var(--tally-red)",
        "Élevé": "var(--tally-red)",
        "Moyen": "var(--diffusion-amber)",
        "Faible": "var(--phosphor-green)",
    }
    rayon = 68
    circonference = round(2 * 3.14159265 * rayon, 2)
    cumul = 0.0
    chart_data = []
    for niveau in ordre_niveaux:
        compte = stats.get(niveau, 0)
        pct = (compte / total_risques * 100) if total_risques else 0
        portion = circonference * pct / 100
        chart_data.append({
            "niveau": niveau,
            "count": compte,
            "pct": round(pct, 1),
            "dasharray": f"{round(portion, 2)} {round(circonference - portion, 2)}",
            "dashoffset": round(-cumul, 2),
            "color": couleurs_niveaux[niveau],
        })
        cumul += portion

    return render_template(
        "dashboard.html",
        stats=stats,
        total_actifs=len(actifs),
        total_processus=len(processus),
        total_risques=total_risques,
        risques=risques_tries,
        top_risques=risques_tries[:5],
        chart_data=chart_data,
        chart_radius=rayon,
        chart_circumference=circonference,
        repartition_types=repartition_types,
    )


def _build_dashboard_pdf():
    """Construit le PDF d'export du tableau de bord (stats + registre complet).
    Utilisé par la route /export/dashboard.pdf ci-dessous."""
    risques = get_risques_enrichis()
    stats = risk_engine.stats_globales(risques)
    actifs = db.get_all("actifs")
    processus = db.get_all("processus")
    risques_tries = sorted(risques, key=lambda r: r["score"], reverse=True)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
        title="Tableau de bord — Registre des risques SSI",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitreDoc", parent=styles["Title"], fontSize=18, spaceAfter=2)
    sub_style = ParagraphStyle("SousTitre", parent=styles["Normal"], fontSize=9.5, textColor=colors.HexColor("#555555"), spaceAfter=14)
    h2_style = ParagraphStyle("H2Doc", parent=styles["Heading2"], fontSize=12.5, spaceBefore=14, spaceAfter=8, textColor=colors.HexColor("#1F4E78"))
    cell_style = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=8, leading=10)
    cell_style_bold = ParagraphStyle("CellBold", parent=cell_style, fontName="Helvetica-Bold")

    elements = []
    elements.append(Paragraph("Tableau de bord — Référentiel des risques SSI", title_style))
    elements.append(Paragraph(
        f"Export généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} — "
        f"{len(processus)} processus · {len(actifs)} actifs · {len(risques)} risques évalués",
        sub_style,
    ))

    # ---- Synthèse par niveau ----
    elements.append(Paragraph("Synthèse par niveau de risque", h2_style))
    synth_data = [["Niveau", "Nombre", "Part"]]
    total = len(risques) or 1
    for niveau in ["Critique", "Élevé", "Moyen", "Faible"]:
        count = stats.get(niveau, 0)
        synth_data.append([niveau, str(count), f"{round(count / total * 100, 1)} %"])
    synth_table = Table(synth_data, colWidths=[60 * mm, 30 * mm, 30 * mm])
    synth_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(synth_table)

    # ---- Registre complet ----
    elements.append(Paragraph("Registre des risques", h2_style))
    reg_header = ["ID", "Actif", "Scénario", "Prob.", "Impact", "Niveau", "Statut"]
    reg_data = [reg_header]
    for r in risques_tries:
        reg_data.append([
            r["id"],
            Paragraph(r["actif"]["nom"] if r["actif"] else "—", cell_style),
            Paragraph(r.get("description_scenario", ""), cell_style),
            r["probabilite"],
            r["impact"],
            r["niveau"],
            r["statut"],
        ])
    reg_table = Table(
        reg_data,
        colWidths=[14 * mm, 42 * mm, 100 * mm, 20 * mm, 20 * mm, 22 * mm, 22 * mm],
        repeatRows=1,
    )
    niveau_colors = {
        "Critique": colors.HexColor("#FFC7CE"),
        "Élevé": colors.HexColor("#FFD966"),
        "Moyen": colors.HexColor("#FFEB9C"),
        "Faible": colors.HexColor("#C6EFCE"),
    }
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for i, r in enumerate(risques_tries, start=1):
        bg = niveau_colors.get(r["niveau"])
        if bg:
            style_cmds.append(("BACKGROUND", (5, i), (5, i), bg))
    reg_table.setStyle(TableStyle(style_cmds))
    elements.append(reg_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer


@app.route("/export/dashboard.pdf")
def export_dashboard_pdf():
    buffer = _build_dashboard_pdf()
    filename = f"tableau_de_bord_risques_{date.today().isoformat()}.pdf"
    return Response(
        buffer.getvalue(),
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment;filename={filename}"},
    )


# ---------- PROCESSUS (biens essentiels) ----------

@app.route("/processus")
def processus_list():
    processus = db.get_all("processus")
    blocs = []
    for p in processus:
        if p["bloc"] not in blocs:
            blocs.append(p["bloc"])
    return render_template("processus.html", processus=processus, blocs=blocs)


@app.route("/processus/<processus_id>")
def processus_detail(processus_id):
    p = db.get_by_id("processus", processus_id)
    if not p:
        return redirect(url_for("processus_list"))
    information = db.get_by_id("informations", p.get("information_id"))
    actifs_support = [db.get_by_id("actifs", aid) for aid in p.get("actifs_support_ids", [])]
    actifs_support = [a for a in actifs_support if a]
    # Risques déjà évalués qui portent sur l'un des actifs de support de ce processus
    actif_ids = {a["id"] for a in actifs_support}
    risques_lies = [r for r in get_risques_enrichis() if r.get("actif_id") in actif_ids]
    risques_lies.sort(key=lambda r: r["score"], reverse=True)
    return render_template(
        "processus_detail.html",
        p=p,
        information=information,
        actifs_support=actifs_support,
        risques_lies=risques_lies,
    )


@app.route("/processus/ajouter", methods=["GET", "POST"])
@auth.admin_required
def processus_add():
    if request.method == "POST":
        bloc_choisi = request.form["bloc"]
        if bloc_choisi == "Autre" and request.form.get("bloc_autre", "").strip():
            bloc_choisi = request.form["bloc_autre"].strip()

        actifs_support_ids = request.form.getlist("actifs_support_ids")

        # L'information essentielle associée est saisie dans le même
        # formulaire (relation 1-1 avec le processus dans ce périmètre).
        information = db.add("informations", {
            "processus_id": None,  # complété juste après une fois l'id du processus connu
            "nom": request.form.get("information_nom", ""),
            "description": request.form.get("information_description", ""),
            "dic_disponibilite": request.form.get("information_dic_disponibilite", "Faible"),
            "dic_integrite": request.form.get("information_dic_integrite", "Faible"),
            "dic_confidentialite": request.form.get("information_dic_confidentialite", "Faible"),
        })

        item = {
            "bloc": bloc_choisi,
            "nom": request.form["nom"],
            "description": request.form.get("description", ""),
            "dic_disponibilite": request.form["dic_disponibilite"],
            "dic_integrite": request.form["dic_integrite"],
            "dic_confidentialite": request.form["dic_confidentialite"],
            "information_id": information["id"],
            "actifs_support_ids": actifs_support_ids,
        }
        nouveau = db.add("processus", item)

        # Boucle l'information vers le processus qui vient d'être créé.
        information["processus_id"] = nouveau["id"]
        db.update("informations", information["id"], information)

        return redirect(url_for("processus_detail", processus_id=nouveau["id"]))

    return render_template(
        "processus_form.html",
        blocs_standards=BLOCS_STANDARDS,
        niveaux_dic=NIVEAUX_DIC,
        actifs=db.get_all("actifs"),
    )


@app.route("/processus/<processus_id>/modifier", methods=["GET", "POST"])
@auth.admin_required
def processus_edit(processus_id):
    p = db.get_by_id("processus", processus_id)
    if not p:
        return redirect(url_for("processus_list"))
    information = db.get_by_id("informations", p.get("information_id"))

    if request.method == "POST":
        bloc_choisi = request.form["bloc"]
        if bloc_choisi == "Autre" and request.form.get("bloc_autre", "").strip():
            bloc_choisi = request.form["bloc_autre"].strip()

        actifs_support_ids = request.form.getlist("actifs_support_ids")

        if information:
            information["nom"] = request.form.get("information_nom", "")
            information["description"] = request.form.get("information_description", "")
            information["dic_disponibilite"] = request.form.get("information_dic_disponibilite", "Faible")
            information["dic_integrite"] = request.form.get("information_dic_integrite", "Faible")
            information["dic_confidentialite"] = request.form.get("information_dic_confidentialite", "Faible")
            db.update("informations", information["id"], information)
            information_id = information["id"]
        else:
            nouvelle_info = db.add("informations", {
                "processus_id": processus_id,
                "nom": request.form.get("information_nom", ""),
                "description": request.form.get("information_description", ""),
                "dic_disponibilite": request.form.get("information_dic_disponibilite", "Faible"),
                "dic_integrite": request.form.get("information_dic_integrite", "Faible"),
                "dic_confidentialite": request.form.get("information_dic_confidentialite", "Faible"),
            })
            information_id = nouvelle_info["id"]

        item = {
            "bloc": bloc_choisi,
            "nom": request.form["nom"],
            "description": request.form.get("description", ""),
            "dic_disponibilite": request.form["dic_disponibilite"],
            "dic_integrite": request.form["dic_integrite"],
            "dic_confidentialite": request.form["dic_confidentialite"],
            "information_id": information_id,
            "actifs_support_ids": actifs_support_ids,
        }
        db.update("processus", processus_id, item)
        return redirect(url_for("processus_detail", processus_id=processus_id))

    return render_template(
        "processus_form.html",
        p=p,
        information=information,
        blocs_standards=BLOCS_STANDARDS,
        niveaux_dic=NIVEAUX_DIC,
        actifs=db.get_all("actifs"),
    )


@app.route("/processus/<processus_id>/supprimer", methods=["POST"])
@auth.admin_required
def processus_delete(processus_id):
    p = db.get_by_id("processus", processus_id)
    if p and p.get("information_id"):
        db.delete("informations", p["information_id"])
    db.delete("processus", processus_id)
    return redirect(url_for("processus_list"))


# ---------- ACTIFS ----------

@app.route("/actifs")
def actifs_list():
    actifs = db.get_all("actifs")
    types = sorted(set(a["type"] for a in actifs))
    services = sorted(set(a["service_it"] for a in actifs))
    importes = request.args.get("importes", type=int)
    erreurs_import = request.args.get("erreurs", type=int)
    return render_template(
        "actifs.html", actifs=actifs, types=types, services=services,
        importes=importes, erreurs_import=erreurs_import,
    )


@app.route("/actifs/ajouter", methods=["GET", "POST"])
@auth.admin_required
def actifs_add():
    if request.method == "POST":
        type_choisi = request.form["type"]
        if type_choisi == "Autre" and request.form.get("type_autre", "").strip():
            type_choisi = request.form["type_autre"].strip()
        service_choisi = request.form["service_it"]
        if service_choisi == "Autre" and request.form.get("service_autre", "").strip():
            service_choisi = request.form["service_autre"].strip()
        item = {
            "nom": request.form["nom"],
            "type": type_choisi,
            "service_it": service_choisi,
            "proprietaire": request.form["proprietaire"],
            "criticite": request.form["criticite"],
            "description": request.form.get("description", ""),
        }
        db.add("actifs", item)
        return redirect(url_for("actifs_list"))
    return render_template(
        "actif_form.html",
        types_standards=TYPES_ACTIFS_STANDARDS,
        services_standards=SERVICES_STANDARDS,
    )


@app.route("/actifs/<actif_id>/modifier", methods=["GET", "POST"])
@auth.admin_required
def actifs_edit(actif_id):
    actif = db.get_by_id("actifs", actif_id)
    if not actif:
        return redirect(url_for("actifs_list"))
    if request.method == "POST":
        type_choisi = request.form["type"]
        if type_choisi == "Autre" and request.form.get("type_autre", "").strip():
            type_choisi = request.form["type_autre"].strip()
        service_choisi = request.form["service_it"]
        if service_choisi == "Autre" and request.form.get("service_autre", "").strip():
            service_choisi = request.form["service_autre"].strip()
        item = {
            "nom": request.form["nom"],
            "type": type_choisi,
            "service_it": service_choisi,
            "proprietaire": request.form["proprietaire"],
            "criticite": request.form["criticite"],
            "description": request.form.get("description", ""),
            "date_ajout": actif.get("date_ajout"),
        }
        db.update("actifs", actif_id, item)
        return redirect(url_for("actifs_list"))
    return render_template(
        "actif_form.html",
        actif=actif,
        types_standards=TYPES_ACTIFS_STANDARDS,
        services_standards=SERVICES_STANDARDS,
    )


@app.route("/actifs/<actif_id>/supprimer", methods=["POST"])
@auth.admin_required
def actifs_delete(actif_id):
    db.delete("actifs", actif_id)
    return redirect(url_for("actifs_list"))


@app.route("/actifs/importer", methods=["POST"])
@auth.admin_required
def actifs_importer():
    fichier = request.files.get("fichier_csv")
    if not fichier or fichier.filename == "":
        return redirect(url_for("actifs_list", erreurs=1))

    try:
        contenu = fichier.stream.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        contenu = fichier.stream.read().decode("latin-1")

    reader = csv.DictReader(io.StringIO(contenu))
    colonnes_presentes = set(reader.fieldnames or [])
    colonnes_requises = {"nom", "type", "service_it"}
    if not colonnes_requises.issubset(colonnes_presentes):
        return redirect(url_for("actifs_list", erreurs=1))

    nb_importes = 0
    for row in reader:
        nom = (row.get("nom") or "").strip()
        if not nom:
            continue
        item = {
            "nom": nom,
            "type": (row.get("type") or "").strip() or "Autre",
            "service_it": (row.get("service_it") or "").strip() or "Autre",
            "proprietaire": (row.get("proprietaire") or "").strip(),
            "criticite": (row.get("criticite") or "").strip() or "Faible",
            "description": (row.get("description") or "").strip(),
        }
        db.add("actifs", item)
        nb_importes += 1

    return redirect(url_for("actifs_list", importes=nb_importes))


@app.route("/actifs/modele.csv")
def actifs_modele_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_ACTIFS_COLONNES)
    writer.writerow([
        "Serveur de messagerie interne", "Matériel", "Infrastructure",
        "Service informatique", "Élevée", "Rôle de l'actif, contexte d'utilisation",
    ])
    csv_bytes = "\ufeff".encode("utf-8") + output.getvalue().encode("utf-8")
    return Response(
        csv_bytes,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment;filename=modele_import_actifs.csv"},
    )


# ---------- RISQUES ----------

@app.route("/risques")
def risques_list():
    risques = get_risques_enrichis()
    risques.sort(key=lambda r: r["score"], reverse=True)
    filtre_niveau = request.args.get("niveau")
    if filtre_niveau:
        risques = [r for r in risques if r["niveau"] == filtre_niveau]
    return render_template("risques.html", risques=risques, filtre_niveau=filtre_niveau)


@app.route("/risques/ajouter", methods=["GET", "POST"])
@auth.admin_required
def risques_add():
    if request.method == "POST":
        # Menace : si "Autre" est choisi avec un libellé saisi, on crée une
        # nouvelle entrée dans le référentiel plutôt que de la perdre.
        menace_id = request.form["menace_id"]
        if menace_id == "AUTRE" and request.form.get("menace_autre", "").strip():
            nouvelle = db.add("menaces", {
                "categorie": "Autre",
                "libelle": request.form["menace_autre"].strip(),
                "description": "",
            })
            menace_id = nouvelle["id"]

        vulnerabilite_id = request.form["vulnerabilite_id"]
        if vulnerabilite_id == "AUTRE" and request.form.get("vulnerabilite_autre", "").strip():
            nouvelle = db.add("vulnerabilites", {
                "categorie": "Autre",
                "libelle": request.form["vulnerabilite_autre"].strip(),
                "description": "",
            })
            vulnerabilite_id = nouvelle["id"]

        mesures_appliquees = request.form.getlist("mesures_appliquees")
        if request.form.get("mesure_autre", "").strip():
            nouvelle = db.add("mesures", {
                "libelle": request.form["mesure_autre"].strip(),
                "type": "Complémentaire",
                "description": "",
            })
            mesures_appliquees.append(nouvelle["id"])

        item = {
            "actif_id": request.form["actif_id"],
            "menace_id": menace_id,
            "vulnerabilite_id": vulnerabilite_id,
            "probabilite": request.form["probabilite"],
            "impact": request.form["impact"],
            "description_scenario": request.form.get("description_scenario", ""),
            "mesures_appliquees": mesures_appliquees,
            "statut": request.form.get("statut", "Réduire"),
            "commentaire": request.form.get("commentaire", ""),
        }
        db.add("risques", item)
        return redirect(url_for("risques_list"))

    return render_template(
        "risque_form.html",
        actifs=db.get_all("actifs"),
        menaces=db.get_all("menaces"),
        vulnerabilites=db.get_all("vulnerabilites"),
        mesures=db.get_all("mesures"),
        statuts=STATUTS_RISQUE,
    )


@app.route("/risques/<risque_id>")
def risque_detail(risque_id):
    risque = db.get_by_id("risques", risque_id)
    if not risque:
        return redirect(url_for("risques_list"))
    enriched = risk_engine.enrichir_risque(risque, db)
    return render_template("risque_detail.html", r=enriched, statuts=STATUTS_RISQUE)


@app.route("/risques/<risque_id>/statut", methods=["POST"])
@auth.admin_required
def risque_update_statut(risque_id):
    risque = db.get_by_id("risques", risque_id)
    if risque:
        risque["statut"] = request.form["statut"]
        db.update("risques", risque_id, risque)
    return redirect(url_for("risque_detail", risque_id=risque_id))


# ---------- REGISTRE (export) ----------

@app.route("/registre")
def registre():
    risques = get_risques_enrichis()
    risques.sort(key=lambda r: r["score"], reverse=True)
    return render_template("registre.html", risques=risques, date_export=date.today().isoformat())


@app.route("/registre/export.csv")
def registre_export_csv():
    risques = get_risques_enrichis()
    risques.sort(key=lambda r: r["score"], reverse=True)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Actif", "Type actif", "Menace", "Vulnérabilité",
        "Probabilité", "Impact", "Score", "Niveau", "Statut",
        "Mesures appliquées", "Commentaire"
    ])
    for r in risques:
        writer.writerow([
            r["id"],
            r["actif"]["nom"] if r["actif"] else "",
            r["actif"]["type"] if r["actif"] else "",
            r["menace"]["libelle"] if r["menace"] else "",
            r["vulnerabilite"]["libelle"] if r["vulnerabilite"] else "",
            r["probabilite"],
            r["impact"],
            r["score"],
            r["niveau"],
            r["statut"],
            "; ".join(m["libelle"] for m in r["mesures"]),
            r.get("commentaire", ""),
        ])

    csv_data = output.getvalue()
    # Excel (surtout sur Windows) suppose du Latin-1/Windows-1252 sans indice
    # explicite -> d'où les accents mal affichés ("Ã©", "Å"...). Le BOM UTF-8
    # ci-dessous force Excel à détecter correctement l'encodage.
    csv_bytes = "\ufeff".encode("utf-8") + csv_data.encode("utf-8")
    return Response(
        csv_bytes,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment;filename=registre_risques.csv"},
    )


# ---------- API légère (utile pour le formulaire dynamique côté JS) ----------

@app.route("/api/vulnerabilites/<vuln_id>/recommandations")
def api_recommandations(vuln_id):
    type_actif = request.args.get("type")
    mesures_ids = risk_engine.recommander_mesures_combinees(vuln_id, type_actif)
    mesures = [db.get_by_id("mesures", m) for m in mesures_ids]
    return jsonify([m for m in mesures if m])


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
