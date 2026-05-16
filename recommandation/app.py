import streamlit as st
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from matcher import charger_offres, matcher_offres
from evaluator import precision_at_k
from cv_parser import parse_cv

# ── Page config ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Job Intelligent",
    page_icon="💼",
    layout="wide"
)

st.markdown("""
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">

<style>
  html, body, [data-testid="stApp"] {
    font-family: 'Inter', -apple-system, sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  #MainMenu, footer { visibility: hidden; }
  [data-testid="stToolbar"] { display: none !important; }
  details summary { font-size: 14px !important; font-weight: 500 !important; }
  [data-testid="stTabs"] button {
    font-family: 'Inter', sans-serif !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
  }

  /* ── Light mode ─────────────────────────── */
  @media (prefers-color-scheme: light) {
    .cv-info-box {
      background: #f0f9ff !important;
      border: 1px solid #bae6fd !important;
    }
    .cv-info-label { color: #0369a1 !important; }
    .empty-state   { border-color: #d1d5db !important; }
    .empty-icon    { color: #d1d5db !important; }
    .empty-text    { color: #6b7280 !important; }
    .empty-sub     { color: #9ca3af !important; }
    .ji-header-sub { color: #6b7280 !important; }
    .ji-sidebar-sub { color: #6b7280 !important; }
    .ji-small      { color: #6b7280 !important; }
    .ji-small-muted { color: #9ca3af !important; }
    .ji-section-note { color: #6b7280 !important; }
    .ji-correct-note { color: #6b7280 !important; }
  }

  /* ── Dark mode ──────────────────────────── */
  @media (prefers-color-scheme: dark) {
    .cv-info-box {
      background: #0c1a2e !important;
      border: 1px solid #1e3a5f !important;
    }
    .cv-info-label { color: #60a5fa !important; }
    .empty-state   { border-color: #374151 !important; }
    .empty-icon    { color: #374151 !important; }
    .empty-text    { color: #9ca3af !important; }
    .empty-sub     { color: #6b7280 !important; }
    .ji-header-sub { color: #9ca3af !important; }
    .ji-sidebar-sub { color: #9ca3af !important; }
    .ji-small      { color: #9ca3af !important; }
    .ji-small-muted { color: #6b7280 !important; }
    .ji-section-note { color: #9ca3af !important; }
    .ji-correct-note { color: #9ca3af !important; }
  }
</style>
""", unsafe_allow_html=True)

# ── Data ─────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    return charger_offres()

df = load_data()

# ── Sidebar ───────────────────────────────────────────────────────
st.sidebar.markdown(f"""
<div style="padding:8px 0 16px;">
  <div style="font-size:16px;font-weight:700;margin-bottom:4px;">
    <i class="bi bi-briefcase-fill" style="color:#3b82f6;margin-right:6px;"></i>Job Intelligent
  </div>
  <div class="ji-sidebar-sub" style="font-size:12px;">Recommandeur d'offres Data</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.success(f"**{len(df):,}** offres chargées")
st.sidebar.divider()

# ── Theme toggle ─────────────────────────────────────────────────
st.sidebar.markdown("**Thème**")
theme = st.sidebar.radio(
    "Mode d'affichage",
    ["🌙 Sombre", "☀️ Clair"],
    horizontal=True,
    key="theme_toggle",
    label_visibility="collapsed"
)

if theme == "☀️ Clair":
    st.markdown("""
    <style>
      html, body, [data-testid="stApp"] {
        background-color: #ffffff !important;
        color: #111827 !important;
      }
      [data-testid="stSidebar"] { background-color: #f9fafb !important; }
      .stButton>button { background-color: #3b82f6 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
      html, body, [data-testid="stApp"] {
        background-color: #0f172a !important;
        color: #f1f5f9 !important;
      }
      [data-testid="stSidebar"] { background-color: #1e293b !important; }
      .stButton>button { background-color: #3b82f6 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

st.sidebar.divider()
if 'source' in df.columns:
    st.sidebar.markdown("**Sources actives**")
    for src, count in df['source'].value_counts().head(8).items():
        st.sidebar.markdown(
            f"<small class='ji-small'><i class='bi bi-dot'></i> {src} - {count:,}</small>",
            unsafe_allow_html=True
        )

st.sidebar.divider()
st.sidebar.markdown("""
<small class="ji-small-muted">
  <i class="bi bi-cpu" style="margin-right:4px;"></i>NLP: sentence-transformers<br>
  <i class="bi bi-database" style="margin-right:4px;"></i>DWH: PostgreSQL star schema<br>
  <i class="bi bi-cloud" style="margin-right:4px;"></i>Cloud: Azure ADLS Gen2<br>
  <i class="bi bi-file-earmark-person" style="margin-right:4px;"></i>CV parser: offline NLP
</small>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────
st.markdown("""
<h2 style="font-size:22px;font-weight:700;margin-bottom:2px;">
  <i class="bi bi-briefcase-fill" style="color:#3b82f6;margin-right:8px;"></i>
  Job Intelligent - Recommandeur d'offres Data
</h2>
<p class="ji-header-sub" style="font-size:14px;margin-top:0;">
  Trouve les offres qui correspondent à ton profil - manuellement ou via ton CV
</p>
""", unsafe_allow_html=True)
st.divider()

# ── Shared result renderer ────────────────────────────────────────
def render_results(resultats, competences, titre):
    p = precision_at_k(resultats, competences + [titre], k=5)
    st.success(f"**{len(resultats)} offres trouvées** ")
    st.markdown("""
    <p class="ji-section-note" style="font-size:13px;">
      <i class="bi bi-card-list" style="margin-right:6px;color:#3b82f6;"></i>
      Offres recommandées
    </p>
    """, unsafe_allow_html=True)
    for i, row in resultats.iterrows():
        with st.expander(
            f"#{i+1} - {row['titre']}  |  {row['entreprise']}  |  {row['ville']}"
        ):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**<i class='bi bi-file-text' style='color:#3b82f6'></i> Contrat :** {row['contrat']}", unsafe_allow_html=True)
                st.markdown(f"**<i class='bi bi-currency-euro' style='color:#22c55e'></i> Salaire :** {row['salaire']}", unsafe_allow_html=True)
                st.markdown(f"**<i class='bi bi-geo-alt' style='color:#f59e0b'></i> Ville :** {row['ville']}", unsafe_allow_html=True)
            with col_b:
                st.markdown(f"**<i class='bi bi-code-slash' style='color:#6366f1'></i> Compétences :** {row['competences_extraites']}", unsafe_allow_html=True)
                st.markdown(f"**<i class='bi bi-graph-up' style='color:#3b82f6'></i> Score :** {row['score']} pts", unsafe_allow_html=True)
            if row.get("url") and str(row["url"]) not in ["Non précisé", "nan", ""]:
                st.markdown(
                    f"[<i class='bi bi-box-arrow-up-right'></i> Voir l'offre]({row['url']})",
                    unsafe_allow_html=True
                )
            st.markdown(f"**Description :** {str(row['description'])[:300]}...")

# ── Tabs ──────────────────────────────────────────────────────────
tab_manual, tab_cv = st.tabs([
    "  Saisie manuelle",
    "  Importer mon CV"
])

# ─────────────────────────────────────────────────────────────────
# TAB 1 — Manual
# ─────────────────────────────────────────────────────────────────
with tab_manual:
    st.markdown("""
    <p class="ji-section-note" style="font-size:13px;margin-bottom:16px;">
      <i class="bi bi-person-lines-fill" style="margin-right:6px;color:#3b82f6;"></i>
      Remplis ton profil manuellement pour trouver les offres correspondantes.
    </p>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        titre = st.text_input(
            "Titre du poste recherché",
            placeholder="ex: data scientist",
            key="m_titre"
        )
        competences_input = st.text_input(
            "Compétences (séparées par des virgules)",
            placeholder="ex: python, machine learning, sql",
            key="m_comp"
        )
        experience = st.selectbox(
            "Expérience",
            ["Moins d'1 an", "1-2 ans", "3-5 ans", "5+ ans"],
            key="m_exp"
        )
    with col2:
        contrat = st.selectbox(
            "Type de contrat",
            ["", "CDI", "CDD", "Mission intérimaire"],
            key="m_contrat"
        )
        ville = st.text_input(
            "Ville souhaitée",
            placeholder="ex: Paris",
            key="m_ville"
        )
        top_k = st.slider("Nombre de recommandations", 5, 20, 10, key="m_topk")

    st.divider()

    if st.button("Trouver mes offres", type="primary", key="m_search"):
        if not titre and not competences_input:
            st.warning("Remplis au moins le titre ou les compétences.")
        else:
            competences = [c.strip() for c in competences_input.split(",") if c.strip()]
            profil = {
                "titre": titre,
                "competences": competences,
                "experience": experience,
                "contrat": contrat,
                "ville": ville
            }
            with st.spinner("Recherche en cours..."):
                resultats = matcher_offres(profil, df, top_k=top_k)
            if resultats.empty:
                st.error("Aucune offre trouvée. Essaie d'autres critères.")
            else:
                render_results(resultats, competences, titre)

# ─────────────────────────────────────────────────────────────────
# TAB 2 — CV Upload
# ─────────────────────────────────────────────────────────────────
with tab_cv:
    st.markdown("""
    <p class="ji-section-note" style="font-size:13px;margin-bottom:16px;">
      <i class="bi bi-file-earmark-person" style="margin-right:6px;color:#3b82f6;"></i>
      Importe ton CV - le parser NLP extrait automatiquement ton profil
      . Tu n'as qu'à choisir ta ville et lancer la recherche.
    </p>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Dépose ton CV ici (PDF ou DOCX)",
        type=["pdf", "docx"],
        help="Ton CV est analysé localement - aucune donnée n'est envoyée à l'extérieur."
    )

    if "cv_profile" not in st.session_state:
        st.session_state.cv_profile = None
    if "cv_filename" not in st.session_state:
        st.session_state.cv_filename = None

    if uploaded_file is not None:
        if st.session_state.cv_filename != uploaded_file.name:
            with st.spinner("Analyse du CV en cours..."):
                try:
                    profile = parse_cv(uploaded_file)
                    st.session_state.cv_profile = profile
                    st.session_state.cv_filename = uploaded_file.name
                except Exception as e:
                    st.error(f"Erreur lors de l'analyse : {e}")
                    st.stop()

        profile = st.session_state.cv_profile

        # Extracted profile box - theme-aware via CSS classes
        st.markdown("""
        <div class="cv-info-box" style="border-radius:10px;padding:16px 20px;margin-bottom:20px;">
          <div class="cv-info-label"
               style="font-size:12px;font-weight:600;text-transform:uppercase;
                      letter-spacing:.06em;margin-bottom:10px;">
            <i class="bi bi-cpu" style="margin-right:6px;"></i>Profil extrait automatiquement
          </div>
        """, unsafe_allow_html=True)

        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            st.markdown("**Poste détecté**")
            st.info(profile.get("titre") or "Non détecté")
        with col_p2:
            st.markdown("**Compétences détectées**")
            skills = profile.get("competences", [])
            st.info(", ".join(skills[:8]) + ("..." if len(skills) > 8 else "") if skills else "Aucune")
        with col_p3:
            st.markdown("**Expérience détectée**")
            st.info(profile.get("experience", "Non détectée"))

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
        <p class="ji-correct-note" style="font-size:12px;margin-bottom:8px;">
          <i class="bi bi-pencil" style="margin-right:4px;"></i>
          Corrige si besoin, choisis ta ville, puis lance la recherche.
        </p>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            cv_titre = st.text_input(
                "Poste recherché",
                value=profile.get("titre", ""),
                key="cv_titre"
            )
            cv_comp_input = st.text_input(
                "Compétences",
                value=", ".join(profile.get("competences", [])),
                key="cv_comp"
            )
            exp_options = ["Moins d'1 an", "1-2 ans", "3-5 ans", "5+ ans"]
            detected_exp = profile.get("experience", "Moins d'1 an")
            exp_index = exp_options.index(detected_exp) if detected_exp in exp_options else 0
            cv_experience = st.selectbox(
                "Expérience", exp_options, index=exp_index, key="cv_exp"
            )
        with col2:
            cv_contrat = st.selectbox(
                "Type de contrat",
                ["", "CDI", "CDD", "Mission intérimaire"],
                key="cv_contrat"
            )
            cv_ville = st.text_input(
                "Ville souhaitée",
                placeholder="ex: Paris",
                key="cv_ville"
            )
            cv_top_k = st.slider(
                "Nombre de recommandations", 5, 20, 10, key="cv_topk"
            )

        st.divider()

        if st.button("Trouver mes offres", type="primary", key="cv_search"):
            cv_competences = [c.strip() for c in cv_comp_input.split(",") if c.strip()]
            profil_final = {
                "titre": cv_titre,
                "competences": cv_competences,
                "experience": cv_experience,
                "contrat": cv_contrat,
                "ville": cv_ville
            }
            with st.spinner("Recherche en cours..."):
                resultats = matcher_offres(profil_final, df, top_k=cv_top_k)
            if resultats.empty:
                st.error("Aucune offre trouvée. Essaie d'autres critères.")
            else:
                render_results(resultats, cv_competences, cv_titre)

    else:
        st.markdown("""
        <div class="empty-state"
             style="text-align:center;padding:48px 20px;border:1px dashed;border-radius:12px;">
          <i class="bi bi-file-earmark-arrow-up empty-icon"
             style="font-size:36px;display:block;margin-bottom:12px;"></i>
          <div class="empty-text"
               style="font-size:14px;font-weight:500;margin-bottom:4px;">
            Aucun CV importé
          </div>
          <div class="empty-sub" style="font-size:12px;">
            Formats supportés : PDF, DOCX 
          </div>
        </div>
        """, unsafe_allow_html=True)
