import requests
import time
from auth import get_token

BASE_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"

def search_offres(mots_cles="data scientist", lieu=None, max_offres=150):
    """
    Récupère les offres d'emploi avec pagination automatique.
    - mots_cles : ex "data engineer", "data analyst"
    - lieu      : code INSEE de la ville (ex "75056" pour Paris)
    - max_offres: nombre max d'offres à récupérer
    """
    toutes_offres = []
    start = 0
    range_size = 50  # max autorisé par appel

    while start < max_offres:
        token = get_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

        params = {
            "motsCles": mots_cles,
            "range": f"{start}-{start + range_size - 1}"
        }

        if lieu:
            params["commune"] = lieu

        try:
            response = requests.get(BASE_URL, headers=headers, params=params)

            # Rate limit : attendre si 429
            if response.status_code == 429:
                print("⏳ Rate limit atteint, attente 10s...")
                time.sleep(10)
                continue

            response.raise_for_status()
            data = response.json()

            offres = data.get("resultats", [])
            if not offres:
                print("✅ Plus d'offres disponibles.")
                break

            toutes_offres.extend(offres)
            print(f"📦 {len(toutes_offres)} offres récupérées...")

            start += range_size
            time.sleep(1)  # pause entre chaque appel

        except requests.exceptions.HTTPError as e:
            print(f"❌ Erreur HTTP : {e}")
            break

    return toutes_offres