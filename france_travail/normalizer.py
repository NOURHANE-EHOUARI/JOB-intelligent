import pandas as pd

# Mapping des types de contrats
CONTRATS = {
    "CDI": "CDI",
    "CDD": "CDD",
    "MIS": "Mission intérimaire",
    "SAI": "Saisonnier",
    "CCE": "Profession commerciale",
    "FRA": "Franchise",
    "LIB": "Libéral",
    "REP": "Reprise d'entreprise",
    "TTI": "Temps partiel",
    "DIN": "CDI Intérimaire"
}

def normaliser_offre(offre: dict) -> dict:
    """
    Prend une offre brute de l'API France Travail
    et retourne un dictionnaire normalisé et propre.
    """

    # Localisation
    lieu = offre.get("lieuTravail", {})
    ville = lieu.get("libelle", "Non précisé")
    code_postal = lieu.get("codePostal", "")

    # Contrat
    type_contrat_raw = offre.get("typeContrat", "")
    type_contrat = CONTRATS.get(type_contrat_raw, type_contrat_raw)

    # Salaire
    salaire_info = offre.get("salaire", {})
    salaire = salaire_info.get("libelle", "Non précisé")

    # Compétences
    competences = [c.get("libelle", "") for c in offre.get("competences", [])]

    # Expérience
    experience = offre.get("experienceLibelle", "Non précisé")

    return {
        "id":           offre.get("id", ""),
        "titre":        offre.get("intitule", "").strip().title(),
        "entreprise":   offre.get("entreprise", {}).get("nom", "Non précisé"),
        "ville":        ville,
        "code_postal":  code_postal,
        "contrat":      type_contrat,
        "salaire":      salaire,
        "experience":   experience,
        "competences":  ", ".join(competences),
        "description":  offre.get("description", "")[:2000],  # limité à 500 chars
        "date_publication": offre.get("dateCreation", "")[:10],
        "url":          offre.get("origineOffre", {}).get("urlOrigine", ""),
        "source":       "France Travail"
    }

def normaliser_liste(offres: list) -> pd.DataFrame:
    """
    Normalise une liste d'offres brutes et retourne un DataFrame propre.
    """
    normalisees = [normaliser_offre(o) for o in offres]
    df = pd.DataFrame(normalisees)

    # Supprimer les doublons sur l'id
    df = df.drop_duplicates(subset=["id"])

    # Nettoyer les valeurs vides
    df = df.fillna("Non précisé")

    print(f"✅ {len(df)} offres normalisées")
    return df