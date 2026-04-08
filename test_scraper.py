import os
from dotenv import load_dotenv
from scrapers.adzuna_scraper import AdzunaScraper
from storage.raw_storage import save_offers

load_dotenv()

scraper = AdzunaScraper(
    keywords=["data engineer", "data scientist"],
    location="Paris",
    app_id=os.getenv("ADZUNA_APP_ID"),
    app_key=os.getenv("ADZUNA_APP_KEY"),
    max_pages=3
)

offers = scraper.scrape()
save_offers(offers, "adzuna")

for o in offers[:3]:
    print(o.title, "|", o.company, "|", o.location, "|", o.salary)