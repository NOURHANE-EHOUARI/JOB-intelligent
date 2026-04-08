import requests
import time

CLIENT_ID     = "PAR_jobintelligent_80211c1113c3373a4217111e16d0220f5e1949b81328b2a3b3195de995ad208d"  
CLIENT_SECRET = "e41b35cb9d673c025d9f093c70dbbaece03a83785e5bf58a34fda950d5af474f"                 

TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"

_token_cache = {"access_token": None, "expires_at": 0}

def get_token():
    """Retourne un token valide, en le renouvelant si expiré."""
    if time.time() < _token_cache["expires_at"] - 30:
        return _token_cache["access_token"]

    response = requests.post(TOKEN_URL, data={
        "grant_type":    "client_credentials",
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope":         "api_offresdemploiv2 o2dsoffre"
    })

    response.raise_for_status()
    data = response.json()

    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"]   = time.time() + data["expires_in"]

    print("✅ Token obtenu avec succès")
    return _token_cache["access_token"]