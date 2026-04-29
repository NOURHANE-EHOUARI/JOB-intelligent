import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from models.job_offer import JobOffer
from scrapers.base_scraper import BaseScraper

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
            offers.append(self.parse_offer(job))
        self.logger.info(f"Jobicy: {len(filtered)} offres data (sur {len(jobs)} total)")
      except requests.RequestException as e:
        self.logger.error(f"Jobicy error: {e}")
      return offers

    def parse_offer(self, raw: dict) -> JobOffer:
      salary_min = raw.get("salaryMin")
      salary_max = raw.get("salaryMax")
      currency = raw.get("salaryCurrency", "")
      salaire = f"{salary_min}–{salary_max} {currency}" if salary_min else "Non précisé"

      return JobOffer(
        titre=raw.get("jobTitle", "N/A"),
        entreprise=raw.get("companyName", "N/A"),
        ville=raw.get("jobGeo", "Remote"),
        source="jobicy",
        url=raw.get("url", ""),
        description=raw.get("jobExcerpt", "")[:500],
        contrat=", ".join(raw.get("jobType", [])),
        salaire=salaire,
        date_publication=raw.get("pubDate", "")[:10],
        competences=", ".join(raw.get("jobIndustry", [])),
       )
