# storage/load_silver_to_dwh.py
"""
Charge les données Silver vers le Data Warehouse PostgreSQL.
Version autonome : connexion directe, pas de dépendance circulaire.
"""
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text
import os, sys

# Configuration des chemins absolus
PROJECT_ROOT = Path(__file__).parent.parent
SILVER_CSV = PROJECT_ROOT / "data/silver/offres_silver.csv"

def generate_mock_data():
    """Génère un fichier Silver fictif pour permettre la démo Power BI."""
    print("⚠️  Fichier Silver introuvable. Génération de données de démo (Mock)...")
    os.makedirs(SILVER_CSV.parent, exist_ok=True)
    
    data = {
        "titre": ["Data Engineer", "Data Scientist", "Analyste BI", "DevOps", "Machine Learning Engineer"] * 10,
        "entreprise": ["TechCorp", "DataStart", "BigBank", "CloudCo", "AI Solutions"] * 10,
        "contrat_normalized": ["CDI"] * 25 + ["CDD"] * 15 + ["Stage"] * 10,
        "salaire_min": [45000, 55000, 40000, 50000, 60000] * 10,
        "salaire_max": [55000, 70000, 45000, 60000, 75000] * 10,
        "ville_clean": ["Paris"] * 20 + ["Lyon"] * 15 + ["Bordeaux"] * 10 + ["Nantes"] * 5,
        "region": ["Île-de-France"] * 20 + ["Auvergne-Rhône-Alpes"] * 15 + ["Nouvelle-Aquitaine"] * 10 + ["Pays de la Loire"] * 5,
        "skills_detected": ["python,sql,aws", "python,ml,pytorch", "sql,tableau,powerbi", "docker,k8s,terraform", "python,sql,spark"] * 10,
        "source": ["adzuna", "linkedin", "indeed", "remotive", "jobicy"] * 10
    }
    df = pd.DataFrame(data)
    df.to_csv(SILVER_CSV, index=False)
    print(f"✅ {len(df)} offres de démo créées dans {SILVER_CSV}")
    return df

def load_silver_to_dwh():
    """Charge le CSV Silver dans PostgreSQL (Star Schema)."""
    
    # 1. Vérifier/Générer le fichier
    if not SILVER_CSV.exists():
        df = generate_mock_data()
    else:
        print(f"📥 Chargement depuis {SILVER_CSV}...")
        df = pd.read_csv(SILVER_CSV)

    if df.empty:
        print("❌ DataFrame vide. Arrêt.")
        return

    # 2. Connexion DB DIRECTE (plus robuste que l'import de module)
    DB_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg2://airflow:airflow@localhost:5433/job_intelligent")
    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Connexion PostgreSQL établie.")
    except Exception as e:
        print(f"❌ Erreur connexion DB: {e}")
        print("💡 Vérifie que Docker est lancé: docker compose ps | grep postgres")
        return

    # 3. Chargement des données
    with engine.begin() as conn:
        print("🏗️  Chargement des Dimensions...")
        
        # Dim Source
        sources = df[["source"]].dropna().drop_duplicates().rename(columns={"source": "nom_source"})
        if not sources.empty:
            sources.to_sql("dim_source", conn, if_exists="append", index=False, method="multi")
            print(f"   ✅ dim_source: +{len(sources)} entrées")

        # Dim Contrat
        contrats = df[["contrat_normalized"]].dropna().drop_duplicates().rename(columns={"contrat_normalized": "type_contrat"})
        if not contrats.empty:
            contrats.to_sql("dim_contrat", conn, if_exists="append", index=False, method="multi")
            print(f"   ✅ dim_contrat: +{len(contrats)} entrées")

        # Dim Ville
        villes = df[["ville_clean", "region"]].dropna().drop_duplicates()
        villes["code_postal"] = "75000"
        villes = villes[["ville_clean", "code_postal", "region"]]
        if not villes.empty:
            villes.to_sql("dim_ville", conn, if_exists="append", index=False, method="multi")
            print(f"   ✅ dim_ville: +{len(villes)} entrées")

        # Dim Date (date du jour pour la démo)
        today = pd.Timestamp.today()
        dates = pd.DataFrame({
            "date_complete": [today.date()], 
            "annee": [today.year], 
            "mois": [today.month], 
            "trimestre": [f"Q{today.quarter}"]
        })
        dates.to_sql("dim_date", conn, if_exists="append", index=False, method="multi")
        print(f"   ✅ dim_date: +{len(dates)} entrées")

        print("🏗️  Chargement de la Table de Faits...")
        
        # Préparer les faits avec les colonnes attendues par ta table
        df_fact = pd.DataFrame()
        df_fact["titre"] = df["titre"]
        df_fact["entreprise"] = df["entreprise"]
        df_fact["salaire_min"] = df["salaire_min"]
        df_fact["salaire_max"] = df["salaire_max"]
        df_fact["skills_detected"] = df["skills_detected"]
        df_fact["source"] = df["source"]
        df_fact["type_contrat"] = df["contrat_normalized"]
        df_fact["ville"] = df["ville_clean"]
        df_fact["date"] = today.date()
        
        # Insertion dans fact_offres
        df_fact.to_sql("fact_offres", conn, if_exists="append", index=False, method="multi")
        print(f"   ✅ fact_offres: +{len(df_fact)} lignes insérées")

    print("\n🎉 Silver → DWH terminé avec succès !")
    print("🚀 Ouvre Power BI et actualise la source 'vw_offres_powerbi' ou 'fact_offres'.")

if __name__ == "__main__":
    load_silver_to_dwh()