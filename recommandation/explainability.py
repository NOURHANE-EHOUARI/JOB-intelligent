# recommandation/explainability.py
from utils.nlp_config import load_nlp_config

def generate_recommendation_reasons(offer_title: str, offer_skills: list, 
                                    candidate_skills: list, cosine_score: float) -> list[str]:
    """Génère 1 à 3 raisons explicables selon les règles YAML."""
    cfg = load_nlp_config()["explainability_rules"]
    reasons = []
    
    # 1. Match Skills
    matched_skills = [s for s in offer_skills if s.lower() in [c.lower() for c in candidate_skills]]
    if matched_skills:
        reasons.append(cfg["reason_templates"]["skill"].format(skills=", ".join(matched_skills[:3])))
        
    # 2. Similarité Sémantique
    if cosine_score >= cfg.get("semantic_threshold", 0.55):
        reasons.append(cfg["reason_templates"]["semantic"])
        
    # 3. Fallback générique
    if not reasons:
        reasons.append("Correspondance globale au profil")
        
    return reasons[:cfg["max_reasons"]]