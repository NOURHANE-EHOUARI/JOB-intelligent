from abc import ABC, abstractmethod
from models.job_offer import JobOffer
import logging

logging.basicConfig(level=logging.INFO)

class BaseScraper(ABC):
    def __init__(self, keywords: list[str], location: str, max_pages: int = 5):
        self.keywords = keywords
        self.location = location
        self.max_pages = max_pages
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def scrape(self) -> list[JobOffer]:
        """Scrape and return a list of normalized JobOffer objects."""
        pass

    @abstractmethod
    def parse_offer(self, raw: dict) -> JobOffer:
        """Parse a raw dict into a JobOffer."""
        pass