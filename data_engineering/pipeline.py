import pandas as pd
import sys
import os

# Ajouter le dossier phase1 au path pour importer le CSV
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'phase1_france_travail'))

from skill_extractor import enrichir_dataframe
from geocoder import enrichir_coordonnees
from quality_check import verifier_qualite

INPUT_FILE  = "../france_travail/offres_france_travail.csv"
OUTPUT_FILE = "offres_enrichies.csv"

def run_pipeline():
    print("🚀 Démarrage du pipeline Phase 2...\n")

    # ── Étape 1 : Charger les données ───────────────
    print("📂 Chargement des données...")
    df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")
    print(f"✅ {len(df)} offres chargées\n")

    # ── Étape 2 : Extraction des compétences ────────
    df = enrichir_dataframe(df)

    # ── Étape 3 : Géocodage des villes ──────────────
    df = enrichir_coordonnees(df)

    # ── Étape 4 : Contrôle qualité ──────────────────
    df = verifier_qualite(df)

    # ── Étape 5 : Sauvegarde ────────────────────────
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"💾 Fichier sauvegardé : {OUTPUT_FILE}")
    

if __name__ == "__main__":
    run_pipeline()