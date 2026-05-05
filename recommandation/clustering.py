# recommandation/clustering.py
import numpy as np
import hdbscan
from utils.nlp_config import load_nlp_config

def run_job_clustering(embeddings: np.ndarray) -> np.ndarray:
    """
    Applique HDBSCAN sur les embeddings 384D.
    Retourne un tableau de labels: 0, 1, 2... (clusters) et -1 (bruit).
    """
    cfg = load_nlp_config()["clustering_config"]
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=cfg["min_cluster_size"],
        min_samples=cfg["min_samples"],
        metric=cfg["metric"],
        cluster_selection_method=cfg["cluster_selection_method"]
    )
    return clusterer.fit_predict(embeddings)

def map_clusters_to_categories(cluster_labels: np.ndarray, categories: dict) -> dict:
    """Mappe les IDs de clusters vers les noms de catégories métier (optionnel, pour BI)."""
    # Exemple d'usage: Hiba pourra appeler ça après vectorizer.py
    unique_labels = set(cluster_labels[cluster_labels != -1])
    mapping = {}
    for label in unique_labels:
        mask = cluster_labels == label
        # Ici on pourrait extraire le mot-clé dominant du cluster
        mapping[int(label)] = f"Cluster_{label}"
    return mapping