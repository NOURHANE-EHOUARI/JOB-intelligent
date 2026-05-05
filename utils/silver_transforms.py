"""
utils/silver_transforms.py
Reusable transformation functions for Silver layer
Colleague Task - Day 3 | Production Ready
"""
import re
import yaml
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# ==========================================================
# CONFIG & UTILS
# ==========================================================

def load_business_rules(config_path: str = "config/silver_business_rules.yaml") -> Dict:
    """Load business rules from YAML config with error handling."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Business rules config not found: {path.resolve()}")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {config_path}: {e}")


# ==========================================================
# TRANSFORMATION FUNCTIONS
# ==========================================================

def normalize_contract(contract: str, rules: Optional[Dict] = None) -> Optional[str]:
    """Normalize contract type using business rules mapping."""
    if pd.isna(contract) or str(contract).strip() == '':
        return None
    
    rules = rules or load_business_rules()
    contract_lower = str(contract).lower().strip()
    mapping = rules.get('contract_mapping', {})
    
    for category, config in mapping.items():
        if category == 'default':
            continue
        keywords = config.get('keywords', [])
        if any(kw in contract_lower for kw in keywords):
            return config['output']
            
    default_val = mapping.get('default', 'AUTRE')
    return default_val if default_val != 'AUTRE' else None


def parse_salary(salary_raw: str, rules: Optional[Dict] = None) -> Tuple[Optional[float], Optional[float]]:
    """Parse salary string into (min_annual, max_annual) in EUR."""
    if pd.isna(salary_raw) or str(salary_raw).strip() == '':
        return None, None
        
    rules = rules or load_business_rules()
    salary_str = str(salary_raw).lower().strip()
    patterns = rules.get('salary_parsing', {}).get('patterns', {})
    
    # 1. Range in K (e.g., "35k-45k")
    if 'range_k' in patterns:
        match = re.search(patterns['range_k'], salary_str)
        if match:
            min_val = float(match.group(1).replace(',', '.')) * 1000
            max_val = float(match.group(2).replace(',', '.')) * 1000 if match.group(2) else min_val
            return min_val, max_val
            
    # 2. Range in EUR (e.g., "50000 - 60000 EUR")
    if 'range_euro' in patterns:
        match = re.search(patterns['range_euro'], salary_str)
        if match:
            min_val = float(match.group(1))
            max_val = float(match.group(2)) if match.group(2) else min_val
            return min_val, max_val
            
    # 3. Explicit monthly regex
    if 'monthly_euro' in patterns:
        match = re.search(patterns['monthly_euro'], salary_str)
        if match:
            monthly = float(match.group(1).replace(',', '.'))
            return monthly * 12, monthly * 12
            
    # 4. Fallback: extract any number & apply smart heuristics
    numbers = re.findall(r'(\d+[.,]?\d*)', salary_str)
    if numbers:
        val = float(numbers[0].replace(',', '.'))
        # If value seems too low for an annual salary, assume it's in hundreds
        if val < 100:
            val *= 100
            
        # ✅ FIX: Detect monthly indicators (French & English)
        monthly_keywords = ['mois', 'mensuel', 'mensuelle', 'monthly', 'per month', 'pm']
        if any(kw in salary_str for kw in monthly_keywords):
            val *= 12
            
        return val, val
        
    return None, None


def clean_location(ville: str, code_postal: Optional[str] = None, rules: Optional[Dict] = None) -> Dict[str, Optional[str]]:
    """Clean and standardize location. Returns dict with ville_clean, code_postal_clean, region."""
    rules = rules or load_business_rules()
    result = {'ville_clean': None, 'code_postal_clean': None, 'region': None}
    
    # Postal code cleaning & region inference
    if code_postal and not pd.isna(code_postal):
        pc = ''.join(filter(str.isdigit, str(code_postal)))
        regex = rules.get('location_rules', {}).get('postal_code_regex', r'^\d{5}$')
        if re.match(regex, pc):
            result['code_postal_clean'] = pc
            prefix = pc[:2]
            region_map = {
                '75': 'Île-de-France', '92': 'Île-de-France', '93': 'Île-de-France', '94': 'Île-de-France',
                '13': 'PACA', '69': 'Auvergne-Rhône-Alpes', '31': 'Occitanie', '33': 'Nouvelle-Aquitaine',
                '59': 'Hauts-de-France', '44': 'Pays de la Loire', '34': 'Occitanie', '06': 'PACA'
            }
            result['region'] = region_map.get(prefix)
            
    # City cleaning
    if ville and not pd.isna(ville):
        v = str(ville).strip()
        for country in rules.get('location_rules', {}).get('remove_countries', []):
            v = re.sub(rf',?\s*{country}\s*$', '', v, flags=re.IGNORECASE)
            
        aliases = rules.get('location_rules', {}).get('city_aliases', {})
        v_lower = v.lower()
        for alias, canonical in aliases.items():
            if alias in v_lower:
                v = canonical
                break
                
        v = re.sub(r'\s+', ' ', v).strip().title()
        if len(v) >= 2:
            result['ville_clean'] = v
            
    return result


def validate_offer_quality(row: pd.Series, rules: Optional[Dict] = None) -> bool:
    """Check if an offer meets quality thresholds for Silver layer."""
    rules = rules or load_business_rules()
    thresholds = rules.get('quality_thresholds', {})
    
    for field in thresholds.get('required_fields', []):
        if field in row.index and (pd.isna(row[field]) or str(row[field]).strip() == ''):
            return False
            
    if 'description' in row.index and not pd.isna(row['description']):
        if len(str(row['description'])) < thresholds.get('min_description_length', 50):
            return False
            
    if 'titre' in row.index and not pd.isna(row['titre']):
        tlen = len(str(row['titre']))
        if tlen < thresholds.get('min_title_length', 10) or tlen > thresholds.get('max_title_length', 200):
            return False
            
    return True


def extract_skills(text: str, rules: Optional[Dict] = None) -> List[str]:
    """Extract skills from text using keyword matching & word boundaries."""
    if pd.isna(text) or str(text).strip() == '':
        return []
        
    rules = rules or load_business_rules()
    text_lower = str(text).lower()
    skills_config = rules.get('skill_extraction', {})
    all_skills = []
    
    for category in ['hard_skills', 'soft_skills']:
        subcats = skills_config.get(category, {})
        if isinstance(subcats, dict):
            for skill_list in subcats.values():
                all_skills.extend(skill_list)
        elif isinstance(subcats, list):
            all_skills.extend(subcats)
            
    detected = []
    for skill in all_skills:
        if re.search(r'\b' + re.escape(skill.lower()) + r'\b', text_lower):
            detected.append(skill)
            
    return detected


# ==========================================================
# MAIN ORCHESTRATOR (SILVER PIPELINE)
# ==========================================================

def transform_to_silver(df_raw: pd.DataFrame, rules: Optional[Dict] = None) -> pd.DataFrame:
    """
    Main Silver layer transformation pipeline.
    Applies quality filters, normalization, parsing, and enrichment.
    """
    if df_raw.empty:
        logger.warning("Input DataFrame is empty. Returning empty Silver DataFrame.")
        return df_raw.copy()
        
    rules = rules or load_business_rules()
    logger.info(f"Starting Silver transform on {len(df_raw)} raw records...")
    
    # 1. Quality Filtering
    logger.info("Applying quality filters...")
    quality_mask = df_raw.apply(lambda row: validate_offer_quality(row, rules), axis=1)
    df = df_raw[quality_mask].copy()
    logger.info(f"Quality filter passed: {len(df)} records ({len(df)/len(df_raw)*100:.1f}%)")
    
    # 2. Contract Normalization
    logger.info("Normalizing contracts...")
    df['contrat_normalized'] = df['contrat'].apply(lambda x: normalize_contract(x, rules))
    
    # 3. Salary Parsing
    logger.info("Parsing salaries...")
    salary_parsed = df['salaire'].apply(lambda x: pd.Series(parse_salary(x, rules)))
    df['salaire_min'] = salary_parsed[0]
    df['salaire_max'] = salary_parsed[1]
    
    # 4. Location Standardization
    logger.info("Cleaning locations...")
    location_clean = df.apply(
        lambda row: clean_location(row.get('ville'), row.get('code_postal'), rules), axis=1
    )
    df['ville_clean'] = location_clean.str['ville_clean']
    df['code_postal_clean'] = location_clean.str['code_postal_clean']
    df['region'] = location_clean.str['region']
    
    # 5. Skill Extraction
    logger.info("Extracting skills from descriptions...")
    df['skills_detected'] = df['description'].apply(lambda x: extract_skills(x, rules))
    
    logger.info("✅ Silver transformation completed.")
    return df


# ==========================================================
# QUICK VALIDATION TEST
# ==========================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    try:
        logger.info("Testing config loading...")
        rules = load_business_rules()
        logger.info(f"✅ Config loaded. Contract categories: {list(rules.get('contract_mapping', {}).keys())}")
        logger.info(f"✅ Skill categories: {list(rules.get('skill_extraction', {}).keys())}")
    except Exception as e:
        logger.error(f"❌ Config test failed: {e}")