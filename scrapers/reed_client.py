import requests
import pandas as pd
import time
import base64

API_KEY  = "0fc66897-5add-44be-9785-80eecd73aca4"
BASE_URL = "https://www.reed.co.uk/api/1.0/search"

# Auth Basic : API_KEY + ":" encodé en base64
credentials = base64.b64encode(f"{API_KEY}:".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {credentials}",
    "Content-Type":  "application/json"
}

METIERS = [
    "data scientist",
    "data engineer",
    "data analyst",
    "machine learning",
    "business intelligence"
]

def search_reed(query: str, offset: int = 0) -> list:
    try:
        params = {
            "keywords":   query,
            "locationName": "France",
            "resultsToTake": 100,
            "resultsToSkip": offset
        }
        response = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        return response.json().get("results", [])
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return []


def normaliser_reed(offre: dict) -> dict:
    # Salaire
    min_sal = offre.get("minimumSalary", "")
    max_sal = offre.get("maximumSalary", "")
    if min_sal and max_sal:
        salaire = f"{min_sal} - {max_sal} GBP"
    else:
        salaire = "Non précisé"

    return {
        "id":                    str(offre.get("jobId", "")),
        "titre":                 offre.get("jobTitle", "").strip().title(),
        "entreprise":            offre.get("employerName", "Non précisé"),
        "ville":                 offre.get("locationName", "Non précisé"),
        "code_postal":           "",
        "contrat":               "CDI" if not offre.get("contract") else offre.get("contract"),
        "salaire":               salaire,
        "experience":            "Non précisé",
        "competences":           "",
        "competences_extraites": "",
        "description":           str(offre.get("jobDescription", ""))[:500],
        "date_publication":      str(offre.get("date", ""))[:10],
        "url":                   offre.get("jobUrl", ""),
        "source":                "Reed"
    }


def collecter_reed():
    print("🚀 Collecte Reed.co.uk...\n")
    toutes = []

    for metier in METIERS:
        print(f"🔍 Recherche : {metier}")
        offres = search_reed(metier)
        if offres:
            toutes.extend(offres)
            print(f"   → {len(offres)} offres trouvées")
        else:
            print(f"   → Aucune offre")
        time.sleep(1)

    if not toutes:
        print("❌ Aucune offre collectée")
        return pd.DataFrame()

    print("\n⚙️  Normalisation des données...")
    normalisees = [normaliser_reed(o) for o in toutes]
    df = pd.DataFrame(normalisees)
    df = df.drop_duplicates(subset=["id"])
    df = df.fillna("Non précisé")

    print(f"✅ {len(df)} offres Reed collectées")
    df.to_csv("offres_reed.csv", index=False, encoding="utf-8-sig")
    print("💾 Sauvegardé : offres_reed.csv")

    print("\n📋 Aperçu :")
    print(df[["titre", "entreprise", "ville", "contrat"]].head(5))

    return df


if __name__ == "__main__":
    collecter_reed()