"""
Standardize Arbeitnow CSV to match JobOffer schema
Colleague Task - Day 2
"""
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import re


def strip_html(text: str) -> str:
    """Remove HTML tags from text"""
    if pd.isna(text) or text == '':
        return None
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', str(text))
    # Remove extra whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean if clean else None


def standardize_arbeitnow(input_path: str, output_path: str = None, 
                          min_description_length: int = 50) -> pd.DataFrame:
    """
    Standardize Arbeitnow CSV to JobOffer schema
    
    Args:
        input_path: Path to raw Arbeitnow CSV
        output_path: Path to save cleaned CSV (optional)
        min_description_length: Minimum chars for description to be kept
    
    Returns:
        Cleaned DataFrame matching JobOffer schema
    """
    df = pd.read_csv(input_path, encoding='utf-8')
    print(f"📥 Loaded {len(df)} offers from Arbeitnow")
    
    # === COLUMN MAPPING ===
    # Arbeitnow columns already match JobOffer schema mostly
    keep_columns = ['id', 'titre', 'entreprise', 'ville', 'code_postal', 
                    'contrat', 'salaire', 'experience', 'competences', 
                    'description', 'date_publication', 'url', 'source']
    
    # Keep only existing columns
    df = df[[col for col in keep_columns if col in df.columns]]
    
    # === DATA CLEANING ===
    
    # 1. Clean text fields
    text_cols = ['titre', 'entreprise', 'ville', 'contrat', 'salaire', 
                 'experience', 'competences']
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna('').astype(str).str.strip()
            # Replace "Non précisé" with None
            df[col] = df[col].replace(['Non précisé', 'nan', ''], None)
    
    # 2. Strip HTML from description
    if 'description' in df.columns:
        df['description'] = df['description'].apply(strip_html)
    
    # 3. Normalize contract types
    if 'contrat' in df.columns:
        df['contrat'] = df['contrat'].apply(normalize_contract_type)
    
    # 4. Clean location
    if 'ville' in df.columns:
        df['ville'] = df['ville'].apply(clean_location)
    if 'code_postal' in df.columns:
        df['code_postal'] = df['code_postal'].apply(clean_postal_code)
    
    # 5. Standardize dates
    if 'date_publication' in df.columns:
        df['date_publication'] = pd.to_datetime(df['date_publication'], errors='coerce')
        df['date_publication'] = df['date_publication'].dt.strftime('%Y-%m-%d')
    
    # 6. Set source
    df['source'] = 'arbeitnow'
    
    # 7. Generate deterministic IDs
    df['id'] = df.apply(generate_offer_id, axis=1)
    
    # 8. Add scraped_at
    df['scraped_at'] = datetime.now(timezone.utc).isoformat()
    
    # === FILTERING ===
    
    # Remove rows without critical fields
    df = df.dropna(subset=['titre', 'ville', 'url'])
    
    # Remove rows with too short descriptions (likely incomplete)
    if 'description' in df.columns:
        df = df[df['description'].str.len() >= min_description_length]
    
    # Remove duplicates
    df = df.drop_duplicates(subset=['titre', 'entreprise', 'ville'], keep='first')
    
    print(f"✅ After cleaning: {len(df)} offers")
    print(f"📊 Contract types: {df['contrat'].value_counts().dropna().to_dict()}")
    
    # Save if output path provided
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"💾 Saved to: {output_path}")
    
    return df


def normalize_contract_type(contract: str) -> str:
    """Normalize contract types to standard values"""
    if pd.isna(contract) or contract in ['', 'Non précisé']:
        return None
    
    contract = str(contract).lower().strip()
    
    if any(x in contract for x in ['cdi', 'permanent', 'unbefristet']):
        return 'CDI'
    elif any(x in contract for x in ['cdd', 'temporary', 'befristet', 'alternance']):
        return 'CDD'
    elif any(x in contract for x in ['stage', 'internship', 'praktikum']):
        return 'STAGE'
    elif any(x in contract for x in ['freelance', 'freiberufler', 'contractor']):
        return 'FREELANCE'
    elif any(x in contract for x in ['interim', 'zeitarbeit', 'mission']):
        return 'INTERIM'
    else:
        return contract.upper() if len(contract) < 30 else 'AUTRE'


def clean_location(ville: str) -> str:
    """Clean and standardize location"""
    if pd.isna(ville) or ville in ['', 'Non précisé']:
        return None
    
    # Remove country suffix if present (e.g., "Berlin, Germany" → "Berlin")
    ville = re.sub(r',\s*(Germany|France|Switzerland|Europe|Remote).*$', '', str(ville), flags=re.I)
    
    # Clean and title case
    ville = ville.strip().title()
    
    return ville if ville and len(ville) > 2 else None


def clean_postal_code(code: str) -> str:
    """Clean postal code format"""
    if pd.isna(code) or code in ['', 'Non précisé']:
        return None
    
    # Keep only digits
    code = ''.join(filter(str.isdigit, str(code)))
    
    # Ensure proper length
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
    input_file = Path(__file__).parent / "offres_arbeitnow.csv"
    output_file = Path(__file__).parent / "offres_arbeitnow_clean.csv"
    
    df_clean = standardize_arbeitnow(input_file, output_file)
    
    print("\n📄 Sample cleaned data:")
    print(df_clean[['titre', 'entreprise', 'ville', 'contrat']].head(2).to_string())