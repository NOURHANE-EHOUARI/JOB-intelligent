import json
from pathlib import Path
from models.job_offer import JobOffer
from datetime import datetime

RAW_DIR = Path("data/raw")

def save_offers(offers: list[JobOffer], source: str) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filepath = RAW_DIR / f"{source}_{timestamp}.json"

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump([o.to_dict() for o in offers], f, ensure_ascii=False, indent=2)

    print(f"Saved {len(offers)} offers → {filepath}")
    return filepath