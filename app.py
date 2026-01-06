import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
from github import Github
from io import StringIO

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Le Mie Spese", page_icon="💰", layout="centered")

# Recuperiamo le credenziali dai Secrets
try:
    token = st.secrets["github"]["token"]
    repo_name = st.secrets["github"]["repo_name"]
except:
    st.error("Errore: Manca la chiave nei Secrets di Streamlit!")
    st.stop()

# Connessione a GitHub
try:
    g = Github(token)
    repo = g.get_repo(repo_name)
except Exception as e:
    st.error(f"Impossibile connettersi a GitHub: {e}")
    st.stop()

BRANCH = "main"
FILE_DATI = 'spese_data.csv'
FILE_ABBONAMENTI = 'abbonamenti.csv'
CATEGORIE = ["Piacere", "Ricarica", "Abbonamento", "Spesa", "Casa", "Trasporti", "Stipendio", "Altro"]

# --- FUNZIONI ---
def carica_csv(filename, cols):
    try:
        content = repo.get_contents(filename, ref=BRANCH)
        decoded = content.decoded_content.decode("utf-8")
        df = pd.read_csv(StringIO(decoded))
        if 'Data' in df.columns: df['Data'] = pd.to_datetime(df['Data']).dt.date
        return df
    except:
        return pd.DataFrame(columns=cols)

def salva_csv(df, filename, msg):
    csv_content = df.to_csv(index=False)
    try:
        content = repo.get_contents(filename, ref=BRANCH)
        repo.update_file(content.path, msg, csv_content, content.sha, branch=BRANCH)
    except:
        repo.create_file(filename, msg, csv_content, branch=BRANCH)

# --- APP ---
st.title("💰 Gestione Spese Cloud")

with st.spinner('Sincronizzazione GitHub...'):
    df = carica_csv(FILE_DATI, ['Data', 'Categoria', 'Importo', 'Note', 'Tipo'])
    df_sub = carica_csv(FILE_ABBONAMENTI, ['Nome', 'Costo', 'Giorno_Rinnovo', 'Attivo'])

oggi = datetime.date.today()

# Controllo Stipendio
preso = False
if not df.empty:
    if not df[(df['Categoria']=='Stipendio') & (pd.to_datetime(df['Data']).dt.month == oggi.month)].empty:
        preso = True

if oggi.day > 15 and not preso:
    st.warning("📅 Stipendio arrivato?")
    c1, c2 = st.columns([0.6,0.4])
    imp = c1.number_input("Euro", value=1500.0, step=50.0)
    if c2.button("SI, REGISTRA"):
        nuova = pd.DataFrame([{'Data': oggi, 'Categoria': 'Stipendio', 'Importo': imp, 'Note': 'Accredito', 'Tipo': 'Entrata'}])
        df = pd.concat([df, nuova], ignore_index=True)
        salva_csv(df, FILE_DATI, "Stipendio")
        st.success("Salvato!")
        st.rerun()

# Menu
scelta = st.selectbox("Vai a:", ["📊 Dashboard", "➕ Aggiungi", "⚙️ Abbonamenti", "📝 Modifica"], label_visibility="collapsed")

if scelta == "➕ Aggiungi":
    st.subheader("Nuovo Movimento")
    tipo = st.radio("Tipo", ["Uscita", "Entrata"], horizontal=True)
    with st.form("add"):
        d = st.date_input("Data", oggi)
        i = st.number_input("Importo", min_value=0.0)
        c = st.selectbox("Categoria", CATEGORIE)
        n = st.text_input("Note")
        if st.form_submit_button("SALVA"):
            if i > 0:
                nuova = pd.DataFrame([{'Data': d, 'Categoria': c, 'Importo': i, 'Note': n, 'Tipo': "Uscita" if "Uscita" in tipo else "Entrata"}])
                df = pd.concat([df, nuova], ignore_index=True)
                salva_csv(df, FILE_DATI, f"Spesa: {n}")
                st.toast("Salvato su GitHub!", icon="✅")
                import time
                time.sleep(2)
                st.rerun()

elif scelta == "📊 Dashboard":
    sub = df[pd.to_datetime(df['Data']).dt.month == oggi.month] if not df.empty else pd.DataFrame()
    if not sub.empty:
        e = sub[sub['Tipo']=='Entrata']['Importo'].sum()
        u = sub[sub['Tipo']=='Uscita']['Importo'].sum()
        k1, k2, k3 = st.columns(3)
        k1.metric("Entrate", f"€{e:.2f}")
        k2.metric("Uscite", f"€{u:.2f}")
        k3.metric("Saldo", f"€{e-u:.2f}")
        if u > 0:
            st.plotly_chart(px.pie(sub[sub['Tipo']=='Uscita'], values='Importo', names='Categoria', hole=0.5), use_container_width=True)
    else:
        st.info("Nessun dato questo mese.")

elif scelta == "⚙️ Abbonamenti":
    st.subheader("Abbonamenti")
    with st.form("sub"):
        n = st.text_input("Nome")
        c = st.number_input("Costo", min_value=0.0)
        g = st.slider("Giorno", 1, 31, 1)
        if st.form_submit_button("Aggiungi"):
            nuova = pd.DataFrame([{'Nome': n, 'Costo': c, 'Giorno_Rinnovo': g, 'Attivo': True}])
            df_sub = pd.concat([df_sub, nuova], ignore_index=True)
            salva_csv(df_sub, FILE_ABBONAMENTI, f"Nuovo sub: {n}")
            st.rerun()
    if not df_sub.empty:
        dele = st.selectbox("Elimina:", df_sub['Nome'].unique())
        if st.button("ELIMINA"):
            df_sub = df_sub[df_sub['Nome'] != dele]
            salva_csv(df_sub, FILE_ABBONAMENTI, "Eliminato sub")
            st.rerun()
        st.dataframe(df_sub, hide_index=True)

elif scelta == "📝 Modifica":
    st.warning("Ogni modifica salva su GitHub.")
    df_new = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    if not df.equals(df_new):
        salva_csv(df_new, FILE_DATI, "Modifica manuale")
        st.rerun()
                                   
