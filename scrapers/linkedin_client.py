# ── FIX: Ensure project root is in Python path ──
import sys, os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# ───────────────────────────────────────────────

import requests
import pandas as pd
import time

# ──────────────────────────────────────────────────────────────
# AJOUT TÂCHE 4 : Import config NLP pour le filtre qualité
# ──────────────────────────────────────────────────────────────
from utils.nlp_config import load_nlp_config

RAPIDAPI_KEY  = "8c8f7b45a4mshecb7e0ad34d8b00p141cd8jsn78528ddea3df"
RAPIDAPI_HOST = "linkedin-job-search-api.p.rapidapi.com"

METIERS = [
    "data scientist",
    "data engineer",
    "data analyst",
    "machine learning",
    "business intelligence"
]

# ──────────────────────────────────────────────────────────────
# AJOUT TÂCHE 4 : Fonction de validation qualité (standalone)
# ──────────────────────────────────────────────────────────────
def validate_offer_quality(title: str, description: str) -> bool:
    """
    Filtre pré-ETL : rejette les offres trop courtes ou contenant des mots-clés négatifs.
    Version standalone pour les scripts fonctionnels (non-class-based).
    """
    cfg = load_nlp_config()
    filters = cfg["scraping_filters"]
    negatives = cfg["negative_keywords"]
    
    text = f"{title} {description}".lower()
    
    # 1. Longueur minimale de description
    if len(description) < filters["description_min_length"]:
        return False
        
    # 2. Mots-clés négatifs (spam/stage non rémunéré/arnaque)
    if any(neg in text for neg in negatives):
        return False
        
    # 3. Au moins un mot-clé technique requis
    if not any(kw in text for kw in filters["required_tech_keywords"]):
        return False
        
    return True


def search_linkedin(query: str, offset: int = 0) -> list:
    """
    Récupère les offres LinkedIn publiées dans les 24 dernières heures.
    """
    url = "https://linkedin-job-search-api.p.rapidapi.com/active-jb-24h"
    headers = {
        "x-rapidapi-key":  RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }
    params = {
        "limit":            "100",
        "offset":           str(offset),
        "description_type": "text",
        "location":         "France",
        "title":            query,
        "country":          "fr"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []
    except requests.exceptions.HTTPError as e:
        print(f"❌ Erreur HTTP : {e}")
        return []
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return []


def normaliser_linkedin(offre: dict) -> dict:
    """
    Normalise une offre LinkedIn brute en format unifié.
    """
    # ✅ AJOUT TÂCHE 4 : Validation qualité pré-normalisation
    title = offre.get("title", "").strip().title()
    description = str(offre.get("description", ""))
    
    if not validate_offer_quality(title, description):
        return None  # Rejeter l'offre si elle ne passe pas les filtres
    
    # Localisation
    lieu = offre.get("location", {})
    if isinstance(lieu, dict):
        ville = lieu.get("city", "Non précisé")
    else:
        ville = str(lieu) if lieu else "Non précisé"

    # Salaire
    salaire_info = offre.get("salary", {})
    if isinstance(salaire_info, dict) and salaire_info:
        salaire = f"{salaire_info.get('min', '')} - {salaire_info.get('max', '')} {salaire_info.get('currency', '')}"
    else:
        salaire = "Non précisé"

    # Compétences
    competences = offre.get("skills", []) or []
    if isinstance(competences, list):
        competences = ", ".join(competences)
    else:
        competences = str(competences)

    # Entreprise
    company = offre.get("company", {})
    if isinstance(company, dict):
        entreprise = company.get("name", "Non précisé")
    else:
        entreprise = str(company) if company else "Non précisé"

    # Contrat
    contrat_raw = offre.get("contract_type", "")
    contrat_map = {
        "FULL_TIME": "CDI",
        "PART_TIME": "Temps partiel",
        "CONTRACT":  "CDD",
        "INTERNSHIP": "Stage",
        "TEMPORARY": "Mission intérimaire"
    }
    contrat = contrat_map.get(contrat_raw, contrat_raw if contrat_raw else "Non précisé")

    return {
        "id":               offre.get("id", ""),
        "titre":            title,
        "entreprise":       entreprise,
        "ville":            ville,
        "code_postal":      "",
        "contrat":          contrat,
        "salaire":          salaire,
        "experience":       offre.get("experience_level", "Non précisé"),
        "competences":      competences,
        "competences_extraites": competences,
        "description":      description[:500],
        "date_publication": str(offre.get("created_at", ""))[:10],
        "url":              offre.get("url", ""),
        "source":           "LinkedIn"
    }


def collecter_linkedin():
    print("🚀 Collecte LinkedIn (offres 24h)...\n")
    toutes = []

    for metier in METIERS:
        print(f"🔍 Recherche : {metier}")
        offres = search_linkedin(metier)

        if offres:
            toutes.extend(offres)
            print(f"   → {len(offres)} offres trouvées")
        else:
            print(f"   → Aucune offre trouvée")

        time.sleep(10)

    if not toutes:
        print("\n❌ Aucune offre collectée")
        return pd.DataFrame()

    # Normalisation
    print("\n⚙️  Normalisation des données...")
    # ✅ AJOUT TÂCHE 4 : Filtrer les None retournés par validate_offer_quality
    normalisees = [normaliser_linkedin(o) for o in toutes]
    normalisees = [n for n in normalisees if n is not None]  # Skip rejected offers
    
    df = pd.DataFrame(normalisees)

    # Déduplication
    df = df.drop_duplicates(subset=["id"])
    df = df.fillna("Non précisé")

    print(f"✅ {len(df)} offres LinkedIn collectées")
    df.to_csv("offres_linkedin.csv", index=False, encoding="utf-8-sig")
    print("💾 Sauvegardé : offres_linkedin.csv")

    # Aperçu
    print("\n📋 Aperçu :")
    print(df[["titre", "entreprise", "ville", "contrat"]].head(5))

    return df


if __name__ == "__main__":
    collecter_linkedin()