import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pickle
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from recommandation.vectorizer import get_or_build_embeddings
from utils.nlp_config import load_nlp_config  # ← AJOUT TÂCHE 4

MODEL_NAME = "all-MiniLM-L6-v2"

def encode_profile(profile: dict) -> np.ndarray:
    """Convert a candidate profile dict into an embedding vector."""
    model = SentenceTransformer(MODEL_NAME)
    text = (
        profile.get("titre", "") + " " +
        profile.get("competences", "") + " " +
        profile.get("experience", "")
    )
    return model.encode([text], normalize_embeddings=False)

def recommend(profile: dict, top_k: int = 10) -> list[dict]:
    df, embeddings = get_or_build_embeddings()
    profile_embedding = encode_profile(profile)

    scores = cosine_similarity(profile_embedding, embeddings)[0]
    top_indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for idx in top_indices:
        offer = df.iloc[int(idx)].to_dict()  # force int index
        offer["score"] = round(float(scores[int(idx)]), 4)
        results.append(offer)

    return results

# ──────────────────────────────────────────────────────────────
# AJOUT TÂCHE 4 : SCORING HYBRIDE & FILTRAGE PAR SEUILS
# ──────────────────────────────────────────────────────────────

def compute_hybrid_score(vector_score: float, keyword_overlap: float) -> float:
    """Combine cosine similarity + overlap de skills/titre selon poids YAML."""
    cfg = load_nlp_config()
    w = cfg["similarity_thresholds"]["hybrid_weights"]
    return w["vector"] * vector_score + w["keyword"] * keyword_overlap

def filter_by_threshold(scores: list[float], min_score: float = None) -> list[int]:
    """Retourne les indices des offres qui dépassent le seuil minimal."""
    cfg = load_nlp_config()
    threshold = min_score or cfg["similarity_thresholds"]["min_cosine"]
    return [i for i, s in enumerate(scores) if s >= threshold]

def get_top_k_indices(scores: list[float], k: int = None) -> list[int]:
    """Retourne les indices des k meilleures offres, filtrées par seuil."""
    cfg = load_nlp_config()
    k = k or cfg["similarity_thresholds"]["max_results"]
    valid_indices = filter_by_threshold(scores)
    sorted_indices = sorted(valid_indices, key=lambda i: scores[i], reverse=True)
    return sorted_indices[:k]

if __name__ == "__main__":
    profile = {
        "titre": "Data Engineer",
        "competences": "Python, SQL, Spark, Airflow, PostgreSQL",
        "experience": "3 ans d'expérience en data engineering et ETL"
    }
    results = recommend(profile, top_k=5)
    
    # ✅ Correction mineure pour que le script tourne (scores n'était pas défini ici à l'origine)
    top_scores = [r["score"] for r in results]
    print(f"Top scores: {top_scores}")
    print("\nTop 5 offres recommandées:\n")
    for i, r in enumerate(results, 1):
        print(f"{i}. {r['titre']} | {r['entreprise']} | {r['ville']} | score: {r['score']}")