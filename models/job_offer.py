from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import uuid, json

@dataclass
class JobOffer:
    title: str
    company: str
    location: str
    source: str                        # "indeed" | "linkedin" | "france_travail"
    url: str
    description: str
    contract_type: Optional[str] = None   # CDI, CDD, Freelance...
    salary: Optional[str] = None
    skills: list[str] = field(default_factory=list)
    posted_at: Optional[str] = None
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)