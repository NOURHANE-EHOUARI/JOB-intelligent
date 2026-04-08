from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os, sys

sys.path.insert(0, "/opt/airflow")

from dotenv import load_dotenv
load_dotenv()

from scrapers.adzuna_scraper import AdzunaScraper
from storage.raw_storage import save_offers

default_args = {
    "owner": "hiba",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

def run_adzuna_scraper():
    scraper = AdzunaScraper(
        keywords=["data engineer", "data scientist", "data analyst"],
        location="Paris",
        app_id=os.getenv("ADZUNA_APP_ID"),
        app_key=os.getenv("ADZUNA_APP_KEY"),
        max_pages=5
    )
    offers = scraper.scrape()
    save_offers(offers, "adzuna")
    print(f"Done: {len(offers)} offers saved.")

with DAG(
    dag_id="job_scraping_dag",
    description="Daily scrape of job offers from Adzuna",
    default_args=default_args,
    start_date=datetime(2026, 4, 1),
    schedule_interval="0 8 * * *",   # every day at 8am
    catchup=False,
    tags=["scraping", "phase1"],
) as dag:

    scrape_adzuna = PythonOperator(
        task_id="scrape_adzuna",
        python_callable=run_adzuna_scraper,
    )

    scrape_adzuna   # easy to chain more tasks later: scrape_adzuna >> scrape_france_travail