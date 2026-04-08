import streamlit as st
import pandas as pd
from matcher import charger_offres, matcher_offres
from evaluator import afficher_evaluation, precision_at_k

# ── Config page ────────────────────────────────
st.set_page_config(
    page_title="Job Intelligent",
    page_icon="💼",
    layout="wide"
)

st.title("💼 Job Intelligent — Recommandeur d'offres Data")
st.markdown("*Trouve les offres qui correspondent à ton profil*")
st.divider()

# ── Chargement des données ─────────────────────
@st.cache_data
def load_data():
    return charger_offres()

df = load_data()
st.sidebar.success(f"✅ {len(df)} offres chargées")

# ── Formulaire profil ──────────────────────────
st.subheader("👤 Mon profil")

col1, col2 = st.columns(2)

with col1:
    titre = st.text_input(
        "Titre du poste recherché",
        placeholder="ex: data scientist"
    )
    competences_input = st.text_input(
        "Compétences (séparées par des virgules)",
        placeholder="ex: python, machine learning, sql"
    )
    experience = st.selectbox(
        "Expérience",
        ["Moins d'1 an", "1-2 ans", "3-5 ans", "5+ ans"]
    )

with col2:
    contrat = st.selectbox(
        "Type de contrat",
        ["", "CDI", "CDD", "Mission intérimaire"]
    )
    ville = st.text_input(
        "Ville souhaitée",
        placeholder="ex: Paris"
    )
    top_k = st.slider("Nombre de recommandations", 5, 20, 10)

st.divider()

# ── Bouton de recherche ────────────────────────
if st.button("🔍 Trouver mes offres", type="primary"):

    if not titre and not competences_input:
        st.warning("⚠️ Remplis au moins le titre ou les compétences !")
    else:
        competences = [c.strip() for c in competences_input.split(",") if c.strip()]

        profil = {
            "titre":       titre,
            "competences": competences,
            "experience":  experience,
            "contrat":     contrat,
            "ville":       ville
        }

        with st.spinner("Recherche en cours..."):
            resultats = matcher_offres(profil, df, top_k=top_k)

        if resultats.empty:
            st.error("❌ Aucune offre trouvée. Essaie d'autres critères.")
        else:
            # Évaluation
            p = precision_at_k(resultats, competences + [titre], k=5)
            st.success(f"✅ {len(resultats)} offres trouvées — Precision@5 : {p:.0%}")

            st.subheader("📋 Offres recommandées")

            for i, row in resultats.iterrows():
                with st.expander(f"#{i+1} — {row['titre']} | {row['entreprise']} | {row['ville']}"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown(f"**Contrat :** {row['contrat']}")
                        st.markdown(f"**Salaire :** {row['salaire']}")
                        st.markdown(f"**Ville :** {row['ville']}")
                    with col_b:
                        st.markdown(f"**Compétences :** {row['competences_extraites']}")
                        st.markdown(f"**Score :** {row['score']} pts")
                    if row.get("url") and row["url"] != "Non précisé":
                        st.markdown(f"[🔗 Voir l'offre]({row['url']})")
                    st.markdown(f"**Description :** {str(row['description'])[:300]}...")