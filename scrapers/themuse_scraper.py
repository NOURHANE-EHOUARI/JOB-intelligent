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

class TheMuseScraper(BaseScraper):
    BASE_URL = "https://www.themuse.com/api/public/jobs"

    def __init__(self, keywords: list[str], max_pages: int = 5):
        super().__init__(keywords, location="", max_pages=max_pages)

    def scrape(self) -> list[JobOffer]:
        offers = []
        for page in range(self.max_pages):
            try:
                response = requests.get(
                    self.BASE_URL,
                    params={
                        "category": "Data and Analytics",
                        "page": page,
                        "descended": "true"
                    },
                    timeout=10
                )
                response.raise_for_status()
                results = response.json().get("results", [])
                if not results:
                    break
                for job in results:
                    # ✅ AJOUT TÂCHE 4 : Ne garder que les offres validées
                    offer = self.parse_offer(job)
                    if offer:  # skip if parse_offer returned None (failed validation)
                        offers.append(offer)
                self.logger.info(f"TheMuse page {page+1}: {len(results)} offres")
            except requests.RequestException as e:
                self.logger.error(f"TheMuse error: {e}")
                break
        return offers

    def parse_offer(self, raw: dict) -> JobOffer:
        # ✅ AJOUT TÂCHE 4 : Validation qualité pré-création du JobOffer
        title = raw.get("name", "N/A")
        description = raw.get("contents", "")
        
        if not self.validate_offer_quality(title, description):
            return None  # Rejeter l'offre si elle ne passe pas les filtres
        
        locations = raw.get("locations", [])
        ville = locations[0].get("name", "Remote") if locations else "Remote"
        levels = raw.get("levels", [])
        experience = levels[0].get("name", "") if levels else ""
        company = raw.get("company", {}).get("name", "N/A")

        return JobOffer(
            titre=title,
            entreprise=company,
            ville=ville,
            source="themuse",
            url=raw.get("refs", {}).get("landing_page", ""),
            description=description[:500],
            contrat="N/A",
            salaire="Non précisé",
            experience=experience,
            date_publication=raw.get("publication_date", "")[:10],
            competences="",
        )