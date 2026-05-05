"""
storage/azure_to_silver.py
Bridge: Azure Bronze (ADLS Gen2) → Silver Transform → Local/Azure Silver
"""
import logging
import pandas as pd
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from storage.azure_storage import AzureDataLake
from utils.silver_transforms import transform_to_silver, load_business_rules

logger = logging.getLogger(__name__)

def bronze_to_silver(
    sources: Optional[List[str]] = None,
    execution_date: Optional[datetime] = None,
    save_local: bool = True,
    save_azure: bool = False,
    azure_client: Optional[AzureDataLake] = None
) -> pd.DataFrame:
    """
    Main bridge function: Read from Azure Bronze → Apply Silver transforms → Save.
    
    Args:
        sources: List of sources to process (None = all available)
        execution_date: Airflow execution date for path filtering
        save_local: Save result to data/silver/offres_silver.csv
        save_azure: Upload result to Azure Silver layer
        azure_client: Optional pre-initialized AzureDataLake client
    
    Returns:
        Transformed Silver DataFrame
    """
    exec_date = execution_date or datetime.utcnow()
    client = azure_client or AzureDataLake()
    rules = load_business_rules()
    
    all_silver_records = []
    
    # Default sources if not specified
    if not sources:
        sources = [
            "adzuna", "france_travail", "arbeitnow", "findwork", 
            "themuse", "linkedin", "jsearch", "remotive", "jobicy"
        ]
    
    logger.info(f"🔄 Processing {len(sources)} sources for Silver transform...")
    
    for source in sources:
        try:
            # 1. Find latest Bronze file for this source
            bronze_files = client.list_bronze_files(source=source)
            if not bronze_files:
                logger.warning(f"⚠️  No Bronze files found for {source}. Skipping.")
                continue
            
            # Get most recent file
            latest_bronze = sorted(bronze_files)[-1]
            logger.info(f"📥 Reading Bronze: {latest_bronze}")
            
            # 2. Download and parse
            content = client.download_file(latest_bronze)
            if latest_bronze.endswith('.json'):
                import json
                data = json.loads(content.decode('utf-8'))
            else:
                # Fallback for CSV in Bronze
                from io import StringIO
                data = pd.read_csv(StringIO(content.decode('utf-8')))
                if isinstance(data, pd.DataFrame):
                    data = data.to_dict(orient='records')
            
            if not 
                logger.warning(f"⚠️  Empty data for {source}. Skipping.")
                continue
            
            # 3. Convert to DataFrame (handle list of dicts or JobOffer objects)
            if isinstance(data, list) and data and hasattr(data[0], '__dict__'):
                df_raw = pd.DataFrame([o.__dict__ for o in data])
            else:
                df_raw = pd.DataFrame(data)
            
            logger.info(f"📊 Raw records from {source}: {len(df_raw)}")
            
            # 4. Apply Silver transforms
            df_silver = transform_to_silver(df_raw, rules)
            df_silver['_source'] = source
            df_silver['_processed_at'] = exec_date
            
            all_silver_records.append(df_silver)
            logger.info(f"✅ Silver records from {source}: {len(df_silver)}")
            
        except Exception as e:
            logger.error(f"❌ Error processing {source}: {e}")
            continue
    
    if not all_silver_records:
        logger.warning("⚠️  No Silver records generated. Returning empty DataFrame.")
        return pd.DataFrame()
    
    # 5. Combine all sources
    df_combined = pd.concat(all_silver_records, ignore_index=True)
    logger.info(f"🎯 Total Silver records: {len(df_combined)}")
    
    # 6. Save locally (for ETL pipeline)
    if save_local:
        silver_dir = Path("data/silver")
        silver_dir.mkdir(parents=True, exist_ok=True)
        output_path = silver_dir / "offres_silver.csv"
        df_combined.to_csv(output_path, index=False, encoding="utf-8-sig")
        logger.info(f"💾 Saved to: {output_path}")
    
    # 7. Optionally upload to Azure Silver layer
    if save_azure and df_combined is not None and not df_combined.empty:
        try:
            silver_path = client.upload_silver(
                data=df_combined.to_dict(orient='records'),
                entity_type="job_offers",
                execution_date=exec_date
            )
            logger.info(f"☁️  Uploaded to Azure Silver: {silver_path}")
        except Exception as e:
            logger.error(f"❌ Azure Silver upload failed: {e}")
    
    return df_combined


# ──────────────────────────────────────────────────────────────
# Airflow Task Wrapper
# ──────────────────────────────────────────────────────────────
def run_silver_transform_task(**context):
    """Airflow PythonOperator callable for Silver transform."""
    from storage.azure_to_silver import bronze_to_silver
    
    exec_date = context["execution_date"]
    
    df_silver = bronze_to_silver(
        execution_date=exec_date,
        save_local=True,      # Save for ETL
        save_azure=False      # Optional: enable for full cloud pipeline
    )
    
    if df_silver is not None and not df_silver.empty:
        print(f"✅ Silver transform complete: {len(df_silver)} records")
        return {"count": len(df_silver), "status": "success"}
    else:
        print("⚠️  Silver transform produced no records")
        return {"count": 0, "status": "no_data"}
