import json
from pathlib import Path
from sqlalchemy.dialects.postgresql import insert
from storage.database import SessionLocal, engine
from storage.models_db import OffreEmploi, Base
import pandas as pd

def init_db():
    Base.metadata.create_all(engine)
    print("Tables créées.")

def load_adzuna_json(filepath: str) -> list[dict]:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def load_france_travail_csv(filepath: str) -> list[dict]:
    df = pd.read_csv(filepath)
    df = df.fillna("Non précisé")
    return df.to_dict(orient="records")

def upsert_offers(offers: list[dict]):
    session = SessionLocal()
    inserted = 0
    skipped = 0
    errors = 0
    try:
        for offer in offers:
            try:
                # Skip offers with no title
                titre = offer.get("titre") or offer.get("title")
                if not titre:
                    errors += 1
                    continue

                stmt = insert(OffreEmploi).values(
                    id=offer.get("id"),
                    titre=titre,
                    entreprise=offer.get("entreprise", offer.get("company", "Non précisé")),
                    ville=offer.get("ville", offer.get("location", "Non précisé")),
                    code_postal=offer.get("code_postal"),
                    contrat=offer.get("contrat", offer.get("contract_type")),
                    salaire=offer.get("salaire", offer.get("salary")),
                    experience=offer.get("experience"),
                    competences=offer.get("competences", ""),
                    description=offer.get("description", ""),
                    date_publication=offer.get("date_publication"),
                    url=offer.get("url", ""),
                    source=offer.get("source", "unknown"),
                    scraped_at=offer.get("scraped_at", ""),
                ).on_conflict_do_nothing(index_elements=["id"])
                result = session.execute(stmt)
                session.commit()
                if result.rowcount > 0:
                    inserted += 1
                else:
                    skipped += 1
            except Exception as e:
                session.rollback()
                errors += 1
        print(f"Inserted: {inserted} | Skipped (duplicates): {skipped} | Errors: {errors}")
    finally:
        session.close()

def run_etl():
    init_db()
    raw_dir = Path("data/raw")

    # Load all JSON files (Adzuna, Remotive, TheMuse, Jobicy)
    
    for f in sorted(raw_dir.glob("*.json")):
      print(f"Loading {f.name}...")
      try:
        offers = load_adzuna_json(str(f))
        upsert_offers(offers)
      except Exception as e:
        print(f"⚠  Skipping {f.name}: {e}")
        continue
    # Load France Travail CSV
    ft_csv = Path("france_travail/offres_france_travail.csv")
    if ft_csv.exists():
        print(f"Loading France Travail CSV...")
        offers = load_france_travail_csv(str(ft_csv))
        upsert_offers(offers)
   
    # Load other CSV files
    data_csvs = [
      "scrapers/offres_arbeitnow.csv",
      "scrapers/offres_indeed.csv",
      "scrapers/offres_linkedin.csv",
      "offres_reed.csv",
    ]
    for csv_path in data_csvs:
       
      p = Path(csv_path)
      if p.exists() and p.stat().st_size > 100:  # skip empty files
        print(f"Loading {p.name}...")
        offers = load_france_travail_csv(str(p))
        upsert_offers(offers)
      elif p.exists():
        print(f"Skipping {p.name} (empty)")
    print("ETL terminé.")
if __name__ == "__main__":
    run_etl()
