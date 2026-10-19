import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ------------------------------------------------------------
# CIVIL TRACKER - Gestion et suivi de chantiers
# Les montants sont exprimés en FCFA. Les données de démonstration
# sont ajoutées projet par projet, sans supprimer les données existantes.
# ------------------------------------------------------------

DB_PATH = Path(__file__).with_name("chantier.db")

st.set_page_config(
    page_title="CIVIL TRACKER",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.stApp { background: #f5f7fb; }
h1, h2, h3 { font-weight: 750; }
[data-testid="stMetric"] {
    background: white; padding: 14px; border-radius: 12px;
    border: 1px solid #e4e8f0;
}
div[data-testid="stDataFrame"] { background: white; }
</style>
""", unsafe_allow_html=True)


def connect_db():
    """Crée les tables de l'application et active les clés étrangères."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL, client TEXT, localisation TEXT,
            budget REAL NOT NULL DEFAULT 0, debut TEXT, fin_prevue TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS taches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            projet_id INTEGER NOT NULL, lot TEXT, tache TEXT NOT NULL,
            responsable TEXT, debut TEXT, fin_prevue TEXT,
            avancement REAL NOT NULL DEFAULT 0,
            statut TEXT NOT NULL DEFAULT 'À faire',
            poids REAL NOT NULL DEFAULT 1,
            cout_prevu REAL NOT NULL DEFAULT 0, cout_reel REAL NOT NULL DEFAULT 0,
            FOREIGN KEY(projet_id) REFERENCES projets(id) ON DELETE CASCADE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ouvriers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL, metier TEXT, telephone TEXT,
            projet_id INTEGER NOT NULL, heures REAL NOT NULL DEFAULT 0,
            FOREIGN KEY(projet_id) REFERENCES projets(id) ON DELETE CASCADE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS materiaux (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL, unite TEXT,
            quantite_prevue REAL NOT NULL DEFAULT 0,
            quantite_utilisee REAL NOT NULL DEFAULT 0,
            prix_unitaire REAL NOT NULL DEFAULT 0,
            projet_id INTEGER NOT NULL,
            FOREIGN KEY(projet_id) REFERENCES projets(id) ON DELETE CASCADE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS depenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, categorie TEXT, description TEXT,
            montant REAL NOT NULL DEFAULT 0,
            projet_id INTEGER NOT NULL,
            FOREIGN KEY(projet_id) REFERENCES projets(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    return conn


def seed_demo_data(conn):
    """Insère chaque jeu de démonstration une seule fois, même si la base existe déjà."""
    demos = [
        {
            "nom": "Construction d'une villa R+1",
            "client": "M. Nguema", "localisation": "Douala - Bonamoussadi",
            "budget": 45_000_000, "debut": "2026-01-15", "fin": "2026-12-15",
            "tasks": [
                ("Installation", "Installation du chantier", "Jean Mbarga", "2026-01-15", "2026-01-30", 100, "Terminé", 1, 1_500_000, 1_450_000),
                ("Fondations", "Fouilles et semelles", "Paul Tchinda", "2026-02-01", "2026-03-15", 100, "Terminé", 3, 6_500_000, 6_800_000),
                ("Gros œuvre", "Élévation des murs", "André Essomba", "2026-03-16", "2026-07-30", 55, "En cours", 4, 12_000_000, 7_200_000),
                ("Charpente", "Pose de la charpente", "François Ewane", "2026-08-01", "2026-09-15", 20, "En cours", 2, 4_500_000, 1_000_000),
                ("Finition", "Électricité et plomberie", "Serge Mvondo", "2026-09-16", "2026-11-15", 0, "À faire", 2, 3_800_000, 0),
            ],
            "workers": [
                ("Jean Mbarga", "Chef de chantier", "690000101", 320),
                ("Paul Tchinda", "Maçon", "690000102", 280),
                ("François Ewane", "Ferrailleur", "690000103", 210),
                ("André Essomba", "Maçon", "690000104", 240),
                ("Serge Mvondo", "Électricien", "690000105", 120),
            ],
            "materials": [
                ("Ciment CPJ 42.5", "sac", 600, 420, 5200),
                ("Sable", "m³", 80, 55, 18000),
                ("Fer à béton 12 mm", "barre", 250, 180, 4500),
                ("Gravier", "m³", 35, 20, 25000),
                ("Bois de coffrage", "pièce", 120, 75, 3000),
            ],
            "expenses": [
                ("2026-02-02", "Matériaux", "Achat ciment et sable", 2_450_000),
                ("2026-03-10", "Main-d'œuvre", "Paiement équipe maçonnerie", 850_000),
                ("2026-05-12", "Transport", "Transport des fers", 320_000),
                ("2026-07-08", "Équipement", "Location bétonnière", 275_000),
            ],
        },
        {
            "nom": "Réhabilitation d'un bâtiment",
            "client": "Commune de Yaoundé", "localisation": "Yaoundé - Mvan",
            "budget": 18_000_000, "debut": "2026-03-01", "fin": "2026-12-30",
            "tasks": [
                ("Démolition", "Dépose des éléments dégradés", "Michel Foka", "2026-03-01", "2026-03-20", 100, "Terminé", 2, 2_200_000, 2_100_000),
                ("Maçonnerie", "Réparation des murs", "Pierre Atangana", "2026-03-21", "2026-06-15", 80, "En cours", 3, 5_500_000, 4_900_000),
                ("Finition", "Peinture et revêtement", "David Mballa", "2026-06-16", "2026-08-30", 40, "En cours", 2, 3_800_000, 1_200_000),
                ("Étanchéité", "Réfection de l'étanchéité", "Lucie Nono", "2026-09-01", "2026-11-15", 10, "En cours", 2, 2_400_000, 500_000),
            ],
            "workers": [
                ("Michel Foka", "Chef d'équipe", "690000201", 260),
                ("Pierre Atangana", "Maçon", "690000202", 240),
                ("David Mballa", "Peintre", "690000203", 120),
                ("Lucie Nono", "Étancheuse", "690000204", 90),
            ],
            "materials": [
                ("Ciment", "sac", 250, 190, 5200),
                ("Peinture acrylique", "seau", 45, 18, 28000),
                ("Carreaux", "m²", 160, 90, 8500),
                ("Mortier de réparation", "sac", 80, 42, 7500),
            ],
            "expenses": [
                ("2026-03-05", "Équipement", "Location matériel de démolition", 450_000),
                ("2026-04-18", "Matériaux", "Achat ciment et mortier", 1_250_000),
                ("2026-07-02", "Main-d'œuvre", "Paiement ouvriers", 600_000),
                ("2026-09-12", "Transport", "Transport des matériaux", 180_000),
            ],
        },
        {
            "nom": "Construction d'un immeuble R+3",
            "client": "SCI Les Bâtisseurs", "localisation": "Bafoussam - Centre",
            "budget": 82_000_000, "debut": "2026-05-01", "fin": "2027-06-30",
            "tasks": [
                ("Études", "Implantation et terrassement", "Serge Kamga", "2026-05-01", "2026-06-15", 100, "Terminé", 2, 5_000_000, 4_800_000),
                ("Fondations", "Semelles et longrines", "Eric Talla", "2026-06-16", "2026-09-15", 35, "En cours", 4, 14_000_000, 5_200_000),
                ("Structure", "Poteaux et dalles", "Alain Njoya", "2026-09-16", "2027-02-28", 0, "À faire", 5, 24_000_000, 0),
                ("Maçonnerie", "Élévation des murs", "Brice Fotso", "2027-01-15", "2027-04-30", 0, "À faire", 3, 12_000_000, 0),
                ("Finition", "Revêtement et peinture", "Carine Tchoua", "2027-04-01", "2027-06-15", 0, "À faire", 2, 8_000_000, 0),
            ],
            "workers": [
                ("Serge Kamga", "Conducteur de travaux", "690000301", 180),
                ("Eric Talla", "Coffreur", "690000302", 150),
                ("Alain Njoya", "Ferrailleur", "690000303", 90),
                ("Brice Fotso", "Maçon", "690000304", 70),
                ("Carine Tchoua", "Peintre", "690000305", 45),
            ],
            "materials": [
                ("Ciment", "sac", 900, 300, 5200),
                ("Fer à béton 12 mm", "barre", 500, 175, 4500),
                ("Gravier", "m³", 120, 45, 25000),
                ("Sable", "m³", 220, 65, 18000),
                ("Parpaings", "unité", 12000, 0, 450),
            ],
            "expenses": [
                ("2026-05-08", "Équipement", "Location engin de terrassement", 900_000),
                ("2026-07-20", "Matériaux", "Achat ciment et fer", 2_750_000),
                ("2026-09-28", "Main-d'œuvre", "Paiement équipe fondations", 780_000),
                ("2026-10-10", "Transport", "Transport gravier et sable", 420_000),
            ],
        },
    ]

    for demo in demos:
        found = conn.execute("SELECT id FROM projets WHERE nom = ?", (demo["nom"],)).fetchone()
        if found:
            continue
        cur = conn.execute(
            "INSERT INTO projets(nom,client,localisation,budget,debut,fin_prevue) VALUES(?,?,?,?,?,?)",
            (demo["nom"], demo["client"], demo["localisation"], demo["budget"], demo["debut"], demo["fin"]),
        )
        pid = cur.lastrowid
        conn.executemany("""
            INSERT INTO taches(projet_id,lot,tache,responsable,debut,fin_prevue,avancement,statut,poids,cout_prevu,cout_reel)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """, [(pid, *t) for t in demo["tasks"]])
        conn.executemany("""
            INSERT INTO ouvriers(nom,metier,telephone,projet_id,heures) VALUES(?,?,?,?,?)
        """, [(n, m, tel, pid, h) for n, m, tel, h in demo["workers"]])
        conn.executemany("""
            INSERT INTO materiaux(nom,unite,quantite_prevue,quantite_utilisee,prix_unitaire,projet_id)
            VALUES(?,?,?,?,?,?)
        """, [(n, u, qp, qu, pu, pid) for n, u, qp, qu, pu in demo["materials"]])
        conn.executemany("""
            INSERT INTO depenses(date,categorie,description,montant,projet_id) VALUES(?,?,?,?,?)
        """, [(d, cat, desc, amount, pid) for d, cat, desc, amount in demo["expenses"]])
    conn.commit()


def money(value):
    return f"{float(value or 0):,.0f} FCFA".replace(",", " ")


def load_table(conn, table, project_id=None):
    allowed = {"projets", "taches", "ouvriers", "materiaux", "depenses"}
    if table not in allowed:
        raise ValueError("Table inconnue")
    if project_id is None or table == "projets":
        return pd.read_sql_query(f"SELECT * FROM {table} ORDER BY id DESC", conn)
    return pd.read_sql_query(
        f"SELECT * FROM {table} WHERE projet_id=? ORDER BY id DESC",
        conn, params=(int(project_id),)
    )


conn = connect_db()
seed_demo_data(conn)
projects = load_table(conn, "projets")

st.title("🏗️ CIVIL TRACKER")
st.caption("Gestion, analyse et suivi des travaux, des équipes, des matériaux et du budget.")
st.info("Les données de démonstration sont fictives. Elles sont stockées localement dans chantier.db.")

menu = st.sidebar.radio("MENU PRINCIPAL", [
    "Tableau de bord", "Projets", "Travaux / Avancement",
    "Ouvriers", "Matériaux", "Dépenses", "Analyse", "Données / Export"
])

if not projects.empty:
    project_options = projects["id"].tolist()
    project_labels = dict(zip(projects["id"], projects["nom"]))


def select_project(key):
    return st.selectbox(
        "Choisir le chantier",
        project_options,
        key=key,
        format_func=lambda pid: project_labels.get(pid, f"Projet {pid}")
    )


if menu == "Tableau de bord":
    if projects.empty:
        st.warning("Créez d'abord un projet.")
    else:
        pid = select_project("dashboard_project")
        p = projects.loc[projects.id == pid].iloc[0]
        tasks = load_table(conn, "taches", pid)
        expenses = load_table(conn, "depenses", pid)
        workers = load_table(conn, "ouvriers", pid)
        materials = load_table(conn, "materiaux", pid)
        weight_sum = tasks["poids"].sum() if not tasks.empty else 0
        progress = (tasks["avancement"] * tasks["poids"]).sum() / weight_sum if weight_sum else 0
        spent = expenses["montant"].sum() if not expenses.empty else 0
        budget = float(p["budget"] or 0)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Avancement pondéré", f"{progress:.1f}%")
        c2.metric("Budget du chantier", money(budget))
        c3.metric("Dépenses saisies", money(spent))
        c4.metric("Budget disponible", money(budget - spent), delta=f"{(spent / budget * 100):.1f}% consommé" if budget else None)
        st.progress(max(0.0, min(1.0, progress / 100)))
        a, b, c = st.columns(3)
        a.metric("Tâches", len(tasks))
        b.metric("Ouvriers", len(workers))
        c.metric("Matériaux suivis", len(materials))
        left, right = st.columns(2)
        with left:
            if not tasks.empty:
                fig = px.bar(tasks, x="tache", y="avancement", color="lot", title="Avancement par tâche")
                fig.update_yaxes(range=[0, 100], title="Avancement (%)")
                fig.update_layout(xaxis_title="", legend_title="Lot")
                st.plotly_chart(fig, use_container_width=True)
        with right:
            if not tasks.empty:
                status = tasks["statut"].value_counts().rename_axis("Statut").reset_index(name="Nombre")
                st.plotly_chart(px.pie(status, names="Statut", values="Nombre", title="Répartition des statuts"), use_container_width=True)
        if not expenses.empty:
            by_date = expenses.groupby("date", as_index=False)["montant"].sum().sort_values("date")
            st.plotly_chart(px.line(by_date, x="date", y="montant", markers=True, title="Dépenses par date"), use_container_width=True)

elif menu == "Projets":
    st.header("Gestion des projets")
    with st.form("new_project", clear_on_submit=True):
        a, b = st.columns(2)
        nom = a.text_input("Nom du chantier *")
        client = b.text_input("Client / maître d'ouvrage")
        loc = a.text_input("Localisation")
        budget = b.number_input("Budget prévisionnel (FCFA)", min_value=0.0, step=100_000.0)
        debut = a.date_input("Date de début", value=date.today())
        fin = b.date_input("Fin prévue", value=date.today())
        submitted = st.form_submit_button("Créer le projet")
        if submitted:
            if not nom.strip():
                st.error("Le nom du chantier est obligatoire.")
            elif fin < debut:
                st.error("La date de fin doit être postérieure ou égale à la date de début.")
            else:
                conn.execute(
                    "INSERT INTO projets(nom,client,localisation,budget,debut,fin_prevue) VALUES(?,?,?,?,?,?)",
                    (nom.strip(), client.strip(), loc.strip(), budget, str(debut), str(fin))
                )
                conn.commit()
                st.success("Projet créé.")
                st.rerun()
    st.subheader("Projets enregistrés")
    st.dataframe(load_table(conn, "projets"), use_container_width=True, hide_index=True)

elif menu == "Travaux / Avancement":
    st.header("Travaux et avancement")
    if projects.empty:
        st.warning("Créez d'abord un projet.")
    else:
        pid = select_project("task_project")
        with st.form("new_task", clear_on_submit=True):
            a, b, c = st.columns(3)
            lot = a.text_input("Lot (gros œuvre, finition...)")
            task_name = b.text_input("Nom de la tâche *")
            responsible = c.text_input("Responsable")
            start = a.date_input("Date de début", value=date.today())
            end = b.date_input("Fin prévue", value=date.today())
            progress = c.slider("Avancement (%)", 0, 100, 0)
            status = a.selectbox("Statut", ["À faire", "En cours", "Bloqué", "Terminé"])
            weight = b.number_input("Poids de la tâche", min_value=0.1, value=1.0, step=0.5)
            planned_cost = c.number_input("Coût prévu (FCFA)", min_value=0.0, step=10_000.0)
            actual_cost = a.number_input("Coût réel (FCFA)", min_value=0.0, step=10_000.0)
            submitted = st.form_submit_button("Enregistrer la tâche")
            if submitted:
                if not task_name.strip():
                    st.error("Le nom de la tâche est obligatoire.")
                elif end < start:
                    st.error("La fin prévue ne peut pas précéder le début.")
                else:
                    if progress == 100:
                        status = "Terminé"
                    elif progress > 0 and status == "À faire":
                        status = "En cours"
                    conn.execute("""
                        INSERT INTO taches(projet_id,lot,tache,responsable,debut,fin_prevue,avancement,statut,poids,cout_prevu,cout_reel)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?)
                    """, (pid, lot.strip(), task_name.strip(), responsible.strip(), str(start), str(end),
                          progress, status, weight, planned_cost, actual_cost))
                    conn.commit()
                    st.success("Tâche enregistrée.")
                    st.rerun()
        tasks = load_table(conn, "taches", pid)
        st.subheader("Liste des travaux")
        st.dataframe(tasks, use_container_width=True, hide_index=True)
        if not tasks.empty:
            st.download_button("Exporter les travaux en CSV", tasks.to_csv(index=False).encode("utf-8-sig"),
                               "travaux.csv", "text/csv")

elif menu == "Ouvriers":
    st.header("Gestion des ouvriers")
    if projects.empty:
        st.warning("Créez d'abord un projet.")
    else:
        pid = select_project("worker_project")
        with st.form("new_worker", clear_on_submit=True):
            a, b = st.columns(2)
            name = a.text_input("Nom complet *")
            trade = b.text_input("Métier")
            phone = a.text_input("Téléphone")
            hours = b.number_input("Heures travaillées", min_value=0.0, max_value=10000.0, value=0.0, step=1.0)
            if st.form_submit_button("Ajouter l'ouvrier"):
                if not name.strip():
                    st.error("Le nom de l'ouvrier est obligatoire.")
                else:
                    conn.execute("INSERT INTO ouvriers(nom,metier,telephone,projet_id,heures) VALUES(?,?,?,?,?)",
                                 (name.strip(), trade.strip(), phone.strip(), pid, hours))
                    conn.commit()
                    st.success("Ouvrier ajouté.")
                    st.rerun()
        workers = load_table(conn, "ouvriers", pid)
        if not workers.empty:
            st.metric("Total des heures déclarées", f"{workers['heures'].sum():,.0f} h")
        st.dataframe(workers, use_container_width=True, hide_index=True)

elif menu == "Matériaux":
    st.header("Suivi des matériaux")
    if projects.empty:
        st.warning("Créez d'abord un projet.")
    else:
        pid = select_project("material_project")
        with st.form("new_material", clear_on_submit=True):
            a, b, c = st.columns(3)
            name = a.text_input("Nom du matériau *")
            unit = b.text_input("Unité (sac, m³, kg, barre...)")
            planned_qty = c.number_input("Quantité prévue", min_value=0.0, step=1.0)
            used_qty = a.number_input("Quantité utilisée", min_value=0.0, step=1.0)
            unit_price = b.number_input("Prix unitaire (FCFA)", min_value=0.0, step=500.0)
            if st.form_submit_button("Ajouter le matériau"):
                if not name.strip():
                    st.error("Le nom du matériau est obligatoire.")
                elif used_qty > planned_qty:
                    st.error("La quantité utilisée ne peut pas dépasser la quantité prévue.")
                else:
                    conn.execute("""
                        INSERT INTO materiaux(nom,unite,quantite_prevue,quantite_utilisee,prix_unitaire,projet_id)
                        VALUES(?,?,?,?,?,?)
                    """, (name.strip(), unit.strip(), planned_qty, used_qty, unit_price, pid))
                    conn.commit()
                    st.success("Matériau enregistré.")
                    st.rerun()
        materials = load_table(conn, "materiaux", pid)
        if not materials.empty:
            materials["Reste à utiliser"] = materials["quantite_prevue"] - materials["quantite_utilisee"]
            materials["Valeur utilisée (FCFA)"] = materials["quantite_utilisee"] * materials["prix_unitaire"]
            c1, c2 = st.columns(2)
            c1.metric("Valeur des matériaux utilisés", money(materials["Valeur utilisée (FCFA)"].sum()))
            c2.metric("Références de matériaux", len(materials))
        st.dataframe(materials, use_container_width=True, hide_index=True)

elif menu == "Dépenses":
    st.header("Dépenses du chantier")
    if projects.empty:
        st.warning("Créez d'abord un projet.")
    else:
        pid = select_project("expense_project")
        with st.form("new_expense", clear_on_submit=True):
            d = st.date_input("Date de la dépense", value=date.today())
            category = st.selectbox("Catégorie", [
                "Matériaux", "Main-d'œuvre", "Transport", "Équipement", "Sous-traitance", "Démolition", "Autre"
            ])
            description = st.text_input("Description *")
            amount = st.number_input("Montant (FCFA)", min_value=0.0, step=1_000.0)
            if st.form_submit_button("Enregistrer la dépense"):
                if not description.strip():
                    st.error("La description est obligatoire.")
                elif amount <= 0:
                    st.error("Le montant doit être supérieur à zéro.")
                else:
                    conn.execute("INSERT INTO depenses(date,categorie,description,montant,projet_id) VALUES(?,?,?,?,?)",
                                 (str(d), category, description.strip(), amount, pid))
                    conn.commit()
                    st.success("Dépense enregistrée.")
                    st.rerun()
        expenses = load_table(conn, "depenses", pid)
        if not expenses.empty:
            st.metric("Total des dépenses enregistrées", money(expenses["montant"].sum()))
            cat = expenses.groupby("categorie", as_index=False)["montant"].sum()
            st.plotly_chart(px.pie(cat, names="categorie", values="montant", title="Dépenses par catégorie"),
                            use_container_width=True)
        st.dataframe(expenses, use_container_width=True, hide_index=True)

elif menu == "Analyse":
    st.header("Analyse financière et technique")
    if projects.empty:
        st.warning("Créez d'abord un projet.")
    else:
        pid = select_project("analysis_project")
        p = projects.loc[projects.id == pid].iloc[0]
        tasks = load_table(conn, "taches", pid)
        expenses = load_table(conn, "depenses", pid)
        budget = float(p["budget"] or 0)
        total_weight = tasks["poids"].sum() if not tasks.empty else 0
        progress = (tasks["avancement"] * tasks["poids"]).sum() / total_weight if total_weight else 0
        planned = tasks["cout_prevu"].sum() if not tasks.empty else 0
        actual = tasks["cout_reel"].sum() if not tasks.empty else 0
        spent = expenses["montant"].sum() if not expenses.empty else 0
        a, b, c, d = st.columns(4)
        a.metric("Avancement pondéré", f"{progress:.1f}%")
        b.metric("Coût prévu des tâches", money(planned))
        c.metric("Coût réel des tâches", money(actual))
        d.metric("Dépenses saisies", money(spent))
        st.caption("Les coûts réels des tâches et les dépenses enregistrées sont deux suivis distincts : ne les additionnez pas sans vérifier qu'ils ne couvrent pas les mêmes achats.")
        if budget:
            st.metric("Budget consommé selon les dépenses", f"{spent / budget * 100:.1f}%",
                      delta=money(budget - spent) + " disponibles")
        if not tasks.empty:
            tasks["Écart coût (réel - prévu)"] = tasks["cout_reel"] - tasks["cout_prevu"]
            costs = tasks.melt(id_vars=["tache"], value_vars=["cout_prevu", "cout_reel"],
                               var_name="Type de coût", value_name="Montant (FCFA)")
            costs["Type de coût"] = costs["Type de coût"].map({
                "cout_prevu": "Coût prévu", "cout_reel": "Coût réel"
            })
            st.plotly_chart(px.bar(costs, x="tache", y="Montant (FCFA)", color="Type de coût",
                                   barmode="group", title="Coût prévu comparé au coût réel"),
                            use_container_width=True)
            st.dataframe(tasks[["lot", "tache", "avancement", "statut", "cout_prevu",
                                "cout_reel", "Écart coût (réel - prévu)"]],
                         use_container_width=True, hide_index=True)
        if not expenses.empty:
            by_cat = expenses.groupby("categorie", as_index=False)["montant"].sum()
            st.plotly_chart(px.bar(by_cat, x="categorie", y="montant", title="Dépenses par catégorie"),
                            use_container_width=True)

elif menu == "Données / Export":
    st.header("Données enregistrées et export")
    table_labels = {
        "projets": "Projets", "taches": "Travaux / tâches",
        "ouvriers": "Ouvriers", "materiaux": "Matériaux", "depenses": "Dépenses"
    }
    for table, label in table_labels.items():
        df = load_table(conn, table)
        with st.expander(f"{label} — {len(df)} ligne(s)", expanded=(table == "projets")):
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button(
                f"Télécharger {table}.csv",
                df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"{table}.csv",
                mime="text/csv",
                key=f"download_{table}"
            )

st.sidebar.divider()
st.sidebar.caption("CIVIL TRACKER · Version améliorée")
st.sidebar.caption("Base locale : chantier.db")
conn.close()
