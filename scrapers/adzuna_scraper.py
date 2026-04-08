import requests
from models.job_offer import JobOffer
from scrapers.base_scraper import BaseScraper

class AdzunaScraper(BaseScraper):
    BASE_URL = "https://api.adzuna.com/v1/api/jobs/fr/search"

    def __init__(self, keywords: list[str], location: str,
                 app_id: str, app_key: str, max_pages: int = 5):
        super().__init__(keywords, location, max_pages)
        self.app_id = app_id
        self.app_key = app_key

    def scrape(self) -> list[JobOffer]:
        offers = []
        query = " ".join(self.keywords)

        for page in range(1, self.max_pages + 1):
            params = {
                "app_id": self.app_id,
                "app_key": self.app_key,
                "results_per_page": 20,
                "what": query,
                "where": self.location,
                "content-type": "application/json",
            }
            try:
                response = requests.get(
                    f"{self.BASE_URL}/{page}",
                    params=params, timeout=10
                )
                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])

                if not results:
                    self.logger.info(f"No results on page {page}, stopping.")
                    break

                for item in results:
                    offers.append(self.parse_offer(item))

                self.logger.info(f"Page {page}: {len(results)} offers fetched")

            except requests.RequestException as e:
                self.logger.error(f"Adzuna request failed: {e}")
                break

        return offers

    def parse_offer(self, raw: dict) -> JobOffer:
        return JobOffer(
            title=raw.get("title", "N/A"),
            company=raw.get("company", {}).get("display_name", "N/A"),
            location=raw.get("location", {}).get("display_name", "N/A"),
            source="adzuna",
            url=raw.get("redirect_url", "N/A"),
            description=raw.get("description", ""),
            salary=(
                f"{raw['salary_min']:.0f}–{raw['salary_max']:.0f}€"
                if raw.get("salary_min") else None
            ),
            contract_type=raw.get("contract_type", None),
            posted_at=raw.get("created", None),
        )