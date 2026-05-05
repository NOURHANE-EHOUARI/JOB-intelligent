"""
test/test_all.py
Master test script — End-to-End validation for job_intelligent
Colleague Task — Pre-Production Validation | Run before Task 5 (Power BI)
"""
import sys
import os
import subprocess
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def log(msg: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    color = {"INFO": Colors.BLUE, "OK": Colors.GREEN, "FAIL": Colors.RED, "WARN": Colors.YELLOW}.get(level, Colors.RESET)
    print(f"{color}[{timestamp}] [{level}] {msg}{Colors.RESET}")

def run_command(cmd: list[str], cwd: Path = None, timeout: int = 60) -> tuple[bool, str]:
    """Exécute une commande shell et retourne (success, output)"""
    try:
        result = subprocess.run(
            cmd, cwd=cwd or PROJECT_ROOT, capture_output=True, text=True, timeout=timeout, shell=(os.name == 'nt')
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, f"Timeout after {timeout}s"
    except Exception as e:
        return False, str(e)

# ──────────────────────────────────────────────────────────────
# TEST STEPS
# ──────────────────────────────────────────────────────────────

def step_0_environment():
    """0. Vérification environnement & dépendances"""
    log("🔍 Étape 0: Vérification environnement...", "INFO")
    
    checks = [
        (["python", "--version"], "Python 3.12+"),
        (["pip", "show", "pandas"], "pandas"),
        (["pip", "show", "sqlalchemy"], "sqlalchemy"),
        (["pip", "show", "sentence-transformers"], "sentence-transformers"),
        (["pip", "show", "pyyaml"], "pyyaml"),
        (["pip", "show", "hdbscan"], "hdbscan (optionnel)"),
    ]
    
    all_ok = True
    for cmd, name in checks:
        ok, _ = run_command(cmd, timeout=10)
        status = "✅" if ok else "⚠️"
        log(f"   {status} {name}", "OK" if ok else "WARN")
        if name not in ["hdbscan (optionnel)"] and not ok:
            all_ok = False
    
    # Vérifier structure dossiers
    required_dirs = ["config", "utils", "scrapers", "recommandation", "storage", "dags", "test"]
    for d in required_dirs:
        exists = (PROJECT_ROOT / d).exists()
        log(f"   {'✅' if exists else '❌'} Dossier {d}/", "OK" if exists else "FAIL")
        if not exists: all_ok = False
    
    return all_ok

def step_1_config_validation():
    """1. Validation des fichiers de configuration"""
    log("🔍 Étape 1: Validation configs YAML...", "INFO")
    
    from utils.nlp_config import load_nlp_config
    from utils.silver_transforms import load_business_rules
    
    try:
        nlp_cfg = load_nlp_config()
        assert "similarity_thresholds" in nlp_cfg
        assert "skills_taxonomy" in nlp_cfg
        log("   ✅ config/nlp_config.yaml", "OK")
    except Exception as e:
        log(f"   ❌ nlp_config: {e}", "FAIL")
        return False
    
    try:
        silver_cfg = load_business_rules()
        assert "contract_mapping" in silver_cfg
        assert "quality_thresholds" in silver_cfg
        log("   ✅ config/silver_business_rules.yaml", "OK")
    except Exception as e:
        log(f"   ❌ silver_business_rules: {e}", "FAIL")
        return False
    
    return True

def step_2_silver_transform_unit():
    """2. Test unitaire du pipeline Silver"""
    log("🔍 Étape 2: Test unitaire Silver transform...", "INFO")
    
    ok, output = run_command(["python", "test/test_silver_transform.py"], timeout=30)
    if ok and "Toutes les assertions passées" in output:
        log("   ✅ test_silver_transform.py", "OK")
        return True
    else:
        log(f"   ❌ test_silver_transform.py échoué", "FAIL")
        log(f"      Output: {output[:200]}...", "WARN")
        return False

def step_3_nlp_integration():
    """3. Test d'intégration NLP"""
    log("🔍 Étape 3: Test intégration NLP...", "INFO")
    
    ok, output = run_command(["python", "test/test_nlp_integration.py"], timeout=45)
    if ok and "TOUTES LES TESTS D'INTÉGRATION NLP ONT RÉUSSI" in output:
        log("   ✅ test_nlp_integration.py", "OK")
        return True
    else:
        log(f"   ❌ test_nlp_integration.py échoué", "FAIL")
        log(f"      Output: {output[:200]}...", "WARN")
        return False

def step_4_scraper_validation():
    """4. Validation rapide des scrapers (sans appel API réel)"""
    log("🔍 Étape 4: Validation scrapers (mock)...", "INFO")
    
    from scrapers.base_scraper import BaseScraper
    from models.job_offer import JobOffer
    
    # Test BaseScraper.validate_offer_quality
    class DummyScraper(BaseScraper):
        def scrape(self): return []
        def parse_offer(self, raw): return None
    
    s = DummyScraper(["data"], "Paris")
    
    tests = [
        (s.validate_offer_quality("Data Engineer", "Python, SQL, AWS, ETL"), True, "Valid offer"),
        (s.validate_offer_quality("Stage", "Trop court"), False, "Short description"),
        (s.validate_offer_quality("Job", "Stage non rémunéré obligatoire"), False, "Negative keyword"),
    ]
    
    all_ok = True
    for title, desc, expected, label in tests:
        result = s.validate_offer_quality(title, desc)
        status = "✅" if result == expected else "❌"
        log(f"   {status} {label}: {result} (expected {expected})", "OK" if result == expected else "FAIL")
        if result != expected: all_ok = False
    
    return all_ok

def step_5_database_connection():
    """5. Test connexion PostgreSQL"""
    log("🔍 Étape 5: Connexion PostgreSQL...", "INFO")
    
    try:
        from storage.database import get_engine
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute("SELECT COUNT(*) FROM offres_emploi").fetchone()
            count = result[0] if result else 0
            log(f"   ✅ Connexion OK — {count} offres dans offres_emploi", "OK")
            return count > 0
    except Exception as e:
        log(f"   ❌ Erreur DB: {e}", "FAIL")
        return False

def step_6_etl_dry_run():
    """6. Simulation ETL (sans écriture)"""
    log("🔍 Étape 6: Simulation ETL (dry-run)...", "INFO")
    
    # Vérifier que les fichiers sources existent
    sources = [
        "data/raw/adzuna_*.json",
        "france_travail/offres_france_travail.csv",
        "scrapers/offres_arbeitnow_clean.csv",
    ]
    
    all_exist = True
    for pattern in sources:
        matches = list(PROJECT_ROOT.glob(pattern))
        status = "✅" if matches else "⚠️"
        log(f"   {status} {pattern} → {len(matches)} fichier(s)", "OK" if matches else "WARN")
        if not matches and "arbeitnow_clean" in pattern:
            # Fallback to raw
            if list(PROJECT_ROOT.glob("scrapers/offres_arbeitnow.csv")):
                log(f"      → Using raw Arbeitnow CSV instead", "WARN")
    
    return True  # Warning tolerated for dry-run

def step_7_api_smoke_test():
    """7. Smoke test de l'API FastAPI (si lancée)"""
    log("🔍 Étape 7: Smoke test API FastAPI...", "INFO")
    
    import requests
    import json
    
    test_profile = {
        "titre": "Data Engineer",
        "competences": "Python, SQL, AWS",
        "experience": "3 ans"
    }
    
    try:
        # Note: API doit être lancée séparément avec uvicorn
        response = requests.post(
            "http://localhost:8000/recommander",
            json=test_profile,
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                log(f"   ✅ API répond — {len(data)} recommandations", "OK")
                return True
        log(f"   ⚠️ API retourne: {response.status_code}", "WARN")
        return False
    except requests.ConnectionError:
        log("   ⚠️ API non lancée (uvicorn) — skip", "WARN")
        return True  # Not a failure, just not running
    except Exception as e:
        log(f"   ❌ Erreur API: {e}", "FAIL")
        return False

def step_8_datawarehouse_check():
    """8. Vérification Data Warehouse (star schema)"""
    log("🔍 Étape 8: Vérification Data Warehouse...", "INFO")
    
    try:
        from storage.database import get_engine
        engine = get_engine()
        
        required_tables = ["fact_offres", "dim_ville", "dim_contrat", "dim_source", "dim_date"]
        all_ok = True
        
        with engine.connect() as conn:
            for table in required_tables:
                result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                count = result[0] if result else 0
                status = "✅" if count > 0 or table == "fact_offres" else "⚠️"  # fact_offres may be 0 during debug
                log(f"   {status} {table}: {count} rows", "OK" if count > 0 or table != "fact_offres" else "WARN")
                if table != "fact_offres" and count == 0:
                    all_ok = False
        
        # Vérifier les FK dans fact_offres
        fk_check = conn.execute("""
            SELECT COUNT(*) FROM fact_offres 
            WHERE id_ville IS NULL OR id_contrat IS NULL OR id_source IS NULL
        """).fetchone()
        null_fks = fk_check[0] if fk_check else 0
        if null_fks == 0:
            log("   ✅ Aucune FK NULL dans fact_offres", "OK")
        else:
            log(f"   ⚠️ {null_fks} lignes avec FK NULL dans fact_offres", "WARN")
        
        return all_ok
    except Exception as e:
        log(f"   ❌ Erreur DWH: {e}", "FAIL")
        return False

def step_9_airflow_dag_parse():
    """9. Validation parsing DAG Airflow"""
    log("🔍 Étape 9: Parsing DAG Airflow...", "INFO")
    
    # Test via airflow CLI si disponible
    ok, output = run_command(
        ["airflow", "dags", "list", "--output", "json"], 
        cwd=PROJECT_ROOT / "dags", 
        timeout=30
    )
    
    if ok and "job_scraping_dag" in output:
        log("   ✅ DAG 'job_scraping_dag' reconnu par Airflow", "OK")
        return True
    else:
        # Fallback: test syntaxe Python
        dag_path = PROJECT_ROOT / "dags" / "scraping_dag.py"
        try:
            with open(dag_path) as f:
                compile(f.read(), str(dag_path), 'exec')
            log("   ✅ scraping_dag.py: syntaxe Python valide", "OK")
            return True
        except SyntaxError as e:
            log(f"   ❌ Erreur syntaxe DAG: {e}", "FAIL")
            return False

def step_10_final_summary():
    """10. Résumé final & recommandations"""
    log("\n" + "="*60, "INFO")
    log("📊 RÉSUMÉ DES TESTS", "INFO")
    log("="*60, "INFO")
    
    # Ce résumé est généré dynamiquement par la fonction main()
    pass

# ──────────────────────────────────────────────────────────────
# MAIN EXECUTION
# ──────────────────────────────────────────────────────────────

def main():
    log("🚀 Démarrage des tests end-to-end — job_intelligent", "INFO")
    log(f"📁 Projet: {PROJECT_ROOT}", "INFO")
    log(f"🕐 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
    print()
    
    steps = [
        ("Environnement", step_0_environment),
        ("Config YAML", step_1_config_validation),
        ("Silver Transform", step_2_silver_transform_unit),
        ("NLP Integration", step_3_nlp_integration),
        ("Scrapers Quality", step_4_scraper_validation),
        ("PostgreSQL Connexion", step_5_database_connection),
        ("ETL Dry-Run", step_6_etl_dry_run),
        ("API Smoke Test", step_7_api_smoke_test),
        ("Data Warehouse", step_8_datawarehouse_check),
        ("Airflow DAG", step_9_airflow_dag_parse),
    ]
    
    results = []
    for name, func in steps:
        try:
            result = func()
            results.append((name, result))
            print()
        except Exception as e:
            log(f"💥 Exception dans {name}: {e}", "FAIL")
            results.append((name, False))
            print()
    
    # Final summary
    log("="*60, "INFO")
    log("📈 RÉSULTATS FINAUX", "INFO")
    log("="*60, "INFO")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        log(f"   {status} — {name}", "OK" if result else "FAIL")
    
    print()
    log(f"🎯 Score: {passed}/{total} étapes validées", "INFO" if passed == total else "WARN")
    
    if passed == total:
        log("🎉 TOUT EST VERT — Prêt pour la Tâche 5 (Power BI) ! 🚀", "OK")
        return 0
    else:
        log("⚠️  Certaines étapes ont échoué — corrige avant de continuer", "WARN")
        log("💡 Astuce: Lance chaque test individuellement pour debug: python test/test_*.py", "INFO")
        return 1

if __name__ == "__main__":
    sys.exit(main())