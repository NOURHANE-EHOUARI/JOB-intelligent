"""
Standardize France Travail CSV to match JobOffer schema
Colleague Task - Day 1
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
import hashlib


def standardize_france_travail(input_path: str, output_path: str = None) -> pd.DataFrame:
    """
    Standardize France Travail CSV to JobOffer schema
    
    Args:
        input_path: Path to raw France Travail CSV
        output_path: Path to save cleaned CSV (optional)
    
    Returns:
        Cleaned DataFrame matching JobOffer schema
    """
    # Read CSV
    df = pd.read_csv(input_path, encoding='utf-8')
    
    print(f"📥 Loaded {len(df)} offers from France Travail")
    print(f"📋 Original columns: {list(df.columns)}")
    
    # Define column mapping (CSV → JobOffer)
    # Most columns already match, just ensure consistency
    column_mapping = {
        'titre': 'titre',
        'entreprise': 'entreprise',
        'ville': 'ville',
        'code_postal': 'code_postal',
        'contrat': 'contrat',
        'salaire': 'salaire',
        'experience': 'experience',
        'competences': 'competences',
        'description': 'description',
        'date_publication': 'date_publication',
        'url': 'url',
        'source': 'source'
    }
    
    # Keep only JobOffer columns
    df = df[[col for col in column_mapping.keys() if col in df.columns]]
    
    # === DATA CLEANING RULES ===
    
    # 1. Clean text fields (remove extra spaces, normalize)
    text_columns = ['titre', 'entreprise', 'ville', 'contrat', 'salaire', 
                    'experience', 'competences', 'description']
    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].fillna('').astype(str).str.strip()
            df[col] = df[col].replace('', None)  # Empty strings → None
    
    # 2. Standardize contract types
    df['contrat'] = df['contrat'].apply(normalize_contract_type)
    
    # 3. Clean location
    df['ville'] = df['ville'].apply(clean_location)
    df['code_postal'] = df['code_postal'].apply(clean_postal_code)
    
    # 4. Parse and standardize dates (ISO 8601)
    df['date_publication'] = pd.to_datetime(df['date_publication'], errors='coerce')
    df['date_publication'] = df['date_publication'].dt.strftime('%Y-%m-%d')
    
    # 5. Ensure source is 'france_travail'
    df['source'] = 'france_travail'
    
    # 6. Generate deterministic IDs (don't use CSV ID)
    df['id'] = df.apply(generate_offer_id, axis=1)
    
    # 7. Add scraped_at timestamp
    from datetime import datetime, timezone
    df['scraped_at'] = datetime.now(timezone.utc).isoformat()
    
    # === VALIDATION ===
    required_columns = ['titre', 'entreprise', 'ville', 'url', 'description', 'source']
    missing_required = df[required_columns].isna().any()
    
    for col, has_missing in missing_required.items():
        if has_missing:
            missing_count = df[col].isna().sum()
            print(f"⚠️  Warning: {missing_count} missing values in '{col}'")
    
    # Drop rows with missing critical fields
    df = df.dropna(subset=['titre', 'ville', 'url'])
    
    # Remove duplicates based on title + company + location
    df = df.drop_duplicates(subset=['titre', 'entreprise', 'ville'], keep='first')
    
    print(f"✅ Cleaned dataset: {len(df)} offers")
    print(f"📊 Contract types: {df['contrat'].value_counts().to_dict()}")
    
    # Save if output path provided
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"💾 Saved to: {output_path}")
    
    return df


def normalize_contract_type(contract: str) -> str:
    """Normalize contract types to standard values"""
    if pd.isna(contract) or contract == '':
        return None
    
    contract = contract.lower().strip()
    
    # Mapping rules
    if any(x in contract for x in ['cdi', 'durée indéterminée']):
        return 'CDI'
    elif any(x in contract for x in ['cdd', 'durée déterminée', 'alternance', 'apprentissage']):
        return 'CDD'
    elif any(x in contract for x in ['stage', 'internship']):
        return 'STAGE'
    elif any(x in contract for x in ['freelance', 'indépendant', 'contractor']):
        return 'FREELANCE'
    elif any(x in contract for x in ['intérim', 'temporary', 'mission']):
        return 'INTERIM'
    else:
        return contract.upper() if len(contract) < 20 else 'AUTRE'


def clean_location(ville: str) -> str:
    """Clean and standardize location"""
    if pd.isna(ville) or ville == '':
        return None
    
    # Remove postal code prefix if present (e.g., "75 - PARIS 06" → "PARIS 06")
    import re
    ville = re.sub(r'^\d+\s*-\s*', '', str(ville))
    
    # Clean and capitalize
    ville = ville.strip().title()
    
    return ville if ville else None


def clean_postal_code(code: str) -> str:
    """Clean postal code format"""
    if pd.isna(code) or code == '':
        return None
    
    # Keep only digits
    code = ''.join(filter(str.isdigit, str(code)))
    
    # Ensure 5 digits for French postal codes
    if len(code) == 5:
        return code
    elif len(code) == 4:
        return '0' + code
    else:
        return None


def generate_offer_id(row: pd.Series) -> str:
    """Generate deterministic ID based on offer content"""
    content = f"{row['titre']}{row['entreprise']}{row['ville']}{row['source']}"
    return hashlib.md5(content.encode()).hexdigest()


if __name__ == "__main__":
    # Run standardization
    input_file = Path(__file__).parent / "offres_france_travail.csv"
    output_file = Path(__file__).parent / "offres_france_travail_clean.csv"
    
    df_clean = standardize_france_travail(input_file, output_file)
    
    # Print sample
    print("\n📄 Sample cleaned data:")
    print(df_clean.head(2).to_string())