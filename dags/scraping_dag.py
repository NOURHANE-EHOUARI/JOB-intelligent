from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os, sys

sys.path.insert(0, "/opt/airflow")

from dotenv import load_dotenv
load_dotenv()

default_args = {
    "owner": "hiba",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

BASE_PATH = "/opt/airflow"

# ─────────────────────────────────────────────────────────────
# Scrapers
# ──────────────────────────────────────────────────────────────

def run_adzuna():
    from scrapers.adzuna_scraper import AdzunaScraper
    from storage.raw_storage import save_offers
    scraper = AdzunaScraper(
        keywords=["data engineer", "data scientist", "data analyst"],
        location="Paris",
        app_id=os.getenv("ADZUNA_APP_ID"),
        app_key=os.getenv("ADZUNA_APP_KEY"),
        max_pages=5
    )
    offers = scraper.scrape()
    save_offers(offers, "adzuna")
    print(f"✅ Adzuna : {len(offers)} offres")
    return len(offers)

def run_france_travail():
    import importlib.util

    base = "/opt/airflow/france_travail"
    for module_name, filename in [
        ("auth", "auth.py"),
        ("client", "client.py"),
        ("normalizer", "normalizer.py")
    ]:
        spec = importlib.util.spec_from_file_location(module_name, os.path.join(base, filename))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod
        spec.loader.exec_module(mod)

    from client import search_offres
    from normalizer import normaliser_liste
    import pandas as pd

    METIERS = ["data scientist", "data engineer", "data analyst", "machine learning", "business intelligence"]
    toutes_offres = []
    for metier in METIERS:
        offres = search_offres(mots_cles=metier, max_offres=100)
        toutes_offres.extend(offres)
        print(f"   → {len(offres)} offres pour '{metier}'")

    df = normaliser_liste(toutes_offres)
    df = df.drop_duplicates(subset=["id"])
    df.to_csv(f"{base}/offres_france_travail.csv", index=False, encoding="utf-8-sig")
    print(f"✅ France Travail : {len(df)} offres")
    return len(df)

def run_arbeitnow():
    from scrapers.arbeitnow_client import collecter_arbeitnow
    df = collecter_arbeitnow()
    print(f"✅ Arbeitnow : {len(df)} offres")
    return len(df)

def run_findwork():
    from scrapers.findwork_scraper import FindworkScraper
    from storage.raw_storage import save_offers
    scraper = FindworkScraper(
        keywords=["data engineer", "data scientist", "data analyst"],
        max_pages=5
    )
    offers = scraper.scrape()
    save_offers(offers, "findwork")
    print(f"✅ Findwork : {len(offers)} offres")
    return len(offers)

def run_themuse():
    from scrapers.themuse_scraper import TheMuseScraper
    from storage.raw_storage import save_offers
    scraper = TheMuseScraper(
        keywords=["data engineer", "data scientist", "data analyst"],
        max_pages=5
    )
    offers = scraper.scrape()
    save_offers(offers, "themuse")
    print(f"✅ TheMuse : {len(offers)} offres")
    return len(offers)

def run_linkedin():
    from scrapers.linkedin_client import collecter_linkedin
    df = collecter_linkedin()
    print(f"✅ LinkedIn : {len(df)} offres")
    return len(df)

def run_jsearch():
    from scrapers.jsearch_client import collecter_indeed
    df = collecter_indeed()
    print(f"✅ JSearch/Indeed : {len(df)} offres")
    return len(df)

def run_remotive():
    from scrapers.remotive_scraper import RemotiveScraper
    from storage.raw_storage import save_offers
    scraper = RemotiveScraper(
        keywords=["data engineer", "data scientist", "data analyst"],
    )
    offers = scraper.scrape()
    save_offers(offers, "remotive")
    print(f"✅ Remotive : {len(offers)} offres")
    return len(offers)

def run_jobicy():
    from scrapers.jobicy_scraper import JobicyScraper
    from storage.raw_storage import save_offers
    scraper = JobicyScraper(
        keywords=["data engineer", "data scientist", "data analyst"],
    )
    offers = scraper.scrape()
    save_offers(offers, "jobicy")
    print(f"✅ Jobicy : {len(offers)} offres")
    return len(offers)

# ─────────────────────────────────────────────────────────────
# ETL
# ──────────────────────────────────────────────────────────────

def run_etl():
    os.chdir(BASE_PATH)
    from storage.etl import run_etl as etl
    etl()
    print("✅ ETL terminé — données chargées dans PostgreSQL")

# ──────────────────────────────────────────────────────────────
# Azure Upload — generic factory, one upload task per source
# ──────────────────────────────────────────────────────────────

def make_upload_task(source_name: str, scrape_task_id: str):
    """Returns an upload callable for a given source."""
    def upload_fn(**context):
        from storage.azure_storage import upload_scraper_output_to_bronze
        ti = context['ti']
        count = ti.xcom_pull(task_ids=scrape_task_id)
        if not count:
            print(f"⚠️ {source_name}: no data to upload (0 offres).")
            return
        exec_date = context['execution_date']
        path = upload_scraper_output_to_bronze(
            data=count,
            source=source_name,
            execution_date=exec_date
        )
        print(f"✅ {source_name} uploaded to Azure Bronze: {path}")
    upload_fn.__name__ = f"upload_{source_name}_fn"
    return upload_fn

# ──────────────────────────────────────────────────────────────
# SILVER TRANSFORM (Colleague Task)
# ──────────────────────────────────────────────────────────────

def run_silver_transform(**context):
    """Applique les règles Silver sur les données consolidées."""
    import pandas as pd
    import glob
    from utils.silver_transforms import transform_to_silver
    
    bronze_dir = os.path.join(BASE_PATH, "data", "bronze")
    silver_dir = os.path.join(BASE_PATH, "data", "silver")
    os.makedirs(silver_dir, exist_ok=True)
    
    # Agrège tous les fichiers Bronze
    csv_files = glob.glob(os.path.join(bronze_dir, "*.csv"))
    if not csv_files:
        print("⚠️ Aucun fichier Bronze trouvé. Skip Silver transform.")
        return
        
    print(f"📥 Chargement de {len(csv_files)} fichiers Bronze...")
    df_raw = pd.concat([pd.read_csv(f) for f in csv_files], ignore_index=True)
    
    # Applique la fonction orchestratrice créée précédemment
    df_silver = transform_to_silver(df_raw)
    
    output_path = os.path.join(silver_dir, "offres_silver.csv")
    df_silver.to_csv(output_path, index=False)
    print(f"✅ Silver transform terminé: {len(df_silver)} records sauvegardés.")

# ──────────────────────────────────────────────────────────────
# DAG
# ──────────────────────────────────────────────────────────────

with DAG(
    dag_id="job_scraping_dag",
    description="Scraping 9 sources + Azure Bronze upload + ETL PostgreSQL",
    default_args=default_args,
    start_date=datetime(2026, 4, 1),
    schedule_interval="0 8 * * *",
    catchup=False,
    tags=["scraping", "etl", "azure", "phase1"],
) as dag:

    # ── Scraper tasks ──
    t_adzuna         = PythonOperator(task_id="scrape_adzuna",         python_callable=run_adzuna)
    t_france_travail = PythonOperator(task_id="scrape_france_travail", python_callable=run_france_travail)
    t_arbeitnow      = PythonOperator(task_id="scrape_arbeitnow",      python_callable=run_arbeitnow)
    t_findwork       = PythonOperator(task_id="scrape_findwork",       python_callable=run_findwork)
    t_themuse        = PythonOperator(task_id="scrape_themuse",        python_callable=run_themuse)
    t_linkedin       = PythonOperator(task_id="scrape_linkedin",       python_callable=run_linkedin)
    t_jsearch        = PythonOperator(task_id="scrape_jsearch",        python_callable=run_jsearch)
    t_remotive       = PythonOperator(task_id="scrape_remotive",       python_callable=run_remotive)
    t_jobicy         = PythonOperator(task_id="scrape_jobicy",         python_callable=run_jobicy)

    # ── Azure Bronze upload tasks (one per source) ──
    t_upload_adzuna         = PythonOperator(task_id="upload_adzuna_bronze",         python_callable=make_upload_task("adzuna",         "scrape_adzuna"),         provide_context=True)
    t_upload_france_travail = PythonOperator(task_id="upload_france_travail_bronze", python_callable=make_upload_task("france_travail", "scrape_france_travail"), provide_context=True)
    t_upload_arbeitnow      = PythonOperator(task_id="upload_arbeitnow_bronze",      python_callable=make_upload_task("arbeitnow",      "scrape_arbeitnow"),      provide_context=True)
    t_upload_findwork       = PythonOperator(task_id="upload_findwork_bronze",       python_callable=make_upload_task("findwork",       "scrape_findwork"),       provide_context=True)
    t_upload_themuse        = PythonOperator(task_id="upload_themuse_bronze",        python_callable=make_upload_task("themuse",        "scrape_themuse"),        provide_context=True)
    t_upload_linkedin       = PythonOperator(task_id="upload_linkedin_bronze",       python_callable=make_upload_task("linkedin",       "scrape_linkedin"),       provide_context=True)
    t_upload_jsearch        = PythonOperator(task_id="upload_jsearch_bronze",        python_callable=make_upload_task("jsearch",        "scrape_jsearch"),        provide_context=True)
    t_upload_remotive       = PythonOperator(task_id="upload_remotive_bronze",       python_callable=make_upload_task("remotive",       "scrape_remotive"),       provide_context=True)
    t_upload_jobicy         = PythonOperator(task_id="upload_jobicy_bronze",         python_callable=make_upload_task("jobicy",         "scrape_jobicy"),         provide_context=True)

    # ── ETL task ──
    t_etl = PythonOperator(task_id="etl_postgresql", python_callable=run_etl)

    # ─ Silver Transform task (Colleague) ──
    transform_silver = PythonOperator(
        task_id='transform_silver',
        python_callable=run_silver_transform,
        provide_context=True,
        dag=dag
    )

    # ── Pipeline: each source follows scrape → upload → ETL ──
    #
    #  scrape_adzuna         → upload_adzuna_bronze         ─┐
    #  scrape_france_travail → upload_france_travail_bronze ─┤
    #  scrape_arbeitnow      → upload_arbeitnow_bronze      ┤
    #  scrape_findwork       → upload_findwork_bronze       ─┤→ etl_postgresql → transform_silver
    #  scrape_themuse        → upload_themuse_bronze        ─┤
    #  scrape_linkedin       → upload_linkedin_bronze       ─┤
    #  scrape_jsearch        → upload_jsearch_bronze        ─┤
    #  scrape_remotive       → upload_remotive_bronze       ─┤
    #  scrape_jobicy         → upload_jobicy_bronze         ─┘

    t_adzuna         >> t_upload_adzuna         >> t_etl
    t_france_travail >> t_upload_france_travail >> t_etl
    t_arbeitnow      >> t_upload_arbeitnow      >> t_etl
    t_findwork       >> t_upload_findwork       >> t_etl
    t_themuse        >> t_upload_themuse        >> t_etl
    t_linkedin       >> t_upload_linkedin       >> t_etl
    t_jsearch        >> t_upload_jsearch        >> t_etl
    t_remotive       >> t_upload_remotive       >> t_etl
    t_jobicy         >> t_upload_jobicy         >> t_etl

    # ─ Silver dependency ──
    t_etl >> transform_silver