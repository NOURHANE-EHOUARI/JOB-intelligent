import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from pydantic import BaseModel
from recommandation.similarity import recommend

app = FastAPI(
    title="Job Intelligent — API de recommandation",
    description="Recommande des offres d'emploi basées sur le profil candidat",
    version="1.0.0"
)

class ProfilCandidat(BaseModel):
    titre: str
    competences: str
    experience: str = ""
    top_k: int = 10

class OffreRecommandee(BaseModel):
    id: str
    titre: str
    entreprise: str
    ville: str
    contrat: str | None
    salaire: str | None
    source: str
    score: float

@app.get("/")
def root():
    return {"message": "Job Intelligent API is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/recommander", response_model=list[OffreRecommandee])
def recommander(profil: ProfilCandidat):
    print(f"Profile received: {profil}")  # add this
    results = recommend(
        profile={
            "titre": profil.titre,
            "competences": profil.competences,
            "experience": profil.experience,
        },
        top_k=profil.top_k
    )
    print(f"Top 3 scores: {[r['score'] for r in results[:3]]}")  # add this
    return results

@app.get("/debug")
def debug():
    import pickle, numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    from sentence_transformers import SentenceTransformer
    
    with open("recommandation/cache/embeddings.pkl", "rb") as f:
        embeddings = pickle.load(f)
    
    model = SentenceTransformer("all-MiniLM-L6-v2")
    text = "Data Engineer Python SQL Spark Airflow"
    profile_emb = model.encode([text], normalize_embeddings=False)
    scores = cosine_similarity(profile_emb, embeddings)[0]
    top_idx = np.argsort(scores)[::-1][:3]
    
    return {
        "max_score": float(scores.max()),
        "mean_score": float(scores.mean()),
        "embeddings_shape": list(embeddings.shape),
        "top_scores": [float(scores[i]) for i in top_idx]
    }
