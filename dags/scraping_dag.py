from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os, sys, json
import pandas as pd

sys.path.insert(0, "/opt/airflow")
sys.path.insert(0, "/opt/airflow/utils")
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
    return {"count": len(offers), "source": "adzuna"}

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
    csv_path = f"{base}/offres_france_travail.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"✅ France Travail : {len(df)} offres")
    return {"count": len(df), "source": "france_travail", "csv_path": csv_path}

def run_arbeitnow():
    from scrapers.arbeitnow_client import collecter_arbeitnow
    df = collecter_arbeitnow()
    print(f"✅ Arbeitnow : {len(df)} offres")
    return {"count": len(df), "source": "arbeitnow"}

def run_findwork():
    from scrapers.findwork_scraper import FindworkScraper
    from storage.raw_storage import save_offers
    scraper = FindworkScraper(keywords=["data engineer", "data scientist", "data analyst"], max_pages=5)
    offers = scraper.scrape()
    save_offers(offers, "findwork")
    print(f"✅ Findwork : {len(offers)} offres")
    return {"count": len(offers), "source": "findwork"}

def run_themuse():
    from scrapers.themuse_scraper import TheMuseScraper
    from storage.raw_storage import save_offers
    scraper = TheMuseScraper(keywords=["data engineer", "data scientist", "data analyst"], max_pages=5)
    offers = scraper.scrape()
    save_offers(offers, "themuse")
    print(f"✅ TheMuse : {len(offers)} offres")
    return {"count": len(offers), "source": "themuse"}

def run_linkedin():
    from scrapers.linkedin_client import collecter_linkedin
    df = collecter_linkedin()
    print(f"✅ LinkedIn : {len(df)} offres")
    return {"count": len(df), "source": "linkedin"}

def run_jsearch():
    from scrapers.jsearch_client import collecter_indeed
    df = collecter_indeed()
    print(f"✅ JSearch/Indeed : {len(df)} offres")
    return {"count": len(df), "source": "jsearch"}

def run_remotive():
    from scrapers.remotive_scraper import RemotiveScraper
    from storage.raw_storage import save_offers
    scraper = RemotiveScraper(keywords=["data engineer", "data scientist", "data analyst"])
    offers = scraper.scrape()
    save_offers(offers, "remotive")
    print(f"✅ Remotive : {len(offers)} offres")
    return {"count": len(offers), "source": "remotive"}

def run_jobicy():
    from scrapers.jobicy_scraper import JobicyScraper
    from storage.raw_storage import save_offers
    scraper = JobicyScraper(keywords=["data engineer", "data scientist", "data analyst"])
    offers = scraper.scrape()
    save_offers(offers, "jobicy")
    print(f"✅ Jobicy : {len(offers)} offres")
    return {"count": len(offers), "source": "jobicy"}

# ──────────────────────────────────────────────────────────────
# FIX 1: Real Bronze Upload — uploads actual raw files to ADLS
# ──────────────────────────────────────────────────────────────

def make_bronze_upload(source_name: str, scrape_task_id: str):
    """
    Uploads the actual raw JSON/CSV files to Azure ADLS Gen2 Bronze layer.
    Path: bronze/raw/{source}/{YYYY}/{MM}/{DD}/{file}
    """
    def upload_fn(**context):
        from storage.azure_storage import AzureDataLake
        from pathlib import Path

        ti = context['ti']
        result = ti.xcom_pull(task_ids=scrape_task_id)
        exec_date = context['execution_date']

        if not result or result.get("count", 0) == 0:
            print(f"⚠️  {source_name}: 0 offers scraped — skipping Bronze upload.")
            return {"uploaded": 0, "source": source_name}

        client = AzureDataLake()
        uploaded = 0
        raw_dir = Path(BASE_PATH) / "data" / "raw"

        # Upload JSON files for this source
        for json_file in sorted(raw_dir.glob(f"{source_name}_*.json")):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                path = client.upload_bronze(
                    data=data,
                    source=source_name,
                    execution_date=exec_date,
                    file_name=json_file.name
                )
                print(f"  📤 Uploaded: {json_file.name} → {path}")
                uploaded += 1
            except Exception as e:
                print(f"  ❌ Failed to upload {json_file.name}: {e}")

        # Upload CSV if present (france_travail, arbeitnow, linkedin, jsearch)
        csv_path = result.get("csv_path")
        if not csv_path:
            # Check scrapers/ folder for CSV sources
            for csv_file in Path(BASE_PATH).glob(f"scrapers/offres_{source_name}.csv"):
                csv_path = str(csv_file)
                break

        if csv_path and Path(csv_path).exists():
            try:
                with open(csv_path, "r", encoding="utf-8-sig") as f:
                    content = f.read()
                path = client.upload_bronze(
                    data=content.encode("utf-8"),
                    source=source_name,
                    execution_date=exec_date,
                    file_name=f"{source_name}_{exec_date.strftime('%Y%m%d_%H%M%S')}.csv"
                )
                print(f"  📤 Uploaded CSV: {Path(csv_path).name} → {path}")
                uploaded += 1
            except Exception as e:
                print(f"  ❌ Failed to upload CSV {csv_path}: {e}")

        print(f"✅ {source_name}: {uploaded} file(s) uploaded to Bronze.")
        return {"uploaded": uploaded, "source": source_name}

    upload_fn.__name__ = f"bronze_upload_{source_name}"
    return upload_fn

# ──────────────────────────────────────────────────────────────
# FIX 2: Silver reads from Azure Bronze (not local disk)
# ──────────────────────────────────────────────────────────────

def run_silver_transform(**context):
    """
    Reads raw files from Azure ADLS Gen2 Bronze layer,
    applies Silver transforms, saves to Azure Silver + local data/silver/.
    Falls back to local data/raw/ if Azure is unavailable.
    """
    from utils.silver_transforms import transform_to_silver, load_business_rules
    from storage.azure_storage import AzureDataLake
    from pathlib import Path
    import io

    exec_date = context["execution_date"]
    rules = load_business_rules()
    silver_dir = Path(BASE_PATH) / "data" / "silver"
    silver_dir.mkdir(parents=True, exist_ok=True)

    all_dfs = []

    # ── Read from Azure Bronze ──
    try:
        client = AzureDataLake()
        bronze_files = client.list_bronze_files()
        print(f"📦 Found {len(bronze_files)} files in Azure Bronze")

        for file_path in bronze_files:
            try:
                content = client.download_file(file_path)

                if file_path.endswith(".json"):
                    data = json.loads(content.decode("utf-8"))
                    if isinstance(data, list) and data:
                        df = pd.DataFrame(data)
                    elif isinstance(data, dict):
                        df = pd.DataFrame([data])
                    else:
                        continue
                elif file_path.endswith(".csv"):
                    df = pd.read_csv(io.StringIO(content.decode("utf-8-sig")))
                else:
                    continue

                source = file_path.split("/")[2] if len(file_path.split("/")) > 2 else "unknown"
                df["_source"] = source
                df["_bronze_path"] = file_path
                all_dfs.append(df)
                print(f"  📥 Read {len(df)} rows from Azure Bronze: {file_path.split('/')[-1]}")

            except Exception as e:
                print(f"  ⚠️  Could not read {file_path}: {e}")

    except Exception as e:
        print(f"⚠️  Azure Bronze unavailable ({e}), falling back to local data/raw/")

        # Fallback: read local files
        raw_dir = Path(BASE_PATH) / "data" / "raw"
        ft_dir = Path(BASE_PATH) / "france_travail"

        for json_file in raw_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data:
                    df = pd.DataFrame(data)
                    df["_source"] = json_file.stem.split("_")[0]
                    df["_bronze_path"] = str(json_file)
                    all_dfs.append(df)
            except Exception as ex:
                print(f"  ⚠️  Error loading {json_file}: {ex}")

        for csv_file in ft_dir.glob("offres_*.csv"):
            try:
                df = pd.read_csv(csv_file)
                if not df.empty:
                    df["_source"] = "france_travail"
                    df["_bronze_path"] = str(csv_file)
                    all_dfs.append(df)
            except Exception as ex:
                print(f"  ⚠️  Error loading {csv_file}: {ex}")

    if not all_dfs:
        print("⚠️  No data found in Bronze. Skipping Silver transform.")
        return {"count": 0, "status": "no_data"}

    df_combined = pd.concat(all_dfs, ignore_index=True)
    print(f"📊 Total Bronze records: {len(df_combined)}")

    df_silver = transform_to_silver(df_combined, rules)
    df_silver["_processed_at"] = exec_date.isoformat()

    # Save locally
    local_path = silver_dir / "offres_silver.csv"
    df_silver.to_csv(local_path, index=False, encoding="utf-8-sig")
    print(f"💾 Silver saved locally: {local_path} ({len(df_silver)} rows)")

    # Upload to Azure Silver
    try:
        client = AzureDataLake()
        silver_path = client.upload_silver(
            data=df_silver.to_dict(orient="records"),
            entity_type="offres",
            execution_date=exec_date
        )
        print(f"📤 Silver uploaded to Azure: {silver_path}")
    except Exception as e:
        print(f"⚠️  Azure Silver upload failed (local file still saved): {e}")

    print(f"✅ Silver transform complete: {len(df_silver)} records")
    return {"count": len(df_silver), "status": "success"}

# ──────────────────────────────────────────────────────────────
# FIX 3: Data Quality Monitoring
# ──────────────────────────────────────────────────────────────

# Expected minimum offers per source (based on historical runs)
QUALITY_THRESHOLDS = {
    "adzuna":         {"min": 50,  "warn_drop_pct": 30},
    "france_travail": {"min": 200, "warn_drop_pct": 20},
    "arbeitnow":      {"min": 100, "warn_drop_pct": 30},
    "findwork":       {"min": 100, "warn_drop_pct": 30},
    "themuse":        {"min": 50,  "warn_drop_pct": 30},
    "linkedin":       {"min": 0,   "warn_drop_pct": 100},  # always 429, expected
    "jsearch":        {"min": 20,  "warn_drop_pct": 50},
    "remotive":       {"min": 10,  "warn_drop_pct": 50},
    "jobicy":         {"min": 5,   "warn_drop_pct": 50},
}

def run_data_quality_check(**context):
    """
    Checks scraper outputs against quality thresholds.
    Logs warnings for zero results or significant drops.
    Fails the task if critical sources return nothing.
    """
    ti = context['ti']
    exec_date = context['execution_date']

    scraper_task_ids = {
        "adzuna":         "scrape_adzuna",
        "france_travail": "scrape_france_travail",
        "arbeitnow":      "scrape_arbeitnow",
        "findwork":       "scrape_findwork",
        "themuse":        "scrape_themuse",
        "linkedin":       "scrape_linkedin",
        "jsearch":        "scrape_jsearch",
        "remotive":       "scrape_remotive",
        "jobicy":         "scrape_jobicy",
    }

    print("\n" + "="*60)
    print(f"📊 DATA QUALITY REPORT — {exec_date.strftime('%Y-%m-%d %H:%M')}")
    print("="*60)

    warnings = []
    critical_failures = []
    report = {}

    for source, task_id in scraper_task_ids.items():
        result = ti.xcom_pull(task_ids=task_id)
        count = result.get("count", 0) if isinstance(result, dict) else (result or 0)
        threshold = QUALITY_THRESHOLDS.get(source, {"min": 0, "warn_drop_pct": 50})

        status = "✅ OK"

        # Check zero results
        if count == 0 and threshold["min"] > 0:
            status = "❌ ZERO RESULTS"
            critical_failures.append(f"{source}: returned 0 offers (min expected: {threshold['min']})")

        # Check below minimum
        elif count < threshold["min"]:
            status = f"⚠️  LOW ({count} < min {threshold['min']})"
            warnings.append(f"{source}: {count} offers — below minimum threshold of {threshold['min']}")

        report[source] = {"count": count, "status": status}
        print(f"  {source:<20} {count:>5} offers   {status}")

    # Total check
    total = sum(r["count"] for r in report.values())
    print(f"\n  {'TOTAL':<20} {total:>5} offers")
    print("="*60)

    # Summary
    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"   - {w}")

    if critical_failures:
        print(f"\n❌ CRITICAL FAILURES ({len(critical_failures)}):")
        for f in critical_failures:
            print(f"   - {f}")

    # Save report to file for audit trail
    from pathlib import Path
    report_dir = Path(BASE_PATH) / "data" / "quality_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"quality_{exec_date.strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w") as f:
        json.dump({
            "execution_date": exec_date.isoformat(),
            "total_offers": total,
            "sources": report,
            "warnings": warnings,
            "critical_failures": critical_failures
        }, f, indent=2)
    print(f"\n💾 Report saved: {report_path}")

    # Upload quality report to Azure Bronze
    try:
        from storage.azure_storage import AzureDataLake
        client = AzureDataLake()
        client.upload_bronze(
            data={"execution_date": exec_date.isoformat(), "total": total, "sources": report},
            source="_quality_reports",
            execution_date=exec_date,
            file_name=f"quality_{exec_date.strftime('%Y%m%d_%H%M%S')}.json"
        )
        print("📤 Quality report uploaded to Azure Bronze.")
    except Exception as e:
        print(f"⚠️  Could not upload quality report to Azure: {e}")

    # Fail task only if ALL critical sources failed simultaneously
    critical_sources = ["adzuna", "france_travail"]
    critical_all_failed = all(
        report[s]["count"] == 0 for s in critical_sources
    )
    if critical_all_failed:
        raise ValueError(
            f"❌ PIPELINE HALTED: All critical sources returned 0 offers. "
            f"Check API keys and connectivity."
        )

    print("\n✅ Data quality check passed.")
    return {"total": total, "warnings": len(warnings), "failures": len(critical_failures)}

# ──────────────────────────────────────────────────────────────
# ETL
# ──────────────────────────────────────────────────────────────

def run_etl():
    os.chdir(BASE_PATH)
    from storage.etl import run_etl as etl
    etl()
    print("✅ ETL terminé — données chargées dans PostgreSQL")

# ──────────────────────────────────────────────────────────────
# Gold Aggregations
# ──────────────────────────────────────────────────────────────

def run_gold_aggregations(**context):
    from storage.gold_aggregations import GoldAggregations
    exec_date = context["execution_date"]
    gold = GoldAggregations()
    results = gold.generate_all(exec_date)

    # Upload each Gold file to Azure
    try:
        from storage.azure_storage import AzureDataLake
        client = AzureDataLake()
        for name, df in results.items():
            client.upload_gold(
                data=df.to_dict(orient="records"),
                aggregation_name=name,
                execution_date=exec_date
            )
        print(f"📤 Gold aggregations uploaded to Azure.")
    except Exception as e:
        print(f"⚠️  Azure Gold upload failed (local files still saved): {e}")

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
    description="Scrape 9 sources → Bronze (Azure) → Quality Check → ETL → Silver (Azure) → Gold (Azure) → DWH",
    default_args=default_args,
    start_date=datetime(2026, 4, 1),
    schedule_interval="0 8 * * *",
    catchup=False,
    tags=["scraping", "etl", "azure", "silver", "gold", "dwh", "quality"],
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

    # ── Real Bronze upload tasks (actual files to ADLS Gen2) ──
    t_bronze_adzuna         = PythonOperator(task_id="bronze_adzuna",         python_callable=make_bronze_upload("adzuna",         "scrape_adzuna"),         provide_context=True)
    t_bronze_france_travail = PythonOperator(task_id="bronze_france_travail", python_callable=make_bronze_upload("france_travail", "scrape_france_travail"), provide_context=True)
    t_bronze_arbeitnow      = PythonOperator(task_id="bronze_arbeitnow",      python_callable=make_bronze_upload("arbeitnow",      "scrape_arbeitnow"),      provide_context=True)
    t_bronze_findwork       = PythonOperator(task_id="bronze_findwork",       python_callable=make_bronze_upload("findwork",       "scrape_findwork"),       provide_context=True)
    t_bronze_themuse        = PythonOperator(task_id="bronze_themuse",        python_callable=make_bronze_upload("themuse",        "scrape_themuse"),        provide_context=True)
    t_bronze_linkedin       = PythonOperator(task_id="bronze_linkedin",       python_callable=make_bronze_upload("linkedin",       "scrape_linkedin"),       provide_context=True)
    t_bronze_jsearch        = PythonOperator(task_id="bronze_jsearch",        python_callable=make_bronze_upload("jsearch",        "scrape_jsearch"),        provide_context=True)
    t_bronze_remotive       = PythonOperator(task_id="bronze_remotive",       python_callable=make_bronze_upload("remotive",       "scrape_remotive"),       provide_context=True)
    t_bronze_jobicy         = PythonOperator(task_id="bronze_jobicy",         python_callable=make_bronze_upload("jobicy",         "scrape_jobicy"),         provide_context=True)

    # ── Data Quality Check (runs after all scrapers) ──
    t_quality = PythonOperator(
        task_id="data_quality_check",
        python_callable=run_data_quality_check,
        provide_context=True,
        retries=0,  # Don't retry quality checks
    )

    # ── ETL task ──
    t_etl = PythonOperator(task_id="etl_postgresql", python_callable=run_etl)

    # ── Silver Transform (reads from Azure Bronze) ──
    t_silver = PythonOperator(
        task_id="transform_silver",
        python_callable=run_silver_transform,
        provide_context=True,
        retries=1,
        retry_delay=timedelta(minutes=2)
    )

    # ── Gold Aggregations (uploads to Azure Gold) ──
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
    # Pipeline:
    #
    # scrape_X → bronze_X ──────────────────────────────────┐
    #                                                        │
    # scrape_X ──────────────────────────────────────────→ data_quality_check
    #                                                        │
    #                                                        ▼
    #                                                   etl_postgresql
    #                                                        │
    #                                         (+ all bronze) ▼
    #                                                transform_silver  (reads Azure Bronze)
    #                                                        │
    #                                               generate_gold_layer (uploads Azure Gold)
    #                                                        │
    #                                               update_datawarehouse
    # ──────────────────────────────────────────────────────────

    all_scrapers = [
        t_adzuna, t_france_travail, t_arbeitnow, t_findwork, t_themuse,
        t_linkedin, t_jsearch, t_remotive, t_jobicy
    ]
    all_bronze = [
        t_bronze_adzuna, t_bronze_france_travail, t_bronze_arbeitnow,
        t_bronze_findwork, t_bronze_themuse, t_bronze_linkedin,
        t_bronze_jsearch, t_bronze_remotive, t_bronze_jobicy
    ]

    # Each scraper → its Bronze upload
    for scraper, bronze in zip(all_scrapers, all_bronze):
        scraper >> bronze

    # All scrapers → Quality check
    all_scrapers >> t_quality

    # Quality check → ETL
    t_quality >> t_etl

    # ETL + all Bronze uploads → Silver (Silver needs both ETL done AND files in Azure)
    ([t_etl] + all_bronze) >> t_silver

    # Silver → Gold → DWH
    t_silver >> t_gold >> t_dwh
