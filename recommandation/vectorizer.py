import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pickle
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from storage.database import get_engine
import pandas as pd

MODEL_NAME = "all-MiniLM-L6-v2"  # lightweight, works in French + English
CACHE_DIR = Path("recommandation/cache")
CACHE_DIR.mkdir(exist_ok=True)

def load_offers_from_db() -> pd.DataFrame:
    engine = get_engine()
    query = """
        SELECT id, titre, entreprise, ville, contrat, 
               salaire, competences, description, source
        FROM offres_emploi
    """
    df = pd.read_sql(query, engine)
    df["text"] = (
        df["titre"].fillna("") + " " +
        df["competences"].fillna("") + " " +
        df["description"].fillna("")
    )
    print(f"Loaded {len(df)} offers from DB.")
    return df

def build_embeddings(df: pd.DataFrame) -> np.ndarray:
    print("Loading sentence-transformer model...")
    model = SentenceTransformer(MODEL_NAME)
    print("Building embeddings...")
    embeddings = model.encode(
      df["text"].tolist(),
      show_progress_bar=True,
      batch_size=32,
      normalize_embeddings=False
    )
    with open(CACHE_DIR / "embeddings.pkl", "wb") as f:
        pickle.dump(embeddings, f)
    with open(CACHE_DIR / "offers_df.pkl", "wb") as f:
        pickle.dump(df, f)
    print(f"Embeddings built and cached: {embeddings.shape}")
    return embeddings

def load_cached_embeddings():
    emb_path = CACHE_DIR / "embeddings.pkl"
    df_path = CACHE_DIR / "offers_df.pkl"
    if emb_path.exists() and df_path.exists():
        with open(emb_path, "rb") as f:
            embeddings = pickle.load(f)
        with open(df_path, "rb") as f:
            df = pickle.load(f)
        print(f"Loaded cached embeddings: {embeddings.shape}")
        return df, embeddings
    return None, None

def get_or_build_embeddings():
    df, embeddings = load_cached_embeddings()
    if df is None:
        df = load_offers_from_db()
        embeddings = build_embeddings(df)
    return df, embeddings

if __name__ == "__main__":
    df = load_offers_from_db()
    build_embeddings(df)
