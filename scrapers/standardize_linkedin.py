"""
Minimal standardization for LinkedIn CSV (low quality data)
Only keep rows with valid title + URL + description
Colleague Task - Day 2 - FIXED VERSION
"""
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
import hashlib


def standardize_linkedin(input_path: str, output_path: str = None) -> pd.DataFrame:
    """
    Filter LinkedIn CSV - keep only usable rows
    """
    df = pd.read_csv(input_path, encoding='utf-8')
    print(f"📥 Loaded {len(df)} offers from LinkedIn")
    
    # Keep only JobOffer columns
    keep_columns = ['id', 'titre', 'entreprise', 'ville', 'code_postal', 
                    'contrat', 'salaire', 'experience', 'competences', 
                    'description', 'date_publication', 'url', 'source']
    df = df[[col for col in keep_columns if col in df.columns]]
    
    # Clean "Non précisé" → None
    for col in df.columns:
        df[col] = df[col].replace(['Non précisé', 'nan', ''], None)
    
    # CRITICAL FILTER: Keep only rows with title + url
    df = df.dropna(subset=['titre', 'url'])
    
    # Optional: Require minimum description length (FIXED: handle NaN safely)
    if 'description' in df.columns:
        # Convert to string safely, then check length
        df['_desc_len'] = df['description'].fillna('').astype(str).str.len()
        df = df[df['_desc_len'] >= 30]
        df = df.drop(columns=['_desc_len'])  # Clean up temp column
    
    # Set source
    df['source'] = 'linkedin'
    
    # Generate IDs
    df['id'] = df.apply(lambda r: hashlib.md5(
        f"{r['titre']}{r['entreprise']}{r['ville']}linkedin".encode()
    ).hexdigest(), axis=1)
    
    df['scraped_at'] = datetime.now(timezone.utc).isoformat()
    
    # Remove duplicates
    df = df.drop_duplicates(subset=['titre', 'url'], keep='first')
    
    print(f"✅ After filtering: {len(df)} usable offers")
    
    if output_path and len(df) > 0:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"💾 Saved to: {output_path}")
    elif len(df) == 0:
        print("⚠️  No usable LinkedIn offers found — this source may be skipped")
    
    return df


if __name__ == "__main__":
    input_file = Path(__file__).parent / "offres_linkedin.csv"
    output_file = Path(__file__).parent / "offres_linkedin_clean.csv"
    
    df_clean = standardize_linkedin(input_file, output_file)
    
    if len(df_clean) > 0:
        print("\n📄 Sample:")
        print(df_clean[['titre', 'entreprise', 'ville']].head(2).to_string())