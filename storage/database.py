# storage/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ──────────────────────────────────────────────────────────────
# Environment-aware database configuration
# ──────────────────────────────────────────────────────────────
def get_database_url():
    """Build DATABASE_URL based on execution environment."""
    if os.getenv("RUNNING_IN_DOCKER") == "true":
        host = os.getenv("DB_HOST", "postgres")
        port = os.getenv("DB_PORT", "5432")
    else:
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5433")
    
    user = os.getenv("DB_USER", "airflow")
    password = os.getenv("DB_PASSWORD", "airflow")
    dbname = os.getenv("DB_NAME", "job_intelligent")
    
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency for FastAPI / general use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_engine():
    """Backward-compatible getter for NLP modules."""
    return engine
