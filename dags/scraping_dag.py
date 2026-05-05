from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os, sys, json
import pandas as pd

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
    return len(offers)

def run_france_travail():
    import importlib.util
    base = "/opt/airflow/france_travail"
    for module_name, filename in [
        ("auth", "auth.py"), ("client", "client.py"), ("normalizer", "normalizer.py")
    ]:
        spec = importlib.util.spec_from_file_location(module_name, os.path.join(base, filename))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod
        spec.loader.exec_module(mod)
    from client import search_offres
    from normalizer import normaliser_liste
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
    scraper = RemotiveScraper(keywords=["data engineer", "data scientist", "data analyst"])
    offers = scraper.scrape()
    save_offers(offers, "remotive")
    print(f"✅ Remotive : {len(offers)} offres")
    return len(offers)

def run_jobicy():
    from scrapers.jobicy_scraper import JobicyScraper
    from storage.raw_storage import save_offers
    scraper = JobicyScraper(keywords=["data engineer", "data scientist", "data analyst"])
    offers = scraper.scrape()
    save_offers(offers, "jobicy")
    print(f"✅ Jobicy : {len(offers)} offres")
    return len(offers)

# ──────────────────────────────────────────────────────────────
# ETL
# ──────────────────────────────────────────────────────────────

def run_etl():
    os.chdir(BASE_PATH)
    from storage.etl import run_etl as etl
    etl()
    print("✅ ETL terminé — données chargées dans PostgreSQL")

# ──────────────────────────────────────────────────────────────
# Azure Bronze Upload
# ──────────────────────────────────────────────────────────────

def make_upload_task(source_name: str, scrape_task_id: str):
    def upload_fn(**context):
        from storage.azure_storage import upload_scraper_output_to_bronze
        ti = context['ti']
        count = ti.xcom_pull(task_ids=scrape_task_id)
        if not count:
            print(f"⚠️ {source_name}: no data to upload (0 offres).")
            return
        exec_date = context['execution_date']
        path = upload_scraper_output_to_bronze(
            data={"count": count, "source": source_name, "timestamp": exec_date.isoformat()},
            source=source_name,
            execution_date=exec_date
        )
        print(f"✅ {source_name} audit uploaded to Azure Bronze: {path}")
    upload_fn.__name__ = f"upload_{source_name}_fn"
    return upload_fn

# ──────────────────────────────────────────────────────────────
# Silver Transform
# ──────────────────────────────────────────────────────────────

def run_silver_transform(**context):
    from utils.silver_transforms import transform_to_silver, load_business_rules
    from pathlib import Path

    exec_date = context["execution_date"]
    rules = load_business_rules()
    raw_dir = Path(BASE_PATH) / "data" / "raw"
    ft_dir  = Path(BASE_PATH) / "france_travail"
    silver_dir = Path(BASE_PATH) / "data" / "silver"
    silver_dir.mkdir(parents=True, exist_ok=True)

    all_dfs = []

    for json_file in raw_dir.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data:
                df = pd.DataFrame(data)
                df['_source_file'] = json_file.name
                all_dfs.append(df)
                print(f"📥 Loaded {len(df)} records from {json_file.name}")
        except Exception as e:
            print(f"⚠️  Error loading {json_file}: {e}")

    for csv_file in ft_dir.glob("offres_*.csv"):
        try:
            df = pd.read_csv(csv_file)
            if not df.empty:
                df['_source_file'] = csv_file.name
                all_dfs.append(df)
                print(f"📥 Loaded {len(df)} records from {csv_file.name}")
        except Exception as e:
            print(f"⚠️  Error loading {csv_file}: {e}")

    if not all_dfs:
        print("⚠️  No raw data found. Skipping Silver transform.")
        return {"count": 0, "status": "no_data"}

    df_combined = pd.concat(all_dfs, ignore_index=True)
    print(f"📊 Total raw records: {len(df_combined)}")

    df_silver = transform_to_silver(df_combined, rules)
    df_silver['_processed_at'] = exec_date.isoformat()

    output_path = silver_dir / "offres_silver.csv"
    df_silver.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"✅ Silver transform complete: {len(df_silver)} records → {output_path}")
    return {"count": len(df_silver), "status": "success"}

# ──────────────────────────────────────────────────────────────
# Gold Aggregations
# ──────────────────────────────────────────────────────────────

def run_gold_aggregations(**context):
    from storage.gold_aggregations import GoldAggregations
    exec_date = context["execution_date"]
    gold = GoldAggregations()
    results = gold.generate_all(exec_date)
    print(f"✅ Gold layer complete. Generated {len(results)} aggregations.")
    return {name: len(df) for name, df in results.items()}

# ──────────────────────────────────────────────────────────────
# Data Warehouse
# ──────────────────────────────────────────────────────────────

def run_dwh():
    os.chdir(BASE_PATH)
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "datawarehouse", f"{BASE_PATH}/storage/datawarehouse.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.run_datawarehouse()
    print("✅ Data Warehouse updated.")

# ──────────────────────────────────────────────────────────────
# DAG Definition
# ──────────────────────────────────────────────────────────────

with DAG(
    dag_id="job_scraping_dag",
    description="Scrape 9 sources → Bronze → ETL → Silver → Gold → DWH",
    default_args=default_args,
    start_date=datetime(2026, 4, 1),
    schedule_interval="0 8 * * *",
    catchup=False,
    tags=["scraping", "etl", "azure", "silver", "gold", "dwh"],
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

    # ── Azure Bronze upload tasks ──
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

    # ── Silver Transform ──
    t_silver = PythonOperator(
        task_id="transform_silver",
        python_callable=run_silver_transform,
        provide_context=True,
        retries=1,
        retry_delay=timedelta(minutes=2)
    )

    # ── Gold Aggregations ──
    t_gold = PythonOperator(
        task_id="generate_gold_layer",
        python_callable=run_gold_aggregations,
        provide_context=True,
        retries=1,
        retry_delay=timedelta(minutes=2)
    )

    # ── Data Warehouse ──
    t_dwh = PythonOperator(
        task_id="update_datawarehouse",
        python_callable=run_dwh,
        retries=1,
        retry_delay=timedelta(minutes=2)
    )

    # ──────────────────────────────────────────────────────────
    # Pipeline dependencies
    #
    # scrape_X → upload_X_bronze ──────────────────────────────┐
    # scrape_X ────────────────────────────────→ etl_postgresql │
    #                                                    ↓       │
    #                                           transform_silver ←┘
    #                                                    ↓
    #                                          generate_gold_layer
    #                                                    ↓
    #                                          update_datawarehouse
    # ──────────────────────────────────────────────────────────

    all_scrapers = [
        t_adzuna, t_france_travail, t_arbeitnow, t_findwork, t_themuse,
        t_linkedin, t_jsearch, t_remotive, t_jobicy
    ]
    all_uploaders = [
        t_upload_adzuna, t_upload_france_travail, t_upload_arbeitnow,
        t_upload_findwork, t_upload_themuse, t_upload_linkedin,
        t_upload_jsearch, t_upload_remotive, t_upload_jobicy
    ]

    # Each scraper → its Bronze upload
    for scraper, uploader in zip(all_scrapers, all_uploaders):
        scraper >> uploader

    # All scrapers → ETL
    all_scrapers >> t_etl

    # ETL + all uploads → Silver
    ([t_etl] + all_uploaders) >> t_silver

    # Silver → Gold → DWH
    t_silver >> t_gold >> t_dwh
