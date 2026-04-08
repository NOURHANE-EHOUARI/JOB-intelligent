from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time
import pandas as pd

# Initialisation du géocodeur
geolocator = Nominatim(user_agent="job-intelligent-app")

# Cache pour éviter de re-géocoder la même ville
_cache_villes = {}

def geocoder_ville(ville: str) -> dict:
    """
    Retourne latitude et longitude d'une ville.
    Utilise un cache pour éviter les appels répétés.
    """
    if not ville or ville == "Non précisé":
        return {"latitude": None, "longitude": None}

    # Nettoyer le nom de la ville (enlever codes postaux)
    ville_clean = ville.split("(")[0].strip()
    ville_clean = ville_clean.split("-")[0].strip()

    # Vérifier le cache
    if ville_clean in _cache_villes:
        return _cache_villes[ville_clean]

    try:
        # Chercher en France uniquement
        location = geolocator.geocode(
            f"{ville_clean}, France",
            timeout=10
        )

        if location:
            result = {
                "latitude":  round(location.latitude, 4),
                "longitude": round(location.longitude, 4)
            }
        else:
            result = {"latitude": None, "longitude": None}

        # Sauvegarder dans le cache
        _cache_villes[ville_clean] = result

        # Pause obligatoire (règle Nominatim : 1 req/sec)
        time.sleep(1)

        return result

    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"⚠️  Erreur géocodage '{ville_clean}' : {e}")
        return {"latitude": None, "longitude": None}


def enrichir_coordonnees(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ajoute les colonnes latitude et longitude au DataFrame.
    """
    print("🌍 Géocodage des villes en cours...")

    # Récupérer les villes uniques pour optimiser
    villes_uniques = df["ville"].unique()
    print(f"   → {len(villes_uniques)} villes uniques à géocoder")

    # Géocoder chaque ville unique
    coords = {}
    for i, ville in enumerate(villes_uniques):
        coords[ville] = geocoder_ville(ville)
        if (i + 1) % 10 == 0:
            print(f"   → {i + 1}/{len(villes_uniques)} villes traitées...")

    # Ajouter les colonnes au DataFrame
    df["latitude"]  = df["ville"].map(lambda v: coords.get(v, {}).get("latitude"))
    df["longitude"] = df["ville"].map(lambda v: coords.get(v, {}).get("longitude"))

    geocodees = df["latitude"].notna().sum()
    print(f"✅ {geocodees}/{len(df)} offres géocodées avec succès")

    return df