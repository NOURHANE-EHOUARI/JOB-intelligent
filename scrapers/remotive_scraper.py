import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from models.job_offer import JobOffer
from scrapers.base_scraper import BaseScraper

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
                    offers.append(self.parse_offer(job))
                self.logger.info(f"Remotive '{keyword}': {len(jobs)} offres")
            except requests.RequestException as e:
                self.logger.error(f"Remotive error: {e}")
        return offers

    def parse_offer(self, raw: dict) -> JobOffer:
        return JobOffer(
            titre=raw.get("title", "N/A"),
            entreprise=raw.get("company_name", "N/A"),
            ville=raw.get("candidate_required_location", "Remote"),
            source="remotive",
            url=raw.get("url", ""),
            description=raw.get("description", "")[:500],
            contrat=raw.get("job_type", "N/A"),
            salaire=raw.get("salary", "Non précisé"),
            date_publication=raw.get("publication_date", "")[:10],
            competences=", ".join(raw.get("tags", [])),
        )

    def parse_offer(self, raw: dict) -> JobOffer:
        return JobOffer(
            titre=raw.get("title", "N/A"),
            entreprise=raw.get("company_name", "N/A"),
            ville=raw.get("candidate_required_location", "Remote"),
            source="remotive",
            url=raw.get("url", ""),
            description=raw.get("description", "")[:500],
            contrat=raw.get("job_type", "N/A"),
            salaire=raw.get("salary", "Non précisé") or "Non précisé",
            date_publication=raw.get("publication_date", "")[:10],
            competences=", ".join(raw.get("tags", [])),
        )
