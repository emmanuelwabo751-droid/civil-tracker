import sqlite3
from datetime import date
import pandas as pd
import streamlit as st
import plotly.express as px

DB = "chantier.db"


def db():
    """Crée les tables nécessaires et insère des données de démonstration si la base est vide."""
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS projets(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT, client TEXT, localisation TEXT,
            budget REAL, debut TEXT, fin_prevue TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS taches(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            projet_id INTEGER, lot TEXT, tache TEXT, responsable TEXT,
            debut TEXT, fin_prevue TEXT, avancement REAL, statut TEXT,
            poids REAL, cout_prevu REAL, cout_reel REAL,
            FOREIGN KEY(projet_id) REFERENCES projets(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ouvriers(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT, metier TEXT, telephone TEXT,
            projet_id INTEGER, heures REAL DEFAULT 0,
            FOREIGN KEY(projet_id) REFERENCES projets(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS materiaux(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT, unite TEXT, quantite_prevue REAL,
            quantite_utilisee REAL, prix_unitaire REAL, projet_id INTEGER,
            FOREIGN KEY(projet_id) REFERENCES projets(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS depenses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, categorie TEXT, description TEXT,
            montant REAL, projet_id INTEGER,
            FOREIGN KEY(projet_id) REFERENCES projets(id)
        )
    """)

    # Insérer les données de test une seule fois, si aucun projet n'existe.
    nb_projets = conn.execute("SELECT COUNT(*) FROM projets").fetchone()[0]
    if nb_projets == 0:
        conn.execute("""
            INSERT INTO projets(nom, client, localisation, budget, debut, fin_prevue)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "Bâtiment R+2 – Douala",
            "Entreprise BTP Cameroun",
            "Douala, Bonamoussadi",
            85000000,
            "2026-09-01",
            "2027-08-31",
        ))
        pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        taches = [
            ("Gros œuvre", "Terrassement", "Jean Mbarga", "2026-09-01", "2026-09-10", 100, "Terminé", 1, 3000000, 2800000),
            ("Gros œuvre", "Fondations", "Paul Tchoumi", "2026-09-11", "2026-10-05", 100, "Terminé", 2, 12000000, 12500000),
            ("Gros œuvre", "Poteaux et poutres du RDC", "Alain Foka", "2026-10-01", "2026-11-15", 70, "En cours", 3, 15000000, 10000000),
            ("Gros œuvre", "Dalle du 1er étage", "David Essomba", "2026-10-10", "2026-11-30", 40, "En cours", 3, 10000000, 4500000),
            ("Maçonnerie", "Élévation des murs", "Marc Ekani", "2026-10-15", "2026-12-20", 25, "En cours", 2, 8000000, 2500000),
            ("Finition", "Enduit des murs", "Serge Mvondo", "2027-02-01", "2027-04-15", 0, "À faire", 1, 4000000, 0),
            ("Finition", "Peinture", "André Nguemo", "2027-05-01", "2027-07-15", 0, "À faire", 1, 3000000, 0),
        ]
        conn.executemany("""
            INSERT INTO taches(
                projet_id, lot, tache, responsable, debut, fin_prevue,
                avancement, statut, poids, cout_prevu, cout_reel
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [(pid, *t) for t in taches])

        ouvriers = [
            ("Jean Mbarga", "Conducteur d'engins", "690000101", pid, 120),
            ("Paul Tchoumi", "Maçon", "690000102", pid, 180),
            ("Alain Foka", "Coffreur", "690000103", pid, 160),
            ("David Essomba", "Ferrailleur", "690000104", pid, 140),
            ("Marc Ekani", "Maçon", "690000105", pid, 100),
            ("Serge Mvondo", "Manœuvre", "690000106", pid, 90),
        ]
        conn.executemany("""
            INSERT INTO ouvriers(nom, metier, telephone, projet_id, heures)
            VALUES (?, ?, ?, ?, ?)
        """, ouvriers)

        materiaux = [
            ("Ciment", "Sac", 2000, 650, 5500, pid),
            ("Sable", "m³", 150, 60, 18000, pid),
            ("Gravier", "m³", 120, 45, 25000, pid),
            ("Fer à béton", "Tonne", 25, 12, 650000, pid),
            ("Parpaings", "Unité", 8000, 2500, 450, pid),
            ("Bois de coffrage", "Pièce", 500, 180, 3000, pid),
        ]
        conn.executemany("""
            INSERT INTO materiaux(
                nom, unite, quantite_prevue, quantite_utilisee, prix_unitaire, projet_id
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, materiaux)

        depenses = [
            ("2026-09-02", "Matériaux", "Achat de ciment", 2000000, pid),
            ("2026-09-04", "Transport", "Transport du sable", 350000, pid),
            ("2026-09-06", "Main-d'œuvre", "Paiement des ouvriers", 750000, pid),
            ("2026-09-09", "Équipement", "Location d'une bétonnière", 200000, pid),
            ("2026-09-12", "Matériaux", "Achat de fer à béton", 3500000, pid),
            ("2026-09-15", "Sous-traitance", "Travaux de terrassement", 1200000, pid),
        ]
        conn.executemany("""
            INSERT INTO depenses(date, categorie, description, montant, projet_id)
            VALUES (?, ?, ?, ?, ?)
        """, depenses)

    conn.commit()
    return conn


st.set_page_config(page_title="CIVIL TRACKER", page_icon="🏗️", layout="wide")
conn = db()

st.markdown("""
<style>
.main {background:#f6f8fb}
h1, h2, h3 {font-weight:700}
[data-testid="stMetric"] {
    background: white; padding: 14px; border-radius: 12px;
    border: 1px solid #e6e9ef;
}
</style>
""", unsafe_allow_html=True)

st.title("🏗️ CIVIL TRACKER")
st.caption("Gestion, analyse et suivi de l'avancement des travaux d'un chantier")
st.info("Des données fictives sont préchargées pour tester l'application. Elles sont enregistrées dans chantier.db.")

projects = pd.read_sql_query("SELECT * FROM projets ORDER BY id DESC", conn)

menu = st.sidebar.radio("MENU", [
    "Tableau de bord", "Projets", "Travaux / Avancement",
    "Ouvriers", "Matériaux", "Dépenses", "Analyse", "Données"
])


def project_name(project_id):
    row = projects.loc[projects["id"] == project_id, "nom"]
    return row.iloc[0] if not row.empty else f"Projet {project_id}"


def project_selector(key=None):
    return st.selectbox(
        "Projet",
        projects["id"].tolist(),
        key=key,
        format_func=project_name
    )


if menu == "Tableau de bord":
    if projects.empty:
        st.info("Commencez par créer un projet dans « Projets ».")
    else:
        pid = project_selector("dashboard_project")
        p = projects[projects.id == pid].iloc[0]
        tasks = pd.read_sql_query("SELECT * FROM taches WHERE projet_id=?", conn, params=(pid,))
        expenses = pd.read_sql_query("SELECT * FROM depenses WHERE projet_id=?", conn, params=(pid,))
        workers = pd.read_sql_query("SELECT * FROM ouvriers WHERE projet_id=?", conn, params=(pid,))
        materials = pd.read_sql_query("SELECT * FROM materiaux WHERE projet_id=?", conn, params=(pid,))

        total_weight = tasks["poids"].sum() if not tasks.empty else 0
        progress = (tasks["avancement"] * tasks["poids"]).sum() / total_weight if total_weight > 0 else 0
        spent = expenses["montant"].sum() if not expenses.empty else 0
        budget = float(p["budget"] or 0)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Avancement pondéré", f"{progress:.1f}%")
        c2.metric("Budget", f"{budget:,.0f} FCFA")
        c3.metric("Dépenses enregistrées", f"{spent:,.0f} FCFA")
        c4.metric("Budget restant", f"{budget-spent:,.0f} FCFA")
        st.progress(min(max(progress / 100, 0), 1))

        c5, c6, c7 = st.columns(3)
        c5.metric("Nombre de tâches", len(tasks))
        c6.metric("Ouvriers enregistrés", len(workers))
        c7.metric("Matériaux suivis", len(materials))

        left, right = st.columns(2)
        with left:
            if not tasks.empty:
                fig = px.bar(tasks, x="tache", y="avancement", color="lot",
                             title="Avancement par tâche")
                fig.update_yaxes(range=[0, 100], title="%")
                st.plotly_chart(fig, use_container_width=True)
        with right:
            if not tasks.empty:
                status = tasks["statut"].value_counts().reset_index()
                status.columns = ["Statut", "Nombre"]
                st.plotly_chart(px.pie(status, names="Statut", values="Nombre",
                                       title="État des travaux"), use_container_width=True)
        if not expenses.empty:
            e = expenses.groupby("date", as_index=False)["montant"].sum()
            st.plotly_chart(px.line(e, x="date", y="montant", markers=True,
                                    title="Évolution des dépenses"), use_container_width=True)


elif menu == "Projets":
    st.header("Gestion des projets")
    with st.form("new_project"):
        a, b = st.columns(2)
        nom = a.text_input("Nom du chantier *")
        client = b.text_input("Client / maître d'ouvrage")
        loc = a.text_input("Localisation")
        budget = b.number_input("Budget prévisionnel (FCFA)", min_value=0.0, step=100000.0)
        debut = a.date_input("Date de début", value=date.today())
        fin = b.date_input("Fin prévue", value=date.today())
        if st.form_submit_button("Créer le projet"):
            if not nom.strip():
                st.error("Le nom du chantier est obligatoire.")
            elif fin < debut:
                st.error("La date de fin doit être postérieure ou égale à la date de début.")
            else:
                conn.execute("""
                    INSERT INTO projets(nom, client, localisation, budget, debut, fin_prevue)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (nom.strip(), client, loc, budget, str(debut), str(fin)))
                conn.commit()
                st.success("Projet créé.")
                st.rerun()
    st.dataframe(pd.read_sql_query("SELECT * FROM projets ORDER BY id DESC", conn),
                 use_container_width=True, hide_index=True)


elif menu == "Travaux / Avancement":
    st.header("Travaux et avancement")
    if projects.empty:
        st.warning("Créez d'abord un projet.")
    else:
        pid = project_selector("task_project")
        with st.form("task"):
            a, b, c = st.columns(3)
            lot = a.text_input("Lot (gros œuvre, finition...)")
            tache = b.text_input("Tâche *")
            resp = c.text_input("Responsable")
            d1 = a.date_input("Début", value=date.today())
            d2 = b.date_input("Fin prévue", value=date.today())
            av = c.slider("Avancement (%)", 0, 100, 0)
            statut = a.selectbox("Statut", ["À faire", "En cours", "Bloqué", "Terminé"])
            poids = b.number_input("Poids de la tâche", min_value=0.1, value=1.0)
            cp = c.number_input("Coût prévu (FCFA)", min_value=0.0, step=10000.0)
            cr = a.number_input("Coût réel (FCFA)", min_value=0.0, step=10000.0)
            if st.form_submit_button("Enregistrer la tâche"):
                if not tache.strip():
                    st.error("Le nom de la tâche est obligatoire.")
                elif d2 < d1:
                    st.error("La fin prévue ne peut pas précéder le début.")
                else:
                    # Garder le statut cohérent avec le pourcentage d'avancement.
                    if av == 100:
                        statut = "Terminé"
                    elif av > 0 and statut == "À faire":
                        statut = "En cours"
                    conn.execute("""
                        INSERT INTO taches(
                            projet_id, lot, tache, responsable, debut, fin_prevue,
                            avancement, statut, poids, cout_prevu, cout_reel
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (pid, lot, tache.strip(), resp, str(d1), str(d2),
                          av, statut, poids, cp, cr))
                    conn.commit()
                    st.success("Tâche enregistrée.")
                    st.rerun()
        tasks = pd.read_sql_query(
            "SELECT * FROM taches WHERE projet_id=? ORDER BY id DESC", conn, params=(pid,)
        )
        st.dataframe(tasks, use_container_width=True, hide_index=True)


elif menu == "Ouvriers":
    st.header("Gestion des ouvriers")
    if projects.empty:
        st.warning("Créez d'abord un projet.")
    else:
        pid = project_selector("worker_project")
        with st.form("worker"):
            a, b = st.columns(2)
            nom = a.text_input("Nom *")
            metier = b.text_input("Métier")
            tel = a.text_input("Téléphone")
            heures = b.number_input("Heures travaillées", min_value=0.0, max_value=10000.0, value=0.0)
            if st.form_submit_button("Ajouter l'ouvrier"):
                if not nom.strip():
                    st.error("Le nom de l'ouvrier est obligatoire.")
                else:
                    conn.execute("""
                        INSERT INTO ouvriers(nom, metier, telephone, projet_id, heures)
                        VALUES (?, ?, ?, ?, ?)
                    """, (nom.strip(), metier, tel, pid, heures))
                    conn.commit()
                    st.success("Ouvrier ajouté.")
                    st.rerun()
        st.dataframe(pd.read_sql_query(
            "SELECT * FROM ouvriers WHERE projet_id=? ORDER BY id DESC", conn, params=(pid,)
        ), use_container_width=True, hide_index=True)


elif menu == "Matériaux":
    st.header("Suivi des matériaux")
    if projects.empty:
        st.warning("Créez d'abord un projet.")
    else:
        pid = project_selector("material_project")
        with st.form("material"):
            a, b, c = st.columns(3)
            nom = a.text_input("Matériau *")
            unite = b.text_input("Unité (kg, m³, sac...)")
            qp = c.number_input("Quantité prévue", min_value=0.0)
            qu = a.number_input("Quantité utilisée", min_value=0.0)
            pu = b.number_input("Prix unitaire (FCFA)", min_value=0.0)
            if st.form_submit_button("Ajouter le matériau"):
                if not nom.strip():
                    st.error("Le nom du matériau est obligatoire.")
                elif qp > 0 and qu > qp:
                    st.error("La quantité utilisée ne peut pas dépasser la quantité prévue.")
                else:
                    conn.execute("""
                        INSERT INTO materiaux(
                            nom, unite, quantite_prevue, quantite_utilisee, prix_unitaire, projet_id
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (nom.strip(), unite, qp, qu, pu, pid))
                    conn.commit()
                    st.success("Matériau enregistré.")
                    st.rerun()
        m = pd.read_sql_query("SELECT * FROM materiaux WHERE projet_id=?", conn, params=(pid,))
        if not m.empty:
            m["Valeur utilisée (FCFA)"] = m["quantite_utilisee"] * m["prix_unitaire"]
            st.metric("Valeur des matériaux utilisés", f"{m['Valeur utilisée (FCFA)'].sum():,.0f} FCFA")
        st.dataframe(m, use_container_width=True, hide_index=True)


elif menu == "Dépenses":
    st.header("Dépenses du chantier")
    if projects.empty:
        st.warning("Créez d'abord un projet.")
    else:
        pid = project_selector("expense_project")
        with st.form("expense"):
            d = st.date_input("Date", value=date.today())
            cat = st.selectbox("Catégorie", [
                "Matériaux", "Main-d'œuvre", "Transport", "Équipement", "Sous-traitance", "Autre"
            ])
            desc = st.text_input("Description")
            amount = st.number_input("Montant (FCFA)", min_value=0.0, step=1000.0)
            if st.form_submit_button("Enregistrer la dépense"):
                if not desc.strip():
                    st.error("La description est obligatoire.")
                else:
                    conn.execute("""
                        INSERT INTO depenses(date, categorie, description, montant, projet_id)
                        VALUES (?, ?, ?, ?, ?)
                    """, (str(d), cat, desc.strip(), amount, pid))
                    conn.commit()
                    st.success("Dépense enregistrée.")
                    st.rerun()
        e = pd.read_sql_query(
            "SELECT * FROM depenses WHERE projet_id=? ORDER BY date DESC", conn, params=(pid,)
        )
        st.dataframe(e, use_container_width=True, hide_index=True)
        if not e.empty:
            st.metric("Total des dépenses", f"{e.montant.sum():,.0f} FCFA")


elif menu == "Analyse":
    st.header("Analyse du chantier")
    if projects.empty:
        st.warning("Créez d'abord un projet.")
    else:
        pid = project_selector("analysis_project")
        tasks = pd.read_sql_query("SELECT * FROM taches WHERE projet_id=?", conn, params=(pid,))
        if tasks.empty:
            st.info("Ajoutez des tâches pour obtenir l'analyse.")
        else:
            total_weight = tasks["poids"].sum()
            progress = (tasks["avancement"] * tasks["poids"]).sum() / total_weight if total_weight > 0 else 0
            planned = tasks["cout_prevu"].sum()
            actual = tasks["cout_reel"].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Avancement pondéré", f"{progress:.2f}%")
            c2.metric("Coût prévu", f"{planned:,.0f} FCFA")
            c3.metric("Coût réel", f"{actual:,.0f} FCFA")
            tasks["Écart coût"] = tasks["cout_reel"] - tasks["cout_prevu"]
            chart_data = tasks.melt(
                id_vars=["tache"], value_vars=["cout_prevu", "cout_reel"],
                var_name="Type de coût", value_name="Montant (FCFA)"
            )
            st.plotly_chart(px.bar(
                chart_data, x="tache", y="Montant (FCFA)", color="Type de coût",
                barmode="group", title="Coût prévu comparé au coût réel"
            ), use_container_width=True)
            st.dataframe(tasks[[
                "lot", "tache", "avancement", "statut",
                "cout_prevu", "cout_reel", "Écart coût"
            ]], use_container_width=True, hide_index=True)


elif menu == "Données":
    st.header("Export des données")
    tables = ["projets", "taches", "ouvriers", "materiaux", "depenses"]
    for table in tables:
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        st.download_button(
            f"Télécharger {table}.csv",
            df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{table}.csv",
            mime="text/csv",
            key=f"download_{table}"
        )

st.sidebar.caption("CIVIL TRACKER · Version de travail")
conn.close()
