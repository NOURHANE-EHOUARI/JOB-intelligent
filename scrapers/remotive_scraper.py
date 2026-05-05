# ── FIX: Ensure project root is in Python path ──
import sys, os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# ───────────────────────────────────────────────

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from models.job_offer import JobOffer
from scrapers.base_scraper import BaseScraper

# ──────────────────────────────────────────────────────────────
# AJOUT TÂCHE 4 : Import config NLP pour le filtre qualité
# ──────────────────────────────────────────────────────────────
from utils.nlp_config import load_nlp_config

class RemotiveScraper(BaseScraper):
    BASE_URL = "https://remotive.com/api/remote-jobs"

    def __init__(self, keywords: list[str], max_pages: int = 1):
        super().__init__(keywords, location="Remote", max_pages=max_pages)

    def scrape(self) -> list[JobOffer]:
        offers = []
        for keyword in self.keywords:
            try:
                response = requests.get(
                    self.BASE_URL,
                    params={"search": keyword, "limit": 100},
                    timeout=10
                )
                response.raise_for_status()
                jobs = response.json().get("jobs", [])
                for job in jobs:
                    # ✅ AJOUT TÂCHE 4 : Ne garder que les offres validées
                    offer = self.parse_offer(job)
                    if offer:  # skip if parse_offer returned None (failed validation)
                        offers.append(offer)
                self.logger.info(f"Remotive '{keyword}': {len(jobs)} offres")
            except requests.RequestException as e:
                self.logger.error(f"Remotive error: {e}")
        return offers

    def parse_offer(self, raw: dict) -> JobOffer:
        # ✅ AJOUT TÂCHE 4 : Validation qualité pré-création du JobOffer
        title = raw.get("title", "N/A")
        description = raw.get("description", "")
        
        if not self.validate_offer_quality(title, description):
            return None  # Rejeter l'offre si elle ne passe pas les filtres
        
        return JobOffer(
            titre=title,
            entreprise=raw.get("company_name", "N/A"),
            ville=raw.get("candidate_required_location", "Remote"),
            source="remotive",
            url=raw.get("url", ""),
            description=description[:500],
            contrat=raw.get("job_type", "N/A"),
            salaire=raw.get("salary", "Non précisé") or "Non précisé",
            date_publication=raw.get("publication_date", "")[:10],
            competences=", ".join(raw.get("tags", [])),
        )