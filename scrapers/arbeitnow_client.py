import requests
import pandas as pd
import time

BASE_URL = "https://arbeitnow.com/api/job-board-api"

METIERS = [
    "data scientist",
    "data engineer",
    "data analyst",
    "machine learning",
    "business intelligence"
]

def search_arbeitnow(query: str, page: int = 1) -> list:
    """
    Récupère les offres depuis Arbeitnow API (gratuite, sans clé).
    """
    try:
        params = {
            "q":    query,
            "page": page
        }
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return []


def normaliser_arbeitnow(offre: dict) -> dict:
    """
    Normalise une offre Arbeitnow en format unifié.
    """
    # Tags/compétences
    tags = offre.get("tags", []) or []
    competences = ", ".join(tags) if tags else "Non précisé"

    # Contrat
    remote = offre.get("remote", False)
    contrat = "Remote" if remote else "CDI"

    # Date
    created = offre.get("created_at", "")
    date = str(created)[:10] if created else "Non précisé"

    return {
        "id":                    str(offre.get("slug", "")),
        "titre":                 offre.get("title", "").strip().title(),
        "entreprise":            offre.get("company_name", "Non précisé"),
        "ville":                 offre.get("location", "Non précisé"),
        "code_postal":           "",
        "contrat":               contrat,
        "salaire":               "Non précisé",
        "experience":            "Non précisé",
        "competences":           competences,
        "competences_extraites": competences,
        "description":           str(offre.get("description", ""))[:500],
        "date_publication":      date,
        "url":                   offre.get("url", ""),
        "source":                "Arbeitnow"
    }


def collecter_arbeitnow():
    print("🚀 Collecte Arbeitnow...\n")
    toutes = []

    for metier in METIERS:
        print(f"🔍 Recherche : {metier}")
        # Récupérer 3 pages par métier
        for page in range(1, 4):
            offres = search_arbeitnow(metier, page=page)
            if not offres:
                break
            toutes.extend(offres)
            time.sleep(1)

        print(f"   → offres récupérées jusqu'ici : {len(toutes)}")

    if not toutes:
        print("❌ Aucune offre collectée")
        return pd.DataFrame()

    # Normalisation
    print("\n⚙️  Normalisation des données...")
    normalisees = [normaliser_arbeitnow(o) for o in toutes]
    df = pd.DataFrame(normalisees)

    # Déduplication
    df = df.drop_duplicates(subset=["id"])
    df = df.fillna("Non précisé")

    print(f"✅ {len(df)} offres Arbeitnow collectées")
    df.to_csv("offres_arbeitnow.csv", index=False, encoding="utf-8-sig")
    print("💾 Sauvegardé : offres_arbeitnow.csv")

    print("\n📋 Aperçu :")
    print(df[["titre", "entreprise", "ville", "contrat"]].head(5))

    return df


if __name__ == "__main__":
    collecter_arbeitnow()