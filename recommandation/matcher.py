import pandas as pd
import re

def charger_offres():
    """Charge les offres enrichies de la phase 2."""
    df = pd.read_csv('data/silver/offres_silver.csv', low_memory=False)
    return df

def matcher_offres(profil: dict, df: pd.DataFrame, top_k: int = 10) -> pd.DataFrame:
    """
    Trouve les offres les plus pertinentes selon le profil candidat.
    profil = {
        "titre": "data scientist",
        "competences": ["python", "machine learning", "sql"],
        "experience": "2 ans",
        "contrat": "CDI",
        "ville": "Paris"
    }
    """
    scores = []

    titre_profil = profil.get("titre", "").lower()
    comp_profil  = [c.lower().strip() for c in profil.get("competences", [])]
    contrat      = profil.get("contrat", "").strip()
    ville        = profil.get("ville", "").lower().strip()

    for _, offre in df.iterrows():
        score = 0

        # ── Score titre (0-3 pts) ──────────────────
        titre_offre = str(offre.get("titre", "")).lower()
        for mot in titre_profil.split():
            if mot in titre_offre:
                score += 1

        # ── Score compétences (0-5 pts) ────────────
        comp_offre = str(offre.get("competences_extraites", "")).lower()
        desc_offre = str(offre.get("description", "")).lower()
        for comp in comp_profil:
            if comp in comp_offre or comp in desc_offre:
                score += 1

        # ── Score contrat (0-2 pts) ────────────────
        if contrat and contrat == str(offre.get("contrat", "")):
            score += 2

        # ── Score ville (0-2 pts) ──────────────────
        ville_offre = str(offre.get("ville", "")).lower()
        if ville and ville in ville_offre:
            score += 2

        scores.append(score)

    df = df.copy()
    df["score"] = scores
    df = df[df["score"] > 0]
    df = df.sort_values("score", ascending=False).head(top_k)
    df = df.reset_index(drop=True)

    return df
