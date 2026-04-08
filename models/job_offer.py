from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import uuid, json
import hashlib

@dataclass
class JobOffer:
    titre: str
    entreprise: str
    ville: str
    source: str                          # "adzuna" | "france_travail"
    url: str
    description: str
    code_postal: Optional[str] = None
    contrat: Optional[str] = None
    salaire: Optional[str] = None
    experience: Optional[str] = None
    competences: str = ""                # comma-separated string like her format
    date_publication: Optional[str] = None
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    id: str = field(default_factory=lambda: "")

    def __post_init__(self):
        if not self.id:
            # deterministic ID based on content — same offer = same ID
            content = f"{self.titre}{self.entreprise}{self.ville}{self.source}"
            self.id = hashlib.md5(content.encode()).hexdigest()

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
