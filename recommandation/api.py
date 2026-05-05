# recommandation/api.py — Pydantic V2 compatible (correct cross-field validation)
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from recommandation.similarity import recommend

app = FastAPI(
    title="Job Intelligent — API de recommandation",
    description="Recommande des offres d'emploi basées sur le profil candidat",
    version="1.1.0"
)

# ──────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────
class ProfilCandidat(BaseModel):
    """Accept profile (free-text) OR titre+competences (structured)."""
    titre: Optional[str] = None
    competences: Optional[str] = None
    profile: Optional[str] = None
    experience: str = ""
    top_k: int = Field(default=10, ge=1, le=50)
    
    @model_validator(mode='after')
    def ensure_input(self):
        """Ensure at least one input method is provided (cross-field validation)."""
        if not self.profile and not (self.titre or self.competences):
            raise ValueError("Provide either 'profile' OR 'titre'/'competences'")
        return self
    
    def get_query_text(self) -> str:
        """Build search query from whichever input was provided."""
        if self.profile and self.profile.strip():
            return self.profile.strip()
        parts = []
        if self.titre and self.titre.strip():
            parts.append(self.titre.strip())
        if self.competences and self.competences.strip():
            parts.extend([s.strip() for s in self.competences.split(",") if s.strip()])
        if self.experience and self.experience.strip():
            parts.append(self.experience.strip())
        return " ".join(parts)


class OffreRecommandee(BaseModel):
    id: str
    titre: str
    entreprise: str
    ville: str
    contrat: Optional[str]
    salaire: Optional[str]
    source: str
    score: float


# ──────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": "Job Intelligent API is running", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/recommander", response_model=List[OffreRecommandee])
def recommander(profil: ProfilCandidat):
    query_text = profil.get_query_text()
    results = recommend(
        profile={
            "titre": profil.titre or "",
            "competences": profil.competences or "",
            "experience": profil.experience,
        },
        top_k=profil.top_k
    )
    return results

@app.get("/debug")
def debug():
    """Simple debug endpoint."""
    import pickle
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    from sentence_transformers import SentenceTransformer
    
    with open("recommandation/cache/embeddings.pkl", "rb") as f:
        embeddings = pickle.load(f)
    
    model = SentenceTransformer("all-MiniLM-L6-v2")
    text = "Data Engineer Python SQL Spark Airflow"
    profile_emb = model.encode([text], normalize_embeddings=True)
    scores = cosine_similarity(profile_emb, embeddings)[0]
    top_idx = np.argsort(scores)[::-1][:3]
    
    return {
        "status": "ok",
        "embeddings_shape": list(embeddings.shape),
        "max_score": float(scores.max()),
        "mean_score": float(scores.mean()),
        "top_scores": [float(scores[i]) for i in top_idx],
        "test_query": text
    }
