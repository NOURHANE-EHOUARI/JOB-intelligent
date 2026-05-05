"""
test/test_nlp_integration.py
Validation complète de l'intégration NLP (Tâche 4)
Colleague Task - Day 4 | Production Ready
"""
import sys
from pathlib import Path

# Ajout du path racine pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.nlp_config import load_nlp_config
from recommandation.similarity import compute_hybrid_score, filter_by_threshold, get_top_k_indices
from recommandation.explainability import generate_recommendation_reasons


def test_nlp_config_loading():
    """Test 1: Chargement et validation de la config YAML"""
    print("🧪 Test 1: Chargement config NLP...")
    cfg = load_nlp_config()
    
    # Vérifications structurelles
    assert "job_categories" in cfg, "❌ job_categories manquant"
    assert "skills_taxonomy" in cfg, "❌ skills_taxonomy manquant"
    assert "similarity_thresholds" in cfg, "❌ similarity_thresholds manquant"
    assert "clustering_config" in cfg, "❌ clustering_config manquant"
    assert "scraping_filters" in cfg, "❌ scraping_filters manquant"
    assert "explainability_rules" in cfg, "❌ explainability_rules manquant"
    
    # Vérifications valeurs clés
    assert cfg["similarity_thresholds"]["min_cosine"] == 0.40
    assert cfg["clustering_config"]["algorithm"] == "hdbscan"
    assert len(cfg["negative_keywords"]) > 0
    assert "python" in [s.lower() for s in cfg["skills_taxonomy"]["hard_skills"]["technical"]]
    
    print("✅ Config NLP chargée et validée.")
    return cfg


def test_hybrid_scoring():
    """Test 2: Calcul du score hybride (vector + keyword)"""
    print("\n🧪 Test 2: Scoring hybride...")
    
    # Cas 1: Scores équilibrés
    score1 = compute_hybrid_score(0.60, 0.40)
    assert 0.50 < score1 < 0.65, f"❌ Score hors plage attendue: {score1}"
    print(f"   → Score équilibré (0.60, 0.40): {score1:.3f} ✅")
    
    # Cas 2: Vector fort, keyword faible
    score2 = compute_hybrid_score(0.70, 0.20)
    assert score2 > 0.55, f"❌ Score trop bas: {score2}"
    print(f"   → Vector fort (0.70, 0.20): {score2:.3f} ✅")
    
    # Cas 3: Vector faible, keyword fort (fallback)
    score3 = compute_hybrid_score(0.35, 0.80)
    assert 0.40 <= score3 <= 0.60, f"❌ Score inattendu: {score3}"
    print(f"   → Keyword fort fallback (0.35, 0.80): {score3:.3f} ✅")
    
    print("✅ Scoring hybride fonctionnel.")


def test_threshold_filtering():
    """Test 3: Filtrage par seuils de similarité"""
    print("\n🧪 Test 3: Filtrage par seuils...")
    
    scores = [0.25, 0.38, 0.42, 0.51, 0.58, 0.63, 0.71, 0.33]
    
    # Filtrage avec seuil par défaut (0.40)
    valid = filter_by_threshold(scores)
    assert len(valid) == 5, f"❌ Attendu 5 indices valides, obtenu {len(valid)}"
    assert 0 not in valid and 1 not in valid, "❌ Scores < 0.40 non filtrés"
    print(f"   → Seuils par défaut: {len(valid)}/{len(scores)} offres valides ✅")
    
    # Filtrage avec seuil personnalisé (0.55)
    strict = filter_by_threshold(scores, min_score=0.55)
    assert len(strict) == 3, f"❌ Attendu 3 indices stricts, obtenu {len(strict)}"
    print(f"   → Seuils stricts (0.55): {len(strict)}/{len(scores)} offres valides ✅")
    
    # Top-K avec filtrage
    top3 = get_top_k_indices(scores, k=3)
    assert len(top3) == 3, f"❌ Top-3 devrait retourner 3 indices"
    assert top3[0] == 6, f"❌ Premier indice devrait être 6 (score 0.71), obtenu {top3[0]}"
    print(f"   → Top-3 indices: {top3} (scores: {[scores[i] for i in top3]}) ✅")
    
    print("✅ Filtrage par seuils fonctionnel.")


def test_explainability_generation():
    """Test 4: Génération des raisons de recommandation"""
    print("\n🧪 Test 4: Explicabilité des recommandations...")
    
    # Cas 1: Match skills fort
    reasons1 = generate_recommendation_reasons(
        offer_title="Data Engineer Senior",
        offer_skills=["python", "sql", "aws", "airflow", "spark"],
        candidate_skills=["python", "sql", "docker"],
        cosine_score=0.62
    )
    assert len(reasons1) <= 3, "❌ Trop de raisons générées"
    assert any("skill" in r.lower() or "correspondance" in r.lower() for r in reasons1), "❌ Aucune raison skill détectée"
    print(f"   → Match skills: {reasons1} ✅")
    
    # Cas 2: Similarité sémantique élevée, peu de skills match
    reasons2 = generate_recommendation_reasons(
        offer_title="ML Engineer",
        offer_skills=["pytorch", "tensorflow", "cuda"],
        candidate_skills=["python", "scikit-learn"],
        cosine_score=0.68
    )
    assert any("sémantique" in r.lower() or "similarité" in r.lower() for r in reasons2), "❌ Raison sémantique manquante"
    print(f"   → Similarité sémantique: {reasons2} ✅")
    
    # Cas 3: Fallback générique
    reasons3 = generate_recommendation_reasons(
        offer_title="Stage Data",
        offer_skills=[],
        candidate_skills=["excel"],
        cosine_score=0.35
    )
    assert len(reasons3) >= 1, "❌ Aucune raison de fallback"
    print(f"   → Fallback: {reasons3} ✅")
    
    print("✅ Génération d'explicabilité fonctionnelle.")


def test_scraping_filters():
    """Test 5: Validation des filtres de scraping (via config)"""
    print("\n🧪 Test 5: Filtres de scraping...")
    
    cfg = load_nlp_config()
    filters = cfg["scraping_filters"]
    negatives = cfg["negative_keywords"]
    
    # Test longueur description
    assert filters["description_min_length"] >= 50, "❌ Seuil description trop bas"
    
    # Test mots-clés requis
    assert len(filters["required_tech_keywords"]) > 0, "❌ Aucun keyword technique requis"
    assert "python" in [k.lower() for k in filters["required_tech_keywords"]]
    
    # Test negative keywords
    assert "stage non rémunéré" in [n.lower() for n in negatives], "❌ Keyword négatif manquant"
    
    print("✅ Filtres de scraping configurés correctement.")


def run_all_tests():
    """Exécute tous les tests d'intégration NLP"""
    print("🚀 Démarrage des tests d'intégration NLP (Tâche 4)\n")
    print("=" * 60)
    
    try:
        test_nlp_config_loading()
        test_hybrid_scoring()
        test_threshold_filtering()
        test_explainability_generation()
        test_scraping_filters()
        
        print("\n" + "=" * 60)
        print("🎉 TOUTES LES TESTS D'INTÉGRATION NLP ONT RÉUSSI ✅")
        print("=" * 60)
        return True
        
    except AssertionError as e:
        print(f"\n❌ ÉCHEC DU TEST: {e}")
        return False
    except Exception as e:
        print(f"\n💥 ERREUR INATTENDUE: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)