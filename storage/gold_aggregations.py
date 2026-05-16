"""
storage/gold_aggregations.py
Gold Layer: Business-ready aggregations from Silver data.
Outputs: CSV files in data/gold/ optimized for Power BI & APIs.
"""
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class GoldAggregations:
    def __init__(self, silver_path: str = "data/silver/offres_silver.csv", gold_dir: str = "data/gold"):
        self.silver_path = Path(silver_path)
        self.gold_dir = Path(gold_dir)
        self.gold_dir.mkdir(parents=True, exist_ok=True)

    def load_silver(self) -> pd.DataFrame:
        if not self.silver_path.exists():
            raise FileNotFoundError(f"⚠️ Silver file not found: {self.silver_path}")
        return pd.read_csv(self.silver_path)

    def _safe_date_col(self, df: pd.DataFrame) -> pd.Series:
        if "_processed_at" in df.columns:
            return pd.to_datetime(df["_processed_at"], errors='coerce').dt.date
        return pd.Series([datetime.now().date()] * len(df))

    def compute_daily_volume(self, df: pd.DataFrame) -> pd.DataFrame:
       dates = self._safe_date_col(df)
       source_col = df["_source"] if "_source" in df.columns else pd.Series(["unknown"] * len(df))
       ct = pd.crosstab(dates, source_col).reset_index()
       # The date column name varies — rename it to 'date'
       date_col = ct.columns[0]
       ct = ct.rename(columns={date_col: "date"})
       return ct.melt(id_vars=["date"], var_name="_source", value_name="job_count")

    def compute_salary_benchmarks(self, df: pd.DataFrame) -> pd.DataFrame:
        valid = df.dropna(subset=["salaire_min"]).copy()
        if valid.empty:
            return pd.DataFrame(columns=["contrat_normalized", "_source", "region", "avg_salary", "offer_count"])
        return valid.groupby(["contrat_normalized", "_source", "region"]).agg(
            avg_salary=("salaire_min", "mean"),
            offer_count=("id", "count")
        ).reset_index()

    def compute_skill_demand(self, df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
        if "skills_detected" not in df.columns:
            return pd.DataFrame(columns=["skill", "count"])
        exploded = df["skills_detected"].explode().dropna()
        counts = exploded.value_counts().head(top_n)
        return pd.DataFrame({"skill": counts.index, "count": counts.values})

    def compute_regional_distribution(self, df: pd.DataFrame) -> pd.DataFrame:
        region_col = df["region"] if "region" in df.columns else pd.Series(["Non spécifié"] * len(df))
        counts = region_col.value_counts()
        return pd.DataFrame({"region": counts.index, "job_count": counts.values})

    def compute_market_health(self, df: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame([{
            "total_offers": len(df),
            "data_completeness": round(df.notna().mean().mean(), 3),
            "avg_desc_length": round(df["description"].str.len().mean(), 1) if "description" in df.columns else 0,
            "sources_active": df["_source"].nunique() if "_source" in df.columns else 0,
            "last_updated": datetime.now().isoformat()
        }])

    def generate_all(self, execution_date: Optional[datetime] = None) -> Dict[str, pd.DataFrame]:
        df = self.load_silver()
        logger.info(f"📊 Generating Gold aggregations from {len(df)} silver records...")

        results = {
            "daily_volume": self.compute_daily_volume(df),
            "salary_benchmarks": self.compute_salary_benchmarks(df),
            "skill_demand": self.compute_skill_demand(df),
            "regional_distribution": self.compute_regional_distribution(df),
            "market_health": self.compute_market_health(df)
        }

        date_str = execution_date.strftime("%Y%m%d") if execution_date else datetime.now().strftime("%Y%m%d")

        for name, agg_df in results.items():
            filepath = self.gold_dir / f"gold_{name}_{date_str}.csv"
            agg_df.to_csv(filepath, index=False, encoding="utf-8-sig")
            logger.info(f"💾 Saved: {filepath.name} ({len(agg_df)} rows)")

        return results
