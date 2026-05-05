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

class JobicyScraper(BaseScraper):
    BASE_URL = "https://jobicy.com/api/v2/remote-jobs"

    def __init__(self, keywords: list[str], max_pages: int = 1):
        super().__init__(keywords, location="Remote", max_pages=max_pages)

    def scrape(self) -> list[JobOffer]:
      offers = []
      try:
        response = requests.get(
            self.BASE_URL,
            params={"count": 50},
            timeout=10
        )
        response.raise_for_status()
        jobs = response.json().get("jobs", [])
        # filter data-related jobs
        keywords = ["data", "analyst", "scientist", "engineer", "ml", "ai", "machine learning"]
        filtered = [
            j for j in jobs
            if any(k in j.get("jobTitle", "").lower() for k in keywords)
        ]
        for job in filtered:
            # ✅ AJOUT TÂCHE 4 : Ne garder que les offres validées
            offer = self.parse_offer(job)
            if offer:  # skip if parse_offer returned None (failed validation)
                offers.append(offer)
        self.logger.info(f"Jobicy: {len(filtered)} offres data (sur {len(jobs)} total)")
      except requests.RequestException as e:
        self.logger.error(f"Jobicy error: {e}")
      return offers

    def parse_offer(self, raw: dict) -> JobOffer:
        # ✅ AJOUT TÂCHE 4 : Validation qualité pré-création du JobOffer
        title = raw.get("jobTitle", "N/A")
        description = raw.get("jobExcerpt", "")
        
        if not self.validate_offer_quality(title, description):
            return None  # Rejeter l'offre si elle ne passe pas les filtres
        
        salary_min = raw.get("salaryMin")
        salary_max = raw.get("salaryMax")
        currency = raw.get("salaryCurrency", "")
        salaire = f"{salary_min}–{salary_max} {currency}" if salary_min else "Non précisé"

        return JobOffer(
            titre=title,
            entreprise=raw.get("companyName", "N/A"),
            ville=raw.get("jobGeo", "Remote"),
            source="jobicy",
            url=raw.get("url", ""),
            description=description[:500],
            contrat=", ".join(raw.get("jobType", [])),
            salaire=salaire,
            date_publication=raw.get("pubDate", "")[:10],
            competences=", ".join(raw.get("jobIndustry", [])),
        )