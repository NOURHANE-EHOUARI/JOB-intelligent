import requests
import pandas as pd
import time

RAPIDAPI_KEY  = "8c8f7b45a4mshecb7e0ad34d8b00p141cd8jsn78528ddea3df"
RAPIDAPI_HOST = "linkedin-job-search-api.p.rapidapi.com"

METIERS = [
    "data scientist",
    "data engineer",
    "data analyst",
    "machine learning",
    "business intelligence"
]

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
        "titre":            offre.get("title", "").strip().title(),
        "entreprise":       entreprise,
        "ville":            ville,
        "code_postal":      "",
        "contrat":          contrat,
        "salaire":          salaire,
        "experience":       offre.get("experience_level", "Non précisé"),
        "competences":      competences,
        "competences_extraites": competences,
        "description":      str(offre.get("description", ""))[:500],
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
    normalisees = [normaliser_linkedin(o) for o in toutes]
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