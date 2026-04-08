import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pickle
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from recommandation.vectorizer import get_or_build_embeddings

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

if __name__ == "__main__":
    profile = {
        "titre": "Data Engineer",
        "competences": "Python, SQL, Spark, Airflow, PostgreSQL",
        "experience": "3 ans d'expérience en data engineering et ETL"
    }
    results = recommend(profile, top_k=5)
    print(f"Top scores: {sorted(scores, reverse=True)[:5]}")
    print("\nTop 5 offres recommandées:\n")
    for i, r in enumerate(results, 1):
        print(f"{i}. {r['titre']} | {r['entreprise']} | {r['ville']} | score: {r['score']}")
