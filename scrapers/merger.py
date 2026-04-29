import pandas as pd
import os

FICHIERS = [
    "../france_travail/offres_france_travail.csv",
    "offres_arbeitnow.csv",
    "offres_indeed.csv",
    "offres_linkedin.csv"
]

def fusionner_sources():
    print("🚀 Fusion de toutes les sources...\n")
    dfs = []

    for fichier in FICHIERS:
        if os.path.exists(fichier):
            df = pd.read_csv(fichier, encoding="utf-8-sig")
            print(f"✅ {fichier} → {len(df)} offres")
            dfs.append(df)
        else:
            print(f"⚠️  {fichier} introuvable, ignoré")

    if not dfs:
        print("❌ Aucun fichier trouvé")
        return

    # Fusionner
    df_final = pd.concat(dfs, ignore_index=True)
    df_final = df_final.drop_duplicates(subset=["id"])
    df_final = df_final.fillna("Non précisé")

    print(f"\n📊 Total final : {len(df_final)} offres uniques")
    print(f"📊 Sources : {df_final['source'].value_counts().to_dict()}")

    df_final.to_csv("offres_completes.csv", index=False, encoding="utf-8-sig")
    print("💾 Sauvegardé : offres_completes.csv ✅")

if __name__ == "__main__":
    fusionner_sources()