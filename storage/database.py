from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

DB_URL = "postgresql+psycopg2://airflow:airflow@localhost:5433/job_intelligent"

engine = create_engine(DB_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def get_engine():
    return engine

def test_connection():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        print("Connected:", result.fetchone()[0])
