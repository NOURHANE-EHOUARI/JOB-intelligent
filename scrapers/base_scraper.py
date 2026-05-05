from abc import ABC, abstractmethod
from models.job_offer import JobOffer
import logging

# ──────────────────────────────────────────────────────────────
# FIX TÂCHE 4: Import déplacé en lazy pour éviter circular import
# (L'import était ici avant → SUPPRIMÉ pour éviter le conflit)
# ──────────────────────────────────────────────────────────────

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

    # ──────────────────────────────────────────────────────────────
    # AJOUT TÂCHE 4 : Méthode de validation qualité pré-ingestion
    # ──────────────────────────────────────────────────────────────
    def validate_offer_quality(self, title: str, description: str) -> bool:
        """
        Filtre pré-ETL : rejette les offres trop courtes ou contenant des mots-clés négatifs.
        À appeler dans parse_offer() ou scrape() avant de créer le JobOffer.
        
        Returns:
            True si l'offre passe tous les filtres, False sinon
        """
        # ✅ FIX: Import lazy à l'intérieur de la méthode pour éviter circular import
        from utils.nlp_config import load_nlp_config
        
        cfg = load_nlp_config()
        filters = cfg["scraping_filters"]
        negatives = cfg["negative_keywords"]
        
        # Concaténer pour recherche globale
        text = f"{title} {description}".lower()
        
        # 1. Longueur minimale de description
        if len(description) < filters["description_min_length"]:
            self.logger.debug(f"❌ Rejeté (desc trop courte): {title[:50]}")
            return False
            
        # 2. Mots-clés négatifs (spam/stage non rémunéré/arnaque)
        if any(neg in text for neg in negatives):
            self.logger.debug(f"❌ Rejeté (mot négatif): {title[:50]}")
            return False
            
        # 3. Au moins un mot-clé technique requis
        if not any(kw in text for kw in filters["required_tech_keywords"]):
            self.logger.debug(f"❌ Rejeté (aucun skill requis): {title[:50]}")
            return False
            
        self.logger.debug(f"✅ Validé: {title[:50]}")
        return True