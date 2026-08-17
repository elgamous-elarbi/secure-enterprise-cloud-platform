-- ============================================================================
-- Schéma PostgreSQL — Application de gestion des risques DGSSI
-- ============================================================================
-- Les identifiants métier (A1, R3, M2...) restent des chaînes de caractères,
-- exactement comme dans les fichiers JSON d'origine, pour ne rien casser
-- côté application (app.py, risk_engine.py, templates) qui manipulent ces
-- ids comme des chaînes partout.
--
-- Deux relations n-n de la version JSON (listes d'ids dans un champ) sont
-- ici modélisées en tables de jonction, ce qui est la façon correcte de
-- représenter une relation many-to-many en base relationnelle :
--   - processus.actifs_support_ids   -> processus_actifs_support
--   - risques.mesures_appliquees     -> risques_mesures
--
-- À exécuter une seule fois pour créer la base :
--   psql -U <user> -d <dbname> -f schema.sql
-- ============================================================================

-- ---------- Tables de référence (pas de dépendances) ----------

CREATE TABLE IF NOT EXISTS utilisateurs (
    id                  VARCHAR(10)   PRIMARY KEY,
    identifiant         VARCHAR(100)  NOT NULL UNIQUE,
    nom_affiche         VARCHAR(150)  NOT NULL,
    mot_de_passe_hash   TEXT          NOT NULL,
    role                VARCHAR(20)   NOT NULL
);

CREATE TABLE IF NOT EXISTS actifs (
    id              VARCHAR(10)  PRIMARY KEY,
    nom             VARCHAR(200) NOT NULL,
    type            VARCHAR(50),
    service_it      VARCHAR(100),
    proprietaire    VARCHAR(150),
    criticite       VARCHAR(20),
    description     TEXT,
    date_ajout      DATE
);

CREATE TABLE IF NOT EXISTS menaces (
    id          VARCHAR(10)  PRIMARY KEY,
    categorie   VARCHAR(100),
    libelle     VARCHAR(200) NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS vulnerabilites (
    id          VARCHAR(10)  PRIMARY KEY,
    categorie   VARCHAR(100),
    libelle     VARCHAR(200) NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS mesures (
    id          VARCHAR(10)  PRIMARY KEY,
    libelle     VARCHAR(200) NOT NULL,
    type        VARCHAR(50),
    description TEXT
);

-- ---------- Processus / informations (référence circulaire) ----------
-- Chaque processus a une information essentielle associée, et chaque
-- information "sait" à quel processus elle appartient (même logique que
-- dans les JSON d'origine : informations.processus_id ET
-- processus.information_id existent tous les deux).

CREATE TABLE IF NOT EXISTS processus (
    id                    VARCHAR(10)  PRIMARY KEY,
    bloc                  VARCHAR(150),
    nom                   VARCHAR(200) NOT NULL,
    description           TEXT,
    dic_disponibilite     VARCHAR(20),
    dic_integrite         VARCHAR(20),
    dic_confidentialite   VARCHAR(20),
    information_id        VARCHAR(10)   -- FK ajoutée plus bas (informations n'existe pas encore)
);

CREATE TABLE IF NOT EXISTS informations (
    id                    VARCHAR(10)  PRIMARY KEY,
    processus_id          VARCHAR(10)  REFERENCES processus(id) ON DELETE CASCADE,
    nom                   VARCHAR(200) NOT NULL,
    description           TEXT,
    dic_disponibilite     VARCHAR(20),
    dic_integrite         VARCHAR(20),
    dic_confidentialite   VARCHAR(20)
);

ALTER TABLE processus
    DROP CONSTRAINT IF EXISTS fk_processus_information;
ALTER TABLE processus
    ADD CONSTRAINT fk_processus_information
    FOREIGN KEY (information_id) REFERENCES informations(id) ON DELETE SET NULL;

-- Table de jonction : actifs de support liés à un processus (n-n)
CREATE TABLE IF NOT EXISTS processus_actifs_support (
    processus_id  VARCHAR(10) REFERENCES processus(id) ON DELETE CASCADE,
    actif_id      VARCHAR(10) REFERENCES actifs(id) ON DELETE CASCADE,
    PRIMARY KEY (processus_id, actif_id)
);

-- ---------- Risques ----------
-- actif_id / menace_id / vulnerabilite_id en ON DELETE SET NULL : si un
-- actif de référence est supprimé, le risque n'est pas perdu (il reste dans
-- le registre, juste avec un actif "manquant"), comportement identique à
-- la version JSON qui ne bloquait pas non plus la suppression.

CREATE TABLE IF NOT EXISTS risques (
    id                     VARCHAR(10)  PRIMARY KEY,
    actif_id               VARCHAR(10)  REFERENCES actifs(id) ON DELETE SET NULL,
    menace_id              VARCHAR(10)  REFERENCES menaces(id) ON DELETE SET NULL,
    vulnerabilite_id       VARCHAR(10)  REFERENCES vulnerabilites(id) ON DELETE SET NULL,
    probabilite            VARCHAR(20),
    impact                 VARCHAR(20),
    description_scenario   TEXT,
    statut                 VARCHAR(20),
    commentaire            TEXT
);

-- Table de jonction : mesures appliquées sur un risque (n-n)
CREATE TABLE IF NOT EXISTS risques_mesures (
    risque_id  VARCHAR(10) REFERENCES risques(id) ON DELETE CASCADE,
    mesure_id  VARCHAR(10) REFERENCES mesures(id) ON DELETE CASCADE,
    PRIMARY KEY (risque_id, mesure_id)
);

-- ---------- Index utiles ----------
CREATE INDEX IF NOT EXISTS idx_risques_actif ON risques(actif_id);
CREATE INDEX IF NOT EXISTS idx_risques_menace ON risques(menace_id);
CREATE INDEX IF NOT EXISTS idx_risques_vuln ON risques(vulnerabilite_id);
CREATE INDEX IF NOT EXISTS idx_informations_processus ON informations(processus_id);
