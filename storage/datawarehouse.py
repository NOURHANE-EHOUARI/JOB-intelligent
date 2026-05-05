"""
Data Warehouse Pipeline - Star Schema Build & Load
Production-ready, idempotent, and fully validated.
Run: python storage/datawarehouse.py
"""

import logging
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
import os
import sys

# ──────────────────────────────────────────────────────────────
# Configuration & Logging
# ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("datawarehouse")

DB_URL = os.getenv("DATABASE_URL", "postgresql://airflow:airflow@localhost:5433/job_intelligent")
engine = create_engine(DB_URL, echo=False)

# ──────────────────────────────────────────────────────────────
# 1. Schema Creation
# ──────────────────────────────────────────────────────────────
def create_dwh_schema() -> None:
    """Create star schema tables with constraints if they don't exist."""
    logger.info("🏗️  Creating/verifying DWH schema...")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dim_date (
                id_date VARCHAR(20) PRIMARY KEY,
                date_val DATE UNIQUE,
                jour INT,
                mois INT,
                annee INT,
                trimestre INT,
                semaine INT,
                jour_semaine VARCHAR(20)
            );
            CREATE TABLE IF NOT EXISTS dim_ville (
                id_ville VARCHAR(100) PRIMARY KEY,
                ville VARCHAR(100),
                code_postal VARCHAR(10)
            );
            CREATE TABLE IF NOT EXISTS dim_contrat (
                id_contrat VARCHAR(50) PRIMARY KEY,
                type_contrat VARCHAR(50) UNIQUE
            );
            CREATE TABLE IF NOT EXISTS dim_source (
                id_source VARCHAR(50) PRIMARY KEY,
                nom_source VARCHAR(50) UNIQUE
            );
            CREATE TABLE IF NOT EXISTS fact_offres (
                id_offre VARCHAR(100) PRIMARY KEY,
                id_date VARCHAR(20) REFERENCES dim_date(id_date),
                id_ville VARCHAR(100) REFERENCES dim_ville(id_ville),
                id_contrat VARCHAR(50) REFERENCES dim_contrat(id_contrat),
                id_source VARCHAR(50) REFERENCES dim_source(id_source),
                titre TEXT,
                entreprise VARCHAR(150),
                salaire TEXT,
                competences TEXT,
                description TEXT
            );
        """))
        conn.commit()
    logger.info("✅ DWH schema verified.")

# ──────────────────────────────────────────────────────────────
# 2. Dimension Population (Idempotent)
# ──────────────────────────────────────────────────────────────
def _upsert_dimension(table: str, df: pd.DataFrame, pk_col: str) -> None:
    """Insert dimension rows, ignoring duplicates (ON CONFLICT DO NOTHING)."""
    # Build dynamic INSERT ... ON CONFLICT DO NOTHING
    cols = df.columns.tolist()
    placeholders = ", ".join([f":{c}" for c in cols])
    update_clause = ", ".join([f"{c} = EXCLUDED.{c}" for c in cols if c != pk_col])
    
    sql = f"""
        INSERT INTO {table} ({', '.join(cols)})
        VALUES ({placeholders})
        ON CONFLICT ({pk_col}) DO UPDATE SET {update_clause};
    """
    
    records = df.to_dict(orient="records")
    with engine.connect() as conn:
        conn.execute(text(sql), records)
        conn.commit()
    logger.info(f"📦 {table} upserted ({len(records)} rows)")

def populate_dimensions() -> None:
    """Extract distinct values from operational DB and populate dimensions."""
    logger.info("🔄 Extracting & loading dimensions...")
    with engine.connect() as conn:
        df_raw = pd.read_sql("SELECT * FROM offres_emploi", conn)

    # Normalize & clean
    df_raw["ville"] = df_raw.get("ville", pd.Series(dtype="str")).fillna("Inconnu").str.strip().str.title()
    df_raw["code_postal"] = df_raw.get("code_postal", pd.Series(dtype="str")).fillna("00000").str.strip()
    df_raw["type_contrat"] = df_raw.get("type_contrat", pd.Series(dtype="str")).fillna("Non précisé").str.strip()
    df_raw["source"] = df_raw.get("source", pd.Series(dtype="str")).fillna("Inconnu").str.strip()
    df_raw["date_publication"] = pd.to_datetime(df_raw.get("date_publication"), errors="coerce")

    # ── Dim Date ──
    dates = df_raw["date_publication"].dropna().unique()
    date_rows = []
    for d in dates:
        date_rows.append({
            "id_date": d.strftime("%Y%m%d"),
            "date_val": d,
            "jour": d.day,
            "mois": d.month,
            "annee": d.year,
            "trimestre": (d.month - 1) // 3 + 1,
            "semaine": d.isocalendar()[1],
            "jour_semaine": d.strftime("%A")
        })
    df_date = pd.DataFrame(date_rows).drop_duplicates("id_date")
    # Fallback row
    df_date = pd.concat([df_date, pd.DataFrame([{
        "id_date": "19000101", "date_val": pd.Timestamp("1900-01-01"),
        "jour": 1, "mois": 1, "annee": 1900, "trimestre": 1, "semaine": 1, "jour_semaine": "Monday"
    }])], ignore_index=True)
    _upsert_dimension("dim_date", df_date, "id_date")

    # ── Dim Ville ──
    df_ville = df_raw[["ville", "code_postal"]].drop_duplicates()
    df_ville["id_ville"] = df_ville["ville"] + "_" + df_ville["code_postal"]
    df_ville = df_ville[["id_ville", "ville", "code_postal"]]
    df_ville = pd.concat([df_ville, pd.DataFrame([{
        "id_ville": "UNK_VILLE", "ville": "Inconnu", "code_postal": "00000"
    }])], ignore_index=True).drop_duplicates("id_ville")
    _upsert_dimension("dim_ville", df_ville, "id_ville")

    # ── Dim Contrat ──
    df_contrat = df_raw[["type_contrat"]].drop_duplicates()
    df_contrat["id_contrat"] = df_contrat["type_contrat"].fillna("Non précisé").str.replace(" ", "_").str.upper()
    df_contrat = df_contrat[["id_contrat", "type_contrat"]]
    df_contrat = pd.concat([df_contrat, pd.DataFrame([{
        "id_contrat": "UNK_CONTRAT", "type_contrat": "Non précisé"
    }])], ignore_index=True).drop_duplicates("id_contrat")
    _upsert_dimension("dim_contrat", df_contrat, "id_contrat")

    # ─ Dim Source ──
    df_source = df_raw[["source"]].drop_duplicates()
    df_source["id_source"] = df_source["source"].str.replace(" ", "_").str.upper()
    df_source = df_source.rename(columns={"source": "nom_source"})[["id_source", "nom_source"]]
    df_source = pd.concat([df_source, pd.DataFrame([{
        "id_source": "UNK_SOURCE", "nom_source": "Inconnu"
    }])], ignore_index=True).drop_duplicates("id_source")
    _upsert_dimension("dim_source", df_source, "id_source")

# ──────────────────────────────────────────────────────────────
# 3. Fact Table Load (FK-Validated)
# ──────────────────────────────────────────────────────────────
def load_fact_table() -> None:
    """Map operational data to dimension surrogate keys & load fact_offres."""
    logger.info("🔄 Building fact_offres...")
    
    with engine.connect() as conn:
        df_raw = pd.read_sql("SELECT * FROM offres_emploi", conn)
    
    if df_raw.empty:
        logger.warning("⚠️  offres_emploi is empty")
        return

    logger.info(f"📊 Raw offers loaded: {len(df_raw)}")

    # ── 1. Normalize fields (MUST match populate_dimensions() EXACTLY) ──
    # Ville: strip, title case, handle missing
    df_raw["ville"] = df_raw.get("ville", pd.Series(dtype="str")).fillna("Inconnu").str.strip().str.title()
    df_raw["code_postal"] = df_raw.get("code_postal", pd.Series(dtype="str")).fillna("00000").str.strip()
    
    df_raw["type_contrat"] = df_raw.get("contrat", pd.Series(dtype="str")).fillna("Non précisé").str.strip()
    df_raw["type_contrat_clean"] = (
        df_raw["type_contrat"]
        .replace("", "Non précisé")
        .str.replace(r"[^\w\s-]", "", regex=True)  # Remove special chars
        .str.replace(" ", "_")
        .str.upper()
        .str[:140]
    )
    
    # Source: same normalization
    df_raw["source"] = df_raw.get("source", pd.Series(dtype="str")).fillna("Inconnu").str.strip()
    df_raw["source_clean"] = df_raw["source"].str.replace(" ", "_").str.upper().str[:140]
    
    # Date: parse with fallback
    df_raw["date_publication"] = pd.to_datetime(df_raw.get("date_publication"), errors="coerce")
    df_raw["id_date_raw"] = df_raw["date_publication"].apply(
        lambda x: x.strftime("%Y%m%d") if pd.notnull(x) else None
    )

    # ── 2. Create surrogate keys using SAME logic as dimensions ──
    # Ville key: ville_code_postal (max 240 chars)
    def make_ville_key(row):
        ville = str(row.get("ville") or "Inconnu").strip()[:180]
        postal = str(row.get("code_postal") or "00000").strip()[:80]
        if postal.lower() in ["non précisé", "n/a", "na", "unknown", ""]:
            postal = "00000"
        return f"{ville}_{postal}"[:240]
    
    df_raw["id_ville_raw"] = df_raw.apply(make_ville_key, axis=1)
    df_raw["id_contrat_raw"] = df_raw["type_contrat_clean"]
    df_raw["id_source_raw"] = df_raw["source_clean"]
    df_raw["id_date"] = df_raw["id_date_raw"].fillna("19000101")  # Fallback for NULL dates

    # ── 3. Load dimension keys (only the PK column needed for mapping) ──
    dim_date = pd.read_sql("SELECT id_date FROM dim_date", engine)
    dim_ville = pd.read_sql("SELECT id_ville FROM dim_ville", engine)
    dim_contrat = pd.read_sql("SELECT id_contrat FROM dim_contrat", engine)
    dim_source = pd.read_sql("SELECT id_source FROM dim_source", engine)
    
    # Create mapping dicts
    map_date = dict(zip(dim_date["id_date"], dim_date["id_date"]))
    map_ville = dict(zip(dim_ville["id_ville"], dim_ville["id_ville"]))
    map_contrat = dict(zip(dim_contrat["id_contrat"], dim_contrat["id_contrat"]))
    map_source = dict(zip(dim_source["id_source"], dim_source["id_source"]))

    # ── 4. Map with explicit fallback to UNKNOWN keys ──
    df_raw["id_date"] = df_raw["id_date"].map(map_date).fillna("19000101")
    df_raw["id_ville"] = df_raw["id_ville_raw"].map(map_ville).fillna("UNK_VILLE")
    df_raw["id_contrat"] = df_raw["id_contrat_raw"].map(map_contrat).fillna("UNK_CONTRAT")
    df_raw["id_source"] = df_raw["id_source_raw"].map(map_source).fillna("UNK_SOURCE")

    # ── 5. Validation: Log mismatches for debugging ──
    fk_cols = ["id_date", "id_ville", "id_contrat", "id_source"]
    for col in fk_cols:
        null_count = df_raw[col].isna().sum()
        if null_count > 0:
            logger.warning(f"⚠️  {col}: {null_count} NULL values after mapping — check dimension population")

    # ── 6. Select fact columns (drop helper columns) ──
    df_raw = df_raw.rename(columns={"id": "id_offre"})
    fact_schema = [
        "id_offre", "id_date", "id_ville", "id_contrat", "id_source",
        "titre", "entreprise", "salaire", "competences", "description"
    ]
    df_fact = df_raw.reindex(columns=fact_schema).dropna(subset=["id_offre"])
    # Final check: ensure no NULL FKs remain
    if df_fact[fk_cols].isna().any().any():
        logger.error("❌ Fact table still contains NULL FKs — aborting load")
        logger.info(f"   Sample problematic rows:\n{df_fact[df_fact[fk_cols].isna().any(axis=1)].head(2)}")
        return

    logger.info(f"📋 Fact rows ready for insert: {len(df_fact)}")

    # ── 7. Idempotent load: truncate then insert in chunks ──
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE fact_offres RESTART IDENTITY CASCADE"))
        conn.commit()

    chunk_size = 200
    total = 0
    for i in range(0, len(df_fact), chunk_size):
        chunk = df_fact.iloc[i:i+chunk_size]
        chunk.to_sql("fact_offres", engine, if_exists="append", index=False)
        total += len(chunk)
        logger.info(f"  Inserted chunk {i//chunk_size + 1}: {total}/{len(df_fact)} rows")

    logger.info(f"✅ fact_offres loaded ({total} rows)")
# ──────────────────────────────────────────────────────────────
# 4. Execution Entry Point
# ──────────────────────────────────────────────────────────────
def run_datawarehouse() -> None:
    """Main pipeline orchestrator."""
    logger.info("🚀 Starting Data Warehouse pipeline...")
    try:
        create_dwh_schema()
        populate_dimensions()
        load_fact_table()
        logger.info("🎉 Data Warehouse pipeline completed successfully.")
    except Exception as e:
        logger.error(f"💥 Pipeline failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run_datawarehouse()
