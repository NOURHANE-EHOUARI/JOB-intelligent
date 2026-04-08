from client import search_offres
from normalizer import normaliser_liste
import pandas as pd
import os

# ─── Paramètres de recherche ───────────────────────────────────────
METIERS = [
    "data scientist",
    "data engineer",
    "data analyst",
    "machine learning",
    "business intelligence"
]

OUTPUT_FILE = "offres_france_travail.csv"

# ─── Pipeline principal ────────────────────────────────────────────
def main():
    print("🚀 Démarrage de la collecte France Travail...\n")
    toutes_offres = []

    for metier in METIERS:
        print(f"🔍 Recherche : {metier}")
        offres = search_offres(mots_cles=metier, max_offres=100)
        toutes_offres.extend(offres)
        print(f"   → {len(offres)} offres trouvées\n")

    # Normalisation
    print("⚙️  Normalisation des données...")
    df = normaliser_liste(toutes_offres)

    # Suppression des doublons globaux
    df = df.drop_duplicates(subset=["id"])
    print(f"📊 Total final : {len(df)} offres uniques\n")

    # Sauvegarde CSV
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"💾 Fichier sauvegardé : {OUTPUT_FILE}")
    print("\n✅ Collecte terminée avec succès !")
    print(df[["titre", "entreprise", "ville", "contrat", "salaire"]].head(10))

if __name__ == "__main__":
    main()