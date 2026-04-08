from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from storage.database import Base

class OffreEmploi(Base):
    __tablename__ = "offres_emploi"

    id              = Column(String, primary_key=True)
    titre           = Column(String, nullable=False)
    entreprise      = Column(String)
    ville           = Column(String)
    code_postal     = Column(String)
    contrat         = Column(String)
    salaire         = Column(String)
    experience      = Column(String)
    competences     = Column(Text)
    description     = Column(Text)
    date_publication = Column(String)
    url             = Column(String)
    source          = Column(String)
    scraped_at      = Column(String)
    created_at      = Column(DateTime, server_default=func.now())
