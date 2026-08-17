"""
Moteur de risque — méthode DGSSI simplifiée.

Échelle retenue (3 niveaux, pour rester gérable sur la durée du stage) :
    Probabilité : Faible (1) / Moyenne (2) / Élevée (3)
    Impact      : Faible (1) / Moyen (2) / Élevé (3) / Critique (4)

Niveau de risque = Probabilité x Impact, classé ensuite en 4 paliers :
    1-2   -> Faible
    3-4   -> Moyen
    6-8   -> Élevé
    9-12  -> Critique
"""

PROBABILITE_SCORES = {"Faible": 1, "Moyenne": 2, "Élevée": 3}
IMPACT_SCORES = {"Faible": 1, "Moyen": 2, "Élevé": 3, "Critique": 4}


def score_risque(probabilite, impact):
    p = PROBABILITE_SCORES.get(probabilite, 1)
    i = IMPACT_SCORES.get(impact, 1)
    return p * i


def niveau_risque(probabilite, impact):
    s = score_risque(probabilite, impact)
    if s >= 9:
        return "Critique"
    if s >= 6:
        return "Élevé"
    if s >= 3:
        return "Moyen"
    return "Faible"


def couleur_niveau(niveau):
    """Couleur tally associée à chaque niveau, pour l'affichage."""
    return {
        "Critique": "var(--tally-red)",
        "Élevé": "var(--tally-red)",
        "Moyen": "var(--diffusion-amber)",
        "Faible": "var(--phosphor-green)",
    }.get(niveau, "var(--text-dim)")


COULEURS_TYPES = {
    "Matériel": "var(--type-materiel)",
    "Logiciel": "var(--type-logiciel)",
    "Données": "var(--type-donnees)",
    "Réseau": "var(--type-reseau)",
    "Personnel": "var(--type-personnel)",
    "Site physique": "var(--type-site)",
    "Service tiers": "var(--type-tiers)",
}


def couleur_type(type_actif):
    """Couleur dédiée à un type d'actif (palette distincte du code
    rouge/ambre/vert des risques, pour ne pas laisser croire qu'un type
    d'actif serait en lui-même 'plus grave' qu'un autre)."""
    return COULEURS_TYPES.get(type_actif, "var(--type-autre)")


def repartition_par_type(actifs):
    """Compte les actifs par type et prépare les données d'affichage
    (couleur + pourcentage) pour le graphique du tableau de bord."""
    compte = {}
    for a in actifs:
        t = a.get("type", "Autre")
        compte[t] = compte.get(t, 0) + 1
    total = len(actifs) or 1
    items = [
        {
            "type": t,
            "count": n,
            "pct": round(n / total * 100, 1),
            "couleur": couleur_type(t),
        }
        for t, n in compte.items()
    ]
    items.sort(key=lambda x: x["count"], reverse=True)
    return items


RECOMMANDATIONS = {
    # (catégorie vulnérabilité déclenchante) -> mesures suggérées (ids de mesures.json)
    "V1": ["S3", "S10"],
    "V2": ["S2"],
    "V3": ["S6", "S7"],
    "V4": ["S12"],
    "V5": ["S4"],
    "V6": ["S10"],
    "V7": ["S9"],
    "V8": ["S11"],
    "V9": ["S10"],
    "V10": ["S1"],
}

# Mesures pertinentes selon le TYPE d'actif concerné, indépendamment de la
# vulnérabilité — par exemple un actif "Réseau" appelle presque toujours à
# vérifier la segmentation, un actif "Personnel" appelle à la sensibilisation
# et à la revue des accès, etc.
RECOMMANDATIONS_PAR_TYPE = {
    "Matériel": ["S12", "S9"],
    "Logiciel": ["S4", "S3"],
    "Données": ["S3", "S9"],
    "Réseau": ["S2", "S13"],
    "Personnel": ["S1", "S10", "S11"],
    "Site physique": ["S12"],
    "Service tiers": ["S10", "S6"],
}


def recommander_mesures(vulnerabilite_id, mesures_deja_appliquees=None):
    """Retourne les ids de mesures suggérées pour une vulnérabilité donnée,
    en excluant celles déjà appliquées sur ce risque."""
    deja = set(mesures_deja_appliquees or [])
    suggestions = RECOMMANDATIONS.get(vulnerabilite_id, [])
    return [m for m in suggestions if m not in deja]


def recommander_mesures_combinees(vulnerabilite_id, type_actif=None, mesures_deja_appliquees=None):
    """Fusionne les recommandations issues de la vulnérabilité ET du type
    d'actif concerné, sans doublon, en excluant ce qui est déjà appliqué."""
    deja = set(mesures_deja_appliquees or [])
    suggestions = list(RECOMMANDATIONS.get(vulnerabilite_id, []))
    for m in RECOMMANDATIONS_PAR_TYPE.get(type_actif, []):
        if m not in suggestions:
            suggestions.append(m)
    return [m for m in suggestions if m not in deja]


def enrichir_risque(risque, db):
    """Ajoute au dict risque les objets liés (actif, menace, vulnérabilité,
    mesures) ainsi que le score et le niveau calculés, prêt pour l'affichage."""
    actif = db.get_by_id("actifs", risque.get("actif_id"))
    menace = db.get_by_id("menaces", risque.get("menace_id"))
    vulnerabilite = db.get_by_id("vulnerabilites", risque.get("vulnerabilite_id"))
    mesures_ids = risque.get("mesures_appliquees", [])
    mesures = [db.get_by_id("mesures", mid) for mid in mesures_ids]
    mesures = [m for m in mesures if m]

    probabilite = risque.get("probabilite", "Faible")
    impact = risque.get("impact", "Faible")
    score = score_risque(probabilite, impact)
    niveau = niveau_risque(probabilite, impact)

    recommandations_ids = recommander_mesures_combinees(
        risque.get("vulnerabilite_id"),
        actif.get("type") if actif else None,
        mesures_ids,
    )
    recommandations = [db.get_by_id("mesures", mid) for mid in recommandations_ids]
    recommandations = [m for m in recommandations if m]

    enriched = dict(risque)
    enriched.update({
        "actif": actif,
        "menace": menace,
        "vulnerabilite": vulnerabilite,
        "mesures": mesures,
        "score": score,
        "niveau": niveau,
        "couleur": couleur_niveau(niveau),
        "recommandations": recommandations,
    })
    return enriched


def stats_globales(risques_enrichis):
    """Compte le nombre de risques par niveau, pour le tableau de bord."""
    compte = {"Critique": 0, "Élevé": 0, "Moyen": 0, "Faible": 0}
    for r in risques_enrichis:
        compte[r["niveau"]] = compte.get(r["niveau"], 0) + 1
    return compte
