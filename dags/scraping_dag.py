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

# ──────────────────────────────────────────────────────────────
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

def run_france_travail():
    import importlib.util, sys, os

    base = f"{BASE_PATH}/france_travail"
    for module_name, filename in [("client", "client.py"), ("normalizer", "normalizer.py")]:
        spec = importlib.util.spec_from_file_location(
            module_name, os.path.join(base, filename)
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod
        spec.loader.exec_module(mod)

    from client import search_offres
    from normalizer import normaliser_liste

    METIERS = [
        "data scientist", "data engineer", "data analyst",
        "machine learning", "business intelligence"
    ]
    toutes_offres = []
    for metier in METIERS:
        offres = search_offres(mots_cles=metier, max_offres=100)
        toutes_offres.extend(offres)
        print(f"   → {len(offres)} offres pour '{metier}'")

    df = normaliser_liste(toutes_offres)
    df = df.drop_duplicates(subset=["id"])
    df.to_csv(f"{BASE_PATH}/france_travail/offres_france_travail.csv", index=False, encoding="utf-8-sig")
    print(f"✅ France Travail : {len(df)} offres")

def run_arbeitnow():
    from scrapers.arbeitnow_client import collecter_arbeitnow
    df = collecter_arbeitnow()
    print(f"✅ Arbeitnow : {len(df)} offres")

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

def run_linkedin():
    from scrapers.linkedin_client import collecter_linkedin
    df = collecter_linkedin()
    print(f"✅ LinkedIn : {len(df)} offres")

def run_jsearch():
    from scrapers.jsearch_client import collecter_indeed
    df = collecter_indeed()
    print(f"✅ JSearch/Indeed : {len(df)} offres")

def run_remotive():
    from scrapers.remotive_scraper import RemotiveScraper
    from storage.raw_storage import save_offers
    scraper = RemotiveScraper(
        keywords=["data engineer", "data scientist", "data analyst"],
    )
    offers = scraper.scrape()
    save_offers(offers, "remotive")
    print(f"✅ Remotive : {len(offers)} offres")

def run_jobicy():
    from scrapers.jobicy_scraper import JobicyScraper
    from storage.raw_storage import save_offers
    scraper = JobicyScraper(
        keywords=["data engineer", "data scientist", "data analyst"],
    )
    offers = scraper.scrape()
    save_offers(offers, "jobicy")
    print(f"✅ Jobicy : {len(offers)} offres")

# ──────────────────────────────────────────────────────────────
# ETL
# ──────────────────────────────────────────────────────────────

def run_etl():
    # Forcer les chemins absolus pour Airflow
    import os
    os.chdir(BASE_PATH)
    from storage.etl import run_etl as etl
    etl()
    print("✅ ETL terminé — données chargées dans PostgreSQL")

# ──────────────────────────────────────────────────────────────
# DAG
# ──────────────────────────────────────────────────────────────

with DAG(
    dag_id="job_scraping_dag",
    description="Scraping 9 sources + ETL PostgreSQL",
    default_args=default_args,
    start_date=datetime(2026, 4, 1),
    schedule_interval="0 8 * * *",  # tous les jours à 8h
    catchup=False,
    tags=["scraping", "etl", "phase1"],
) as dag:

    t_adzuna         = PythonOperator(task_id="scrape_adzuna",         python_callable=run_adzuna)
    t_france_travail = PythonOperator(task_id="scrape_france_travail", python_callable=run_france_travail)
    t_arbeitnow      = PythonOperator(task_id="scrape_arbeitnow",      python_callable=run_arbeitnow)
    t_findwork       = PythonOperator(task_id="scrape_findwork",       python_callable=run_findwork)
    t_themuse        = PythonOperator(task_id="scrape_themuse",        python_callable=run_themuse)
    t_linkedin       = PythonOperator(task_id="scrape_linkedin",       python_callable=run_linkedin)
    t_jsearch        = PythonOperator(task_id="scrape_jsearch",        python_callable=run_jsearch)
    t_remotive       = PythonOperator(task_id="scrape_remotive",       python_callable=run_remotive)
    t_jobicy         = PythonOperator(task_id="scrape_jobicy",         python_callable=run_jobicy)

    t_etl = PythonOperator(task_id="etl_postgresql", python_callable=run_etl)

    # Tous les scrapers en parallèle → ETL en dernier
    [
        t_adzuna,
        t_france_travail,
        t_arbeitnow,
        t_findwork,
        t_themuse,
        t_linkedin,
        t_jsearch,
        t_remotive,
        t_jobicy,
    ] >> t_etl