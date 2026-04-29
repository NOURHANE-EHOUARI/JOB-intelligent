import requests
import pandas as pd
import time

BASE_URL = "https://api.welcometothejungle.com/api/v1/jobs"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Referer": "https://www.welcometothejungle.com/fr/jobs",
    "Origin": "https://www.welcometothejungle.com"
}

METIERS = [
    "data scientist",
    "data engineer",
    "data analyst",
    "machine learning",
    "business intelligence"
]

def search_wttj(query: str, page: int = 1) -> list:
    try:
        params = {
            "query":        query,
            "page":         page,
            "per_page":     30,
            "language":     "fr",
            "country_code": "FR"
        }
        response = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("jobs", []) or data.get("data", []) or []
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return []


def normaliser_wttj(offre: dict) -> dict:
    offices = offre.get("offices", []) or []
    ville = offices[0].get("city", "Non précisé") if offices else "Non précisé"

    contrat_map = {
        "FULL_TIME":      "CDI",
        "PART_TIME":      "Temps partiel",
        "INTERNSHIP":     "Stage",
        "FREELANCE":      "Freelance",
        "APPRENTICESHIP": "Alternance",
        "TEMPORARY":      "CDD"
    }
    contrat_raw = offre.get("contract_type", "")
    contrat = contrat_map.get(contrat_raw, contrat_raw if contrat_raw else "Non précisé")

    salary = offre.get("salary", {}) or {}
    if salary and salary.get("min"):
        salaire = f"{salary.get('min', '')} - {salary.get('max', '')} {salary.get('currency', 'EUR')}"
    else:
        salaire = "Non précisé"

    tags = offre.get("tags", []) or []
    competences = ", ".join([t.get("name", "") for t in tags if isinstance(t, dict)])

    org = offre.get("organization", {}) or {}
    entreprise = org.get("name", "Non précisé")

    slug = offre.get("slug", offre.get("reference", ""))

    return {
        "id":                    str(slug),
        "titre":                 offre.get("name", offre.get("title", "")).strip().title(),
        "entreprise":            entreprise,
        "ville":                 ville,
        "code_postal":           "",
        "contrat":               contrat,
        "salaire":               salaire,
        "experience":            offre.get("experience_level", "Non précisé"),
        "competences":           competences,
        "competences_extraites": competences,
        "description":           str(offre.get("description", ""))[:500],
        "date_publication":      str(offre.get("published_at", ""))[:10],
        "url":                   f"https://www.welcometothejungle.com/fr/jobs/{slug}",
        "source":                "WelcomeToTheJungle"
    }


def collecter_wttj():
    print("🚀 Collecte WelcomeToTheJungle...\n")
    toutes = []

    for metier in METIERS:
        print(f"🔍 Recherche : {metier}")
        for page in range(1, 4):
            offres = search_wttj(metier, page=page)
            if not offres:
                print(f"   → Aucune offre page {page}")
                break
            toutes.extend(offres)
            time.sleep(2)
        print(f"   → offres récupérées : {len(toutes)}")

    if not toutes:
        print("❌ Aucune offre collectée")
        return pd.DataFrame()

    print("\n⚙️  Normalisation des données...")
    normalisees = [normaliser_wttj(o) for o in toutes]
    df = pd.DataFrame(normalisees)
    df = df.drop_duplicates(subset=["id"])
    df = df.fillna("Non précisé")

    print(f"✅ {len(df)} offres WTTJ collectées")
    df.to_csv("offres_wttj.csv", index=False, encoding="utf-8-sig")
    print("💾 Sauvegardé : offres_wttj.csv")

    print("\n📋 Aperçu :")
    print(df[["titre", "entreprise", "ville", "contrat"]].head(5))

    return df


if __name__ == "__main__":
    collecter_wttj()