
import sqlite3
from datetime import date
import pandas as pd
import streamlit as st
#import plotly.express as px

DB = "chantier.db"

def db():
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS projets(
        id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, client TEXT,
        localisation TEXT, budget REAL, debut TEXT, fin_prevue TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS taches(
        id INTEGER PRIMARY KEY AUTOINCREMENT, projet_id INTEGER,
        lot TEXT, tache TEXT, responsable TEXT, debut TEXT, fin_prevue TEXT,
        avancement REAL, statut TEXT, poids REAL, cout_prevu REAL, cout_reel REAL,
        FOREIGN KEY(projet_id) REFERENCES projets(id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS ouvriers(
        id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, metier TEXT,
        telephone TEXT, projet_id INTEGER, heures REAL DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS materiaux(
        id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, unite TEXT,
        quantite_prevue REAL, quantite_utilisee REAL, prix_unitaire REAL,
        projet_id INTEGER)""")
    c.execute("""CREATE TABLE IF NOT EXISTS depenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, categorie TEXT,
        description TEXT, montant REAL, projet_id INTEGER)""")
    c.commit()
    return c

conn = db()
st.set_page_config(page_title="CIVIL TRACKER", page_icon="🏗️", layout="wide")

st.markdown("""
<style>
.main {background:#f6f8fb}
.kpi {padding:18px;border-radius:14px;background:white;border:1px solid #e6e9ef}
h1,h2,h3 {font-weight:700}
</style>
""", unsafe_allow_html=True)

st.title("🏗️ CIVIL TRACKER")
st.caption("Gestion, analyse et suivi de l'avancement des travaux d'un chantier")

projects = pd.read_sql_query("SELECT * FROM projets ORDER BY id DESC", conn)

menu = st.sidebar.radio("MENU", [
    "Tableau de bord","Projets","Travaux / Avancement",
    "Ouvriers","Matériaux","Dépenses","Analyse","Données"
])

if menu == "Tableau de bord":
    if projects.empty:
        st.info("Commencez par créer un projet dans « Projets ».")
    else:
        pid = st.sidebar.selectbox("Projet", projects["id"], format_func=lambda x: projects.loc[projects.id==x,"nom"].iloc[0])
        p = projects[projects.id==pid].iloc[0]
        tasks = pd.read_sql_query("SELECT * FROM taches WHERE projet_id=?", conn, params=(pid,))
        expenses = pd.read_sql_query("SELECT * FROM depenses WHERE projet_id=?", conn, params=(pid,))
        workers = pd.read_sql_query("SELECT * FROM ouvriers WHERE projet_id=?", conn, params=(pid,))
        materials = pd.read_sql_query("SELECT * FROM materiaux WHERE projet_id=?", conn, params=(pid,))
        progress = (tasks["avancement"]*tasks["poids"]).sum()/tasks["poids"].sum() if not tasks.empty and tasks["poids"].sum()>0 else 0
        planned = tasks["cout_prevu"].sum() if not tasks.empty else 0
        actual = tasks["cout_reel"].sum() if not tasks.empty else 0
        spent = expenses["montant"].sum() if not expenses.empty else 0
        budget = float(p["budget"] or 0)
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Avancement", f"{progress:.1f}%")
        c2.metric("Budget", f"{budget:,.0f}")
        c3.metric("Dépenses", f"{spent:,.0f}")
        c4.metric("Écart budget", f"{budget-spent:,.0f}")
        st.progress(min(max(progress/100,0),1))
        col1,col2 = st.columns(2)
        with col1:
            if not tasks.empty:
                fig=px.bar(tasks, x="tache", y="avancement", color="lot", title="Avancement par tâche")
                fig.update_yaxes(range=[0,100], title="%")
                st.plotly_chart(fig,use_container_width=True)
        with col2:
            if not tasks.empty:
                status=tasks["statut"].value_counts().reset_index()
                status.columns=["Statut","Nombre"]
                st.plotly_chart(px.pie(status,names="Statut",values="Nombre",title="État des travaux"),use_container_width=True)
        if not expenses.empty:
            e=expenses.groupby("date",as_index=False)["montant"].sum()
            st.plotly_chart(px.line(e,x="date",y="montant",markers=True,title="Évolution des dépenses"),use_container_width=True)

elif menu == "Projets":
    st.header("Gestion des projets")
    with st.form("new_project"):
        a,b=st.columns(2)
        nom=a.text_input("Nom du chantier *")
        client=b.text_input("Client / maître d'ouvrage")
        loc=a.text_input("Localisation")
        budget=b.number_input("Budget prévisionnel", min_value=0.0, step=100000.0)
        debut=a.date_input("Date de début", value=date.today())
        fin=b.date_input("Fin prévue", value=date.today())
        if st.form_submit_button("Créer le projet"):
            conn.execute("INSERT INTO projets(nom,client,localisation,budget,debut,fin_prevue) VALUES(?,?,?,?,?,?)",
                         (nom,client,loc,budget,str(debut),str(fin)))
            conn.commit(); st.success("Projet créé."); st.rerun()
    st.dataframe(projects, use_container_width=True)

elif menu == "Travaux / Avancement":
    st.header("Travaux et avancement")
    if projects.empty: st.warning("Créez d'abord un projet.")
    else:
        pid=st.selectbox("Projet",projects.id,format_func=lambda x: projects.loc[projects.id==x,"nom"].iloc[0])
        with st.form("task"):
            a,b,c=st.columns(3)
            lot=a.text_input("Lot (gros œuvre, finition...)")
            tache=b.text_input("Tâche")
            resp=c.text_input("Responsable")
            d1=a.date_input("Début",value=date.today())
            d2=b.date_input("Fin prévue",value=date.today())
            av=c.slider("Avancement (%)",0,100,0)
            statut=a.selectbox("Statut",["À faire","En cours","Bloqué","Terminé"])
            poids=b.number_input("Poids de la tâche",min_value=0.1,value=1.0)
            cp=c.number_input("Coût prévu",min_value=0.0,step=10000.0)
            cr=a.number_input("Coût réel",min_value=0.0,step=10000.0)
            if st.form_submit_button("Enregistrer la tâche"):
                conn.execute("""INSERT INTO taches(projet_id,lot,tache,responsable,debut,fin_prevue,avancement,statut,poids,cout_prevu,cout_reel)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""",(pid,lot,tache,resp,str(d1),str(d2),av,statut,poids,cp,cr))
                conn.commit(); st.success("Tâche enregistrée."); st.rerun()
        tasks=pd.read_sql_query("SELECT * FROM taches WHERE projet_id=? ORDER BY id DESC",conn,params=(pid,))
        st.dataframe(tasks,use_container_width=True)

elif menu == "Ouvriers":
    st.header("Gestion des ouvriers")
    if projects.empty: st.warning("Créez d'abord un projet.")
    else:
        pid=st.selectbox("Projet",projects.id,key="wp",format_func=lambda x: projects.loc[projects.id==x,"nom"].iloc[0])
        with st.form("worker"):
            a,b=st.columns(2)
            nom=a.text_input("Nom")
            metier=b.text_input("Métier")
            tel=a.text_input("Téléphone")
            heures=b.number_input("Heures travaillées",0.0,10000.0,0.0)
            if st.form_submit_button("Ajouter"):
                conn.execute("INSERT INTO ouvriers(nom,metier,telephone,projet_id,heures) VALUES(?,?,?,?,?)",(nom,metier,tel,pid,heures))
                conn.commit(); st.success("Ouvrier ajouté."); st.rerun()
        st.dataframe(pd.read_sql_query("SELECT * FROM ouvriers WHERE projet_id=?",conn,params=(pid,)),use_container_width=True)

elif menu == "Matériaux":
    st.header("Suivi des matériaux")
    if projects.empty: st.warning("Créez d'abord un projet.")
    else:
        pid=st.selectbox("Projet",projects.id,key="mp",format_func=lambda x: projects.loc[projects.id==x,"nom"].iloc[0])
        with st.form("material"):
            a,b,c=st.columns(3)
            nom=a.text_input("Matériau")
            unite=b.text_input("Unité (kg, m³, sac...)")
            qp=c.number_input("Quantité prévue",0.0)
            qu=a.number_input("Quantité utilisée",0.0)
            pu=b.number_input("Prix unitaire",0.0)
            if st.form_submit_button("Ajouter"):
                conn.execute("INSERT INTO materiaux(nom,unite,quantite_prevue,quantite_utilisee,prix_unitaire,projet_id) VALUES(?,?,?,?,?,?)",(nom,unite,qp,qu,pu,pid))
                conn.commit(); st.success("Matériau enregistré."); st.rerun()
        m=pd.read_sql_query("SELECT * FROM materiaux WHERE projet_id=?",conn,params=(pid,))
        if not m.empty: m["Valeur utilisée"]=m.quantite_utilisee*m.prix_unitaire
        st.dataframe(m,use_container_width=True)

elif menu == "Dépenses":
    st.header("Dépenses du chantier")
    if projects.empty: st.warning("Créez d'abord un projet.")
    else:
        pid=st.selectbox("Projet",projects.id,key="dp",format_func=lambda x: projects.loc[projects.id==x,"nom"].iloc[0])
        with st.form("expense"):
            d=st.date_input("Date",value=date.today())
            cat=st.selectbox("Catégorie",["Matériaux","Main-d'œuvre","Transport","Équipement","Sous-traitance","Autre"])
            desc=st.text_input("Description")
            amount=st.number_input("Montant",0.0,step=1000.0)
            if st.form_submit_button("Enregistrer"):
                conn.execute("INSERT INTO depenses(date,categorie,description,montant,projet_id) VALUES(?,?,?,?,?)",(str(d),cat,desc,amount,pid))
                conn.commit(); st.success("Dépense enregistrée."); st.rerun()
        e=pd.read_sql_query("SELECT * FROM depenses WHERE projet_id=? ORDER BY date DESC",conn,params=(pid,))
        st.dataframe(e,use_container_width=True)
        if not e.empty:
            st.metric("Total dépenses",f"{e.montant.sum():,.0f}")

elif menu == "Analyse":
    st.header("Analyse du chantier")
    if projects.empty: st.warning("Créez d'abord un projet.")
    else:
        pid=st.selectbox("Projet",projects.id,key="ap",format_func=lambda x: projects.loc[projects.id==x,"nom"].iloc[0])
        tasks=pd.read_sql_query("SELECT * FROM taches WHERE projet_id=?",conn,params=(pid,))
        if tasks.empty: st.info("Ajoutez des tâches pour obtenir l'analyse.")
        else:
            progress=(tasks.avancement*tasks.poids).sum()/tasks.poids.sum()
            planned=tasks.cout_prevu.sum(); actual=tasks.cout_reel.sum()
            c1,c2,c3=st.columns(3)
            c1.metric("Avancement pondéré",f"{progress:.2f}%")
            c2.metric("Coût prévu",f"{planned:,.0f}")
            c3.metric("Coût réel",f"{actual:,.0f}")
            tasks["Écart coût"]=tasks.cout_reel-tasks.cout_prevu
            st.plotly_chart(px.bar(tasks,x="tache",y=["cout_prevu","cout_reel"],barmode="group",title="Prévision vs réel"),use_container_width=True)
            st.dataframe(tasks[["lot","tache","avancement","statut","cout_prevu","cout_reel","Écart coût"]],use_container_width=True)

elif menu == "Données":
    st.header("Export des données")
    tables=["projets","taches","ouvriers","materiaux","depenses"]
    for table in tables:
        df=pd.read_sql_query(f"SELECT * FROM {table}",conn)
        st.download_button(f"Télécharger {table}.csv",df.to_csv(index=False).encode("utf-8"),f"{table}.csv","text/csv")
