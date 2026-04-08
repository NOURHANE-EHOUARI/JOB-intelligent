import re

# Liste de compétences tech du domaine Data
COMPETENCES_DATA = [
    # Langages
    "python", "r", "sql", "scala", "java", "julia",
    # Big Data
    "spark", "hadoop", "kafka", "airflow", "dbt", "hive",
    # Cloud
    "aws", "azure", "gcp", "google cloud", "databricks", "snowflake",
    # Bases de données
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    # ML / IA
    "machine learning", "deep learning", "nlp", "tensorflow", "pytorch",
    "scikit-learn", "keras", "huggingface", "llm",
    # Viz / BI
    "power bi", "tableau", "looker", "qlik", "matplotlib", "seaborn",
    # Data Engineering
    "etl", "pipeline", "docker", "kubernetes", "git", "api",
    # Stats
    "statistiques", "modélisation", "régression", "clustering"
]

def extraire_competences(texte: str) -> list:
    """
    Extrait les compétences présentes dans un texte.
    """
    if not texte or texte == "Non précisé":
        return []

    texte_lower = texte.lower()
    trouvees = []

    for comp in COMPETENCES_DATA:
        # Cherche le mot complet (pas juste une partie)
        pattern = r'\b' + re.escape(comp) + r'\b'
        if re.search(pattern, texte_lower):
            trouvees.append(comp)

    return trouvees

def enrichir_dataframe(df):
    """
    Ajoute une colonne 'competences_extraites' au DataFrame.
    """
    import pandas as pd

    print("⚙️  Extraction des compétences en cours...")

    df["competences_extraites"] = df["description"].apply(
        lambda x: ", ".join(extraire_competences(str(x)))
    )

    # Stats rapides
    total = df["competences_extraites"].apply(
        lambda x: len(x.split(", ")) if x else 0
    ).sum()

    print(f"✅ {total} compétences extraites sur {len(df)} offres")
    return df