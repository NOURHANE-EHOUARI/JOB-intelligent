from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from models.job_offer import JobOffer
from scrapers.base_scraper import BaseScraper
import time, random

class IndeedScraper(BaseScraper):
    BASE_URL = "https://fr.indeed.com/jobs"

    def scrape(self) -> list[JobOffer]:
        offers = []
        query = " ".join(self.keywords)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="fr-FR",
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()

            for p_num in range(self.max_pages):
                url = (
                    f"{self.BASE_URL}"
                    f"?q={query.replace(' ', '+')}"
                    f"&l={self.location}"
                    f"&start={p_num * 10}"
                )
                try:
                    page.goto(url, timeout=15000)
                    page.wait_for_selector("div.job_seen_beacon", timeout=8000)
                except Exception as e:
                    self.logger.warning(f"Page {p_num} load failed: {e}")
                    break

                soup = BeautifulSoup(page.content(), "html.parser")
                cards = soup.find_all("div", class_="job_seen_beacon")

                if not cards:
                    self.logger.info(f"No cards on page {p_num}, stopping.")
                    break

                for card in cards:
                    try:
                        raw = self._extract_card(card)
                        offers.append(self.parse_offer(raw))
                    except Exception as e:
                        self.logger.warning(f"Card parse error: {e}")

                self.logger.info(f"Page {p_num + 1}: {len(cards)} offers")
                time.sleep(random.uniform(2.0, 3.5))

            browser.close()

        return offers

    def _extract_card(self, card) -> dict:
        title_el  = card.find("h2", class_="jobTitle")
        company_el = card.find("span", {"data-testid": "company-name"})
        location_el = card.find("div", {"data-testid": "text-location"})
        salary_el  = card.find("div", class_="salary-snippet-container")
        link_el   = card.find("a", class_="jcs-JobTitle")

        return {
            "title":    title_el.get_text(strip=True)   if title_el   else "N/A",
            "company":  company_el.get_text(strip=True)  if company_el  else "N/A",
            "location": location_el.get_text(strip=True) if location_el else "N/A",
            "salary":   salary_el.get_text(strip=True)   if salary_el   else None,
            "url": "https://fr.indeed.com" + link_el["href"] if link_el else "N/A",
            "description": "",
        }

    def parse_offer(self, raw: dict) -> JobOffer:
        return JobOffer(
            title=raw["title"],
            company=raw["company"],
            location=raw["location"],
            source="indeed",
            url=raw["url"],
            description=raw.get("description", ""),
            salary=raw.get("salary"),
        )
        