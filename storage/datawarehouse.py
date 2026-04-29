import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from sqlalchemy import text
from storage.database import get_engine

engine = get_engine()

def create_dwh_schema():
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS fact_offres CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS dim_ville CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS dim_contrat CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS dim_source CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS dim_date CASCADE"))

        conn.execute(text("""
            CREATE TABLE dim_ville (
                id_ville SERIAL PRIMARY KEY,
                ville VARCHAR(255) UNIQUE,
                code_postal VARCHAR(20)
            )
        """))
        conn.execute(text("""
            CREATE TABLE dim_contrat (
                id_contrat SERIAL PRIMARY KEY,
                type_contrat VARCHAR(100) UNIQUE
            )
        """))
        conn.execute(text("""
            CREATE TABLE dim_source (
                id_source SERIAL PRIMARY KEY,
                nom_source VARCHAR(100) UNIQUE
            )
        """))
        conn.execute(text("""
            CREATE TABLE dim_date (
                id_date SERIAL PRIMARY KEY,
                date_publication DATE UNIQUE,
                jour INT, mois INT, annee INT,
                trimestre INT, semaine INT
            )
        """))
        conn.execute(text("""
            CREATE TABLE fact_offres (
                id_offre VARCHAR PRIMARY KEY,
                id_ville INT REFERENCES dim_ville(id_ville),
                id_contrat INT REFERENCES dim_contrat(id_contrat),
                id_source INT REFERENCES dim_source(id_source),
                id_date INT REFERENCES dim_date(id_date),
                titre VARCHAR(500),
                entreprise VARCHAR(255),
                salaire VARCHAR(255),
                competences TEXT,
                description TEXT
            )
        """))
    print("Schema DWH créé.")

def populate_dwh():
    df = pd.read_sql("SELECT * FROM offres_emploi", engine)
    print(f"Source: {len(df)} offres")

    with engine.begin() as conn:
        # dim_ville
        villes = df[["ville", "code_postal"]].drop_duplicates().fillna("")
        for _, row in villes.iterrows():
            conn.execute(text("""
                INSERT INTO dim_ville (ville, code_postal)
                VALUES (:ville, :code_postal)
                ON CONFLICT (ville) DO NOTHING
            """), {"ville": row["ville"], "code_postal": row["code_postal"]})

        # dim_contrat
        for c in df["contrat"].dropna().unique():
            conn.execute(text("""
                INSERT INTO dim_contrat (type_contrat) VALUES (:c)
                ON CONFLICT (type_contrat) DO NOTHING
            """), {"c": str(c)})

        # dim_source
        for s in df["source"].dropna().unique():
            conn.execute(text("""
                INSERT INTO dim_source (nom_source) VALUES (:s)
                ON CONFLICT (nom_source) DO NOTHING
            """), {"s": str(s)})

        # dim_date
        dates = df["date_publication"].dropna()
        dates = dates[dates.str.match(r"\d{4}-\d{2}-\d{2}", na=False)].unique()
        for d in dates:
            try:
                dt = pd.to_datetime(d)
                conn.execute(text("""
                    INSERT INTO dim_date (date_publication, jour, mois, annee, trimestre, semaine)
                    VALUES (:date, :jour, :mois, :annee, :trim, :sem)
                    ON CONFLICT (date_publication) DO NOTHING
                """), {
                    "date": dt.date(), "jour": dt.day, "mois": dt.month,
                    "annee": dt.year, "trim": (dt.month - 1) // 3 + 1,
                    "sem": dt.isocalendar()[1]
                })
            except Exception:
                pass

        print("Dimensions populated.")

        # Load maps
        ville_map = {r.ville: r.id_ville for r in conn.execute(text("SELECT id_ville, ville FROM dim_ville"))}
        contrat_map = {r.type_contrat: r.id_contrat for r in conn.execute(text("SELECT id_contrat, type_contrat FROM dim_contrat"))}
        source_map = {r.nom_source: r.id_source for r in conn.execute(text("SELECT id_source, nom_source FROM dim_source"))}
        date_map = {str(r.date_publication): r.id_date for r in conn.execute(text("SELECT id_date, date_publication FROM dim_date"))}

        inserted = 0
        for _, row in df.iterrows():
            try:
                conn.execute(text("""
                    INSERT INTO fact_offres
                        (id_offre, id_ville, id_contrat, id_source, id_date,
                         titre, entreprise, salaire, competences, description)
                    VALUES
                        (:id, :ville, :contrat, :source, :date,
                         :titre, :entreprise, :salaire, :competences, :description)
                    ON CONFLICT DO NOTHING
                """), {
                    "id": row["id"],
                    "ville": ville_map.get(row.get("ville")),
                    "contrat": contrat_map.get(row.get("contrat")),
                    "source": source_map.get(row.get("source")),
                    "date": date_map.get(str(row.get("date_publication", ""))[:10]),
                    "titre": row.get("titre"),
                    "entreprise": row.get("entreprise"),
                    "salaire": row.get("salaire"),
                    "competences": row.get("competences"),
                    "description": row.get("description"),
                })
                inserted += 1
            except Exception as e:
                print(f"Error: {e}")
                pass

        print(f"fact_offres: {inserted} lignes insérées.")
    print("Data Warehouse peuplé avec succès.")

if __name__ == "__main__":
    create_dwh_schema()
    populate_dwh()
