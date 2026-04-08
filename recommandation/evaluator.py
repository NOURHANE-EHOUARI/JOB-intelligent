import pandas as pd

def precision_at_k(resultats: pd.DataFrame, mots_cles: list, k: int = 5) -> float:
    """
    Calcule la precision@k :
    combien d'offres parmi les k premières sont vraiment pertinentes.
    """
    if resultats.empty:
        return 0.0

    top_k = resultats.head(k)
    pertinentes = 0

    for _, offre in top_k.iterrows():
        titre = str(offre.get("titre", "")).lower()
        desc  = str(offre.get("description", "")).lower()
        comps = str(offre.get("competences_extraites", "")).lower()

        texte = titre + " " + desc + " " + comps
        for mot in mots_cles:
            if mot.lower() in texte:
                pertinentes += 1
                break

    precision = pertinentes / k
    return round(precision, 2)


def recall_at_k(resultats: pd.DataFrame, df_total: pd.DataFrame,
                mots_cles: list, k: int = 5) -> float:
    """
    Calcule le recall@k :
    parmi toutes les offres pertinentes, combien on a retrouvé dans le top k.
    """
    # Total offres pertinentes dans tout le dataset
    total_pertinentes = 0
    for _, offre in df_total.iterrows():
        texte = (str(offre.get("titre", "")) + " " +
                 str(offre.get("description", ""))).lower()
        for mot in mots_cles:
            if mot.lower() in texte:
                total_pertinentes += 1
                break

    if total_pertinentes == 0:
        return 0.0

    # Pertinentes dans le top k
    top_k = resultats.head(k)
    trouvees = 0
    for _, offre in top_k.iterrows():
        texte = (str(offre.get("titre", "")) + " " +
                 str(offre.get("description", ""))).lower()
        for mot in mots_cles:
            if mot.lower() in texte:
                trouvees += 1
                break

    recall = trouvees / total_pertinentes
    return round(recall, 2)


def afficher_evaluation(resultats, df_total, mots_cles, k=5):
    """Affiche un rapport d'évaluation complet."""
    print("\n" + "="*40)
    print("📈 ÉVALUATION DU MODÈLE")
    print("="*40)

    p = precision_at_k(resultats, mots_cles, k)
    r = recall_at_k(resultats, df_total, mots_cles, k)

    print(f"   • Precision@{k} : {p:.0%}")
    print(f"   • Recall@{k}    : {r:.0%}")
    print(f"   • Offres retournées : {len(resultats)}")
    print("="*40 + "\n")