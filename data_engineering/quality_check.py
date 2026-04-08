import pandas as pd
from collections import Counter

def verifier_qualite(df: pd.DataFrame) -> pd.DataFrame:
    """
    Vérifie et affiche un rapport de qualité des données.
    """
    print("\n" + "="*50)
    print("📊 RAPPORT DE QUALITÉ DES DONNÉES")
    print("="*50)

    total = len(df)
    print(f"\n📁 Total offres : {total}")

    # ── Valeurs manquantes ──────────────────────────
    print("\n🔍 Valeurs manquantes :")
    colonnes_importantes = [
        "titre", "entreprise", "ville",
        "contrat", "salaire", "competences_extraites",
        "latitude", "longitude"
    ]

    for col in colonnes_importantes:
        if col in df.columns:
            manquants = df[col].isin(["Non précisé", "", None]).sum()
            manquants += df[col].isna().sum()
            pct = round(manquants / total * 100, 1)
            status = "✅" if pct < 30 else "⚠️ "
            print(f"   {status} {col:<25} {manquants:>4} manquants ({pct}%)")

    # ── Distribution des contrats ───────────────────
    print("\n📋 Distribution des contrats :")
    if "contrat" in df.columns:
        for contrat, count in df["contrat"].value_counts().head(5).items():
            pct = round(count / total * 100, 1)
            print(f"   • {contrat:<25} {count:>4} offres ({pct}%)")

    # ── Top 10 villes ───────────────────────────────
    print("\n🏙️  Top 10 villes :")
    if "ville" in df.columns:
        for ville, count in df["ville"].value_counts().head(10).items():
            print(f"   • {ville:<25} {count:>4} offres")

    # ── Top 10 compétences ──────────────────────────
    print("\n🛠️  Top 10 compétences demandées :")
    if "competences_extraites" in df.columns:
        toutes_comp = []
        for comps in df["competences_extraites"].dropna():
            if comps and comps not in ["Non précisé", ""]:
                toutes_comp.extend([c.strip() for c in comps.split(",")])

        top_comp = Counter(toutes_comp).most_common(10)
        for comp, count in top_comp:
            if comp:  # ignorer les valeurs vides
                print(f"   • {comp:<25} {count:>4} offres")

    # ── Couverture géocodage ────────────────────────
    print("\n🌍 Couverture géocodage :")
    if "latitude" in df.columns:
        geocodees = df["latitude"].notna().sum()
        pct = round(geocodees / total * 100, 1)
        print(f"   ✅ {geocodees}/{total} offres géolocalisées ({pct}%)")

    print("\n" + "="*50 + "\n")
    return df