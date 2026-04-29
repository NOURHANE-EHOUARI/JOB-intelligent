import requests
import pandas as pd
import time

RAPIDAPI_KEY  = "8c8f7b45a4mshecb7e0ad34d8b00p141cd8jsn78528ddea3df"
RAPIDAPI_HOST = "jsearch.p.rapidapi.com"

METIERS = [
    "data scientist",
    "data engineer", 
    "data analyst",
    "machine learning",
    "business intelligence"
]

def search_jsearch(query: str, page: int = 1) -> list:
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "x-rapidapi-key":  RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }
    params = {
        "query":       f"{query} France",
        "page":        page,
        "num_pages":   1,
        "country":     "fr",
        "date_posted": "month"
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json().get("data", [])


def normaliser_jsearch(offre: dict) -> dict:
    return {
        "id":               offre.get("job_id", ""),
        "titre":            offre.get("job_title", "").strip().title(),
        "entreprise":       offre.get("employer_name", "Non précisé"),
        "ville":            offre.get("job_city", "Non précisé"),
        "code_postal":      "",
        "contrat":          "CDI" if offre.get("job_is_remote") else offre.get("job_employment_type", "Non précisé"),
        "salaire":          f"{offre.get('job_min_salary', '')} - {offre.get('job_max_salary', '')}",
        "experience":       offre.get("job_required_experience", {}).get("required_experience_in_months", "Non précisé"),
        "competences":      ", ".join(offre.get("job_required_skills", []) or []),
        "description":      (offre.get("job_description", "")[:500]),
        "date_publication": offre.get("job_posted_at_datetime_utc", "")[:10],
        "url":              offre.get("job_apply_link", ""),
        "source":           "JSearch/Indeed"
    }


def collecter_indeed():
    print("🚀 Collecte JSearch/Indeed...\n")
    toutes = []

    for metier in METIERS:
        print(f"🔍 Recherche : {metier}")
        offres = search_jsearch(metier)
        toutes.extend(offres)
        print(f"   → {len(offres)} offres trouvées")
        time.sleep(1)

    normalisees = [normaliser_jsearch(o) for o in toutes]
    df = pd.DataFrame(normalisees).drop_duplicates(subset=["id"])

    print(f"\n✅ {len(df)} offres Indeed collectées")
    df.to_csv("offres_indeed.csv", index=False, encoding="utf-8-sig")
    print("💾 Sauvegardé : offres_indeed.csv")
    return df


if __name__ == "__main__":
    collecter_indeed()