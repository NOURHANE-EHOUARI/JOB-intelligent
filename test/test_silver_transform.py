"""
tests/test_silver_transform.py
Test unitaire & validation rapide du pipeline Silver
Colleague Task - Day 3 | FIXED: Mock data respects quality thresholds
"""
import pandas as pd
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.silver_transforms import transform_to_silver, load_business_rules

def test_silver_pipeline():
    print("🧪 Chargement des règles métier...")
    rules = load_business_rules()
    print("✅ Règles chargées.\n")

    # Données de test simulées (respectant min_description_length >= 50)
    data = {
        "titre": ["Data Scientist Senior", "Stage Data Analyst", "DevOps Freelance", "Court"],
        "entreprise": ["TechCorp", "StartupXYZ", "RemoteConsulting", "BadCo"],
        "ville": ["Paris 06", "Lyon, France", "Bordeaux", "X"],
        "code_postal": ["75006", "69001", "33000", "12345"],
        "contrat": ["CDI", "Stage PFE", "Freelance / Indépendant", "CDD"],
        "salaire": ["Mensuel de 4500€", "Non précisé", "80k-95k", "2000€/mois"],
        "description": [
            "Pandas, Python, SQL, AWS, Machine Learning en production avec des pipelines ETL robustes.",
            "Stage de 6 mois sur des projets de data science, analyse statistique et visualisation Power BI.",
            "Terraform, Kubernetes, CI/CD, Docker, monitoring Prometheus et gestion cloud AWS.",
            "Trop court."  # Sera filtré (titre < 10 & desc < 50)
        ],
        "url": ["https://techcorp.fr/1", "https://startup.fr/2", "https://remote.fr/3", "https://bad.fr/4"],
        "source": ["test", "test", "test", "test"]
    }
    df_raw = pd.DataFrame(data)
    print(f"📥 DataFrame brut: {len(df_raw)} lignes\n")

    # Exécution du pipeline Silver
    df_silver = transform_to_silver(df_raw, rules)
    
    print("📊 Résultat Silver:")
    cols = ["titre", "contrat_normalized", "salaire_min", "salaire_max", 
            "ville_clean", "code_postal_clean", "region", "skills_detected"]
    print(df_silver[cols].to_string(index=False))
    print(f"\n✅ Pipeline terminé: {len(df_silver)} lignes validées (sur {len(df_raw)})")
    
    # Assertions de validation
    assert len(df_silver) == 3, f"❌ Attendu 3 lignes, obtenu {len(df_silver)}. Vérifie les seuils qualité."
    
    # 1. Contrat
    assert df_silver.iloc[0]["contrat_normalized"] == "CDI"
    assert df_silver.iloc[1]["contrat_normalized"] == "STAGE"
    assert df_silver.iloc[2]["contrat_normalized"] == "FREELANCE"
    
    # 2. Salaire
    assert df_silver.iloc[0]["salaire_min"] == 54000.0  # 4500 * 12
    assert df_silver.iloc[2]["salaire_min"] == 80000.0  # 80k
    
    # 3. Lieu
    assert df_silver.iloc[0]["ville_clean"] == "Paris"
    assert df_silver.iloc[0]["code_postal_clean"] == "75006"
    assert df_silver.iloc[0]["region"] == "Île-de-France"
    
    # 4. Skills
    assert "python" in [s.lower() for s in df_silver.iloc[0]["skills_detected"]]
    assert "aws" in [s.lower() for s in df_silver.iloc[0]["skills_detected"]]
    
    print("\n✅ Toutes les assertions passées. Le pipeline Silver est fonctionnel.")

if __name__ == "__main__":
    test_silver_pipeline()