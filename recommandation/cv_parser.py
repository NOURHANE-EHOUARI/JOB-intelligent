"""
recommandation/cv_parser.py
Offline CV parser — no API, no internet required.
Extracts: titre, competences, experience from PDF or DOCX.
"""

import re
import yaml
import pdfplumber
from pathlib import Path
from typing import Optional


# ── Known job titles (French + English) ──────────────────────────
JOB_TITLES = [
    # Data
    "data scientist", "data engineer", "data analyst", "data architect",
    "data manager", "data steward", "data quality", "data governance",
    "machine learning engineer", "ml engineer", "ai engineer",
    "deep learning engineer", "nlp engineer", "computer vision engineer",
    # BI
    "business intelligence", "bi developer", "bi analyst", "bi engineer",
    "business analyst", "reporting analyst", "analytics engineer",
    # Dev
    "software engineer", "software developer", "backend developer",
    "frontend developer", "fullstack developer", "devops engineer",
    "cloud engineer", "platform engineer", "site reliability engineer",
    # Management
    "product manager", "product owner", "project manager", "tech lead",
    "data lead", "chief data officer", "cdo", "cto",
    # French variants
    "ingénieur données", "ingénieur data", "analyste données",
    "ingénieur machine learning", "développeur", "chef de projet",
    "responsable data", "architecte données", "consultant data",
    "alternant data", "stagiaire data",
]

# ── Experience patterns ───────────────────────────────────────────
EXP_PATTERNS = [
    # "5 ans d'expérience", "5 years of experience"
    (r'(\d+)\s*(?:ans?|years?)\s*(?:d[\'e\s])?(?:expérience|experience)', None),
    # "expérience de 3 ans"
    (r'(?:expérience|experience)\s+(?:de\s+)?(\d+)\s*(?:ans?|years?)', None),
    # "depuis 2019" → compute approximate years
    (r'depuis\s+(20\d{2})', 'year'),
    # "2019 - présent"
    (r'(20\d{2})\s*[-–]\s*(?:présent|present|aujourd\'hui|now|current)', 'year'),
]

EXPERIENCE_BUCKETS = [
    (0, 1,  "Moins d'1 an"),
    (1, 3,  "1-2 ans"),
    (3, 5,  "3-5 ans"),
    (5, 99, "5+ ans"),
]


# ── Text extraction ───────────────────────────────────────────────

def extract_text_pdf(uploaded_file) -> str:
    with pdfplumber.open(uploaded_file) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return "\n".join(pages)


def extract_text_docx(uploaded_file) -> str:
    from docx import Document
    doc = Document(uploaded_file)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


# ── Skill extraction ──────────────────────────────────────────────

def load_skills_from_config(config_path: str = "config/nlp_config.yaml") -> list:
    """Load skills from your existing nlp_config.yaml taxonomy."""
    skills = []
    path = Path(config_path)
    if not path.exists():
        # Fallback hardcoded list if config missing
        return _fallback_skills()
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    skill_section = cfg.get("skills", {})
    for category, items in skill_section.items():
        if isinstance(items, list):
            skills.extend(items)
        elif isinstance(items, dict):
            for sub_items in items.values():
                if isinstance(sub_items, list):
                    skills.extend(sub_items)
    # Add extra technical skills not in config
    skills.extend(_extra_skills())
    # Deduplicate preserving order
    seen = set()
    result = []
    for s in skills:
        if s.lower() not in seen:
            seen.add(s.lower())
            result.append(s)
    return result


def _extra_skills() -> list:
    return [
        "Python", "R", "SQL", "NoSQL", "Java", "Scala", "Go", "Rust", "C++",
        "Spark", "PySpark", "Hadoop", "Kafka", "Airflow", "dbt", "Luigi",
        "Pandas", "NumPy", "Scikit-learn", "TensorFlow", "PyTorch", "Keras",
        "XGBoost", "LightGBM", "NLTK", "spaCy", "HuggingFace", "LangChain",
        "PostgreSQL", "MySQL", "MongoDB", "Cassandra", "Redis", "Elasticsearch",
        "Snowflake", "BigQuery", "Redshift", "Databricks", "Delta Lake",
        "AWS", "Azure", "GCP", "S3", "EC2", "Lambda", "Azure Blob", "ADLS",
        "Docker", "Kubernetes", "Terraform", "CI/CD", "GitHub Actions", "Jenkins",
        "Power BI", "Tableau", "Looker", "Metabase", "Grafana", "Superset",
        "Excel", "DAX", "Power Query",
        "Git", "GitHub", "GitLab", "Jira", "Confluence",
        "FastAPI", "Flask", "Django", "REST", "GraphQL", "Streamlit",
        "Linux", "Bash", "Shell",
        "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
        "MLOps", "DataOps", "ETL", "ELT", "Data Warehouse", "Data Lake",
        "Statistics", "Probability", "A/B Testing", "Feature Engineering",
        "Agile", "Scrum", "GDPR",
    ]


def _fallback_skills() -> list:
    return _extra_skills()


def extract_skills(text: str, all_skills: list) -> list:
    """Match skills from text using word boundaries."""
    text_lower = text.lower()
    found = []
    for skill in all_skills:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found.append(skill)
    return found


# ── Job title detection ───────────────────────────────────────────

def detect_title(text: str) -> Optional[str]:
    """Find the most likely job title in the CV text."""
    text_lower = text.lower()

    # Sort by length desc so longer/more specific titles match first
    sorted_titles = sorted(JOB_TITLES, key=len, reverse=True)

    # Look in first 500 chars (header of CV usually has the title)
    header = text_lower[:500]
    for title in sorted_titles:
        if title in header:
            return title.title()

    # Fall back to full document
    for title in sorted_titles:
        if title in text_lower:
            return title.title()

    return None


# ── Experience detection ──────────────────────────────────────────

def detect_experience(text: str) -> str:
    """Detect years of experience from CV text."""
    import datetime
    current_year = datetime.datetime.now().year
    years_found = []

    text_lower = text.lower()

    for pattern, mode in EXP_PATTERNS:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            try:
                val = int(match)
                if mode == 'year':
                    # It's a start year — compute duration
                    if 2000 <= val <= current_year:
                        years_found.append(current_year - val)
                else:
                    # It's a direct year count
                    if 0 <= val <= 40:
                        years_found.append(val)
            except ValueError:
                continue

    if not years_found:
        return "Moins d'1 an"

    # Take the maximum found (most experienced mention wins)
    max_years = max(years_found)

    for low, high, label in EXPERIENCE_BUCKETS:
        if low <= max_years < high:
            return label

    return "5+ ans"


# ── Main parser ───────────────────────────────────────────────────

def parse_cv(uploaded_file) -> dict:
    """
    Main entry point. Takes a Streamlit UploadedFile.
    Returns dict with keys: titre, competences, experience.
    """
    filename = uploaded_file.name.lower()

    if filename.endswith(".pdf"):
        text = extract_text_pdf(uploaded_file)
    elif filename.endswith(".docx"):
        text = extract_text_docx(uploaded_file)
    else:
        raise ValueError(f"Format non supporté : {filename}")

    if len(text.strip()) < 30:
        raise ValueError("Le CV semble vide ou illisible.")

    all_skills = load_skills_from_config()

    titre      = detect_title(text) or ""
    competences = extract_skills(text, all_skills)
    experience  = detect_experience(text)

    return {
        "titre":       titre,
        "competences": competences[:12],  # cap at 12 most relevant
        "experience":  experience,
        "_raw_length": len(text),
    }
