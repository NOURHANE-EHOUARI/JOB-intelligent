import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import time
from models.job_offer import JobOffer
from scrapers.base_scraper import BaseScraper

# ──────────────────────────────────────────────────────────────
# AJOUT TÂCHE 4 : Import config NLP pour le filtre qualité
# ──────────────────────────────────────────────────────────────
from utils.nlp_config import load_nlp_config

FINDWORK_API_KEY = "b6f5ea050bcd7c670adf34e5a59d4c942457ea3a"

class FindworkScraper(BaseScraper):
    BASE_URL = "https://findwork.dev/api/jobs/"

    def __init__(self, keywords: list[str], max_pages: int = 5):
        super().__init__(keywords, location="", max_pages=max_pages)
        self.headers = {"Authorization": f"Token {FINDWORK_API_KEY}"}

    def scrape(self) -> list[JobOffer]:
        offers = []
        seen_ids = set()

        for keyword in self.keywords:
            url = self.BASE_URL
            page = 1
            while url and page <= self.max_pages:
                try:
                    response = requests.get(
                        url,
                        headers=self.headers,
                        params={"search": keyword} if page == 1 else {},
                        timeout=10
                    )
                    response.raise_for_status()
                    data = response.json()
                    results = data.get("results", [])

                    if not results:
                        break

                    for job in results:
                        job_id = job.get("id", "")
                        if job_id in seen_ids:
                            continue
                        seen_ids.add(job_id)
                        # ✅ AJOUT TÂCHE 4 : Ne garder que les offres validées
                        offer = self.parse_offer(job)
                        if offer:  # skip if parse_offer returned None (failed validation)
                            offers.append(offer)

                    self.logger.info(f"Findwork '{keyword}' page {page}: {len(results)} offres")
                    url = data.get("next")
                    page += 1
                    time.sleep(0.5)

                except requests.RequestException as e:
                    self.logger.error(f"Findwork error: {e}")
                    break

        return offers

    def parse_offer(self, raw: dict) -> JobOffer:
        # ✅ AJOUT TÂCHE 4 : Validation qualité pré-création du JobOffer
        title = raw.get("role") or raw.get("title") or "Non précisé"
        description = raw.get("text", "")
        
        if not self.validate_offer_quality(title, description):
            return None  # Rejeter l'offre si elle ne passe pas les filtres
        
        keywords = raw.get("keywords", []) or []
        if not keywords:
            competences = ""
        elif isinstance(keywords[0], dict):
            competences = ", ".join([k.get("name", "") for k in keywords])
        else:
           competences = ", ".join(keywords)
        return JobOffer(
            id=str(raw.get("id", "")),
            titre = title,
            entreprise=raw.get("company_name", "Non précisé"),
            ville=raw.get("location", "Remote") or "Remote",
            source="findwork",
            url=raw.get("url", ""),
            description=description[:500],
            contrat="Remote" if raw.get("remote") else "N/A",
            salaire="Non précisé",
            date_publication=raw.get("date_posted", "")[:10],
            competences=competences,
        )