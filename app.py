import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
from github import Github
from io import StringIO

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Gestione Finanze", page_icon="💰", layout="centered")

# --- RECUPERO CREDENZIALI ---
try:
    token = st.secrets["github"]["token"]
    repo_name = st.secrets["github"]["repo_name"]
except:
    st.error("Errore: Manca la chiave nei Secrets di Streamlit!")
    st.stop()

# --- CONNESSIONE GITHUB ---
try:
    g = Github(token)
    repo = g.get_repo(repo_name)
except Exception as e:
    st.error(f"Errore connessione GitHub: {e}")
    st.stop()

BRANCH = "main"
FILE_DATI = 'spese_data.csv'
FILE_RICORRENTI = 'ricorrenti.csv' # Nuovo nome per il file abbonamenti/rate

# Categorie disponibili
CATEGORIE_USCITE = ["Spesa", "Casa", "Bollette", "Svago", "Auto", "Salute", "Rata", "Abbonamento", "Altro"]
CATEGORIE_ENTRATE = ["Stipendio", "Regalo", "Rimborso", "Extra", "Altro"]

# --- FUNZIONI ---
def carica_csv(filename, cols):
    try:
        content = repo.get_contents(filename, ref=BRANCH)
        decoded = content.decoded_content.decode("utf-8")
        df = pd.read_csv(StringIO(decoded))
        if 'Data' in df.columns: df['Data'] = pd.to_datetime(df['Data']).dt.date
        
        # Aggiungiamo colonne mancanti se il file è vecchio
        for col in cols:
            if col not in df.columns:
                df[col] = "" if col != "Attivo" else True
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
st.title("💰 Gestione Finanze")

# 1. CARICAMENTO DATI
with st.spinner('Sincronizzazione dati...'):
    df = carica_csv(FILE_DATI, ['Data', 'Categoria', 'Importo', 'Note', 'Tipo'])
    # Carichiamo il file ricorrenti (ex abbonamenti) con la nuova colonna 'Etichetta'
    df_rec = carica_csv(FILE_RICORRENTI, ['Nome', 'Costo', 'Giorno', 'Etichetta', 'Attivo'])

oggi = datetime.date.today()
mese_corr = oggi.month
anno_corr = oggi.year

# 2. AUTOMAZIONE: CONTROLLO SCADENZE (Rate e Abbonamenti)
nuovi_inserimenti = False
if not df_rec.empty:
    for index, row in df_rec.iterrows():
        if row['Attivo']:
            # Cerchiamo se è già stato pagato questo mese/anno
            # Usiamo il nome e il mese per verificare
            gia_pagato = df[
                (df['Note'].astype(str).str.contains(f"AUTO: {row['Nome']}", case=False, na=False)) & 
                (pd.to_datetime(df['Data']).dt.month == mese_corr) &
                (pd.to_datetime(df['Data']).dt.year == anno_corr)
            ]
            
            # Se oggi è passato il giorno X e non c'è il pagamento
            if oggi.day >= int(row['Giorno']) and gia_pagato.empty:
                data_pagamento = oggi.replace(day=int(row['Giorno']))
                tipo_spesa = row['Etichetta'] if 'Etichetta' in row and row['Etichetta'] else "Abbonamento"
                
                nuova_riga = pd.DataFrame([{
                    'Data': data_pagamento,
                    'Categoria': tipo_spesa, # Usa Rata o Abbonamento come categoria
                    'Importo': row['Costo'],
                    'Note': f"AUTO: {row['Nome']}", # Nota speciale per riconoscerlo
                    'Tipo': 'Uscita'
                }])
                df = pd.concat([df, nuova_riga], ignore_index=True)
                nuovi_inserimenti = True

if nuovi_inserimenti:
    salva_csv(df, FILE_DATI, "Inserimento automatico ricorrenti")
    st.toast("✅ Rate e Abbonamenti inseriti automaticamente!", icon="robot")
    # Non facciamo rerun immediato per non bloccare, si aggiornerà al prossimo click

# 3. MENU NAVIGAZIONE
scelta = st.selectbox("Menu:", ["📊 Dashboard & Grafici", "➕ Aggiungi Movimento", "🔄 Spese Ricorrenti (Rate/Sub)", "📝 Modifica Dati"], label_visibility="collapsed")

# --- DASHBOARD ---
if scelta == "📊 Dashboard & Grafici":
    # Filtro dati mese corrente
    mask_mese = (pd.to_datetime(df['Data']).dt.month == mese_corr) & (pd.to_datetime(df['Data']).dt.year == anno_corr)
    df_mese = df[mask_mese] if not df.empty else pd.DataFrame()

    if not df_mese.empty:
        entrate = df_mese[df_mese['Tipo']=='Entrata']['Importo'].sum()
        uscite = df_mese[df_mese['Tipo']=='Uscita']['Importo'].sum()
        
        # KPI in alto
        k1, k2, k3 = st.columns(3)
        k1.metric("Entrate Mese", f"€ {entrate:,.2f}")
        k2.metric("Uscite Mese", f"€ {uscite:,.2f}")
        k3.metric("Saldo Mese", f"€ {entrate - uscite:,.2f}", delta_color="normal")

        st.divider()

        # GRAFICI A TORTA
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("🔴 Uscite")
            df_uscite = df_mese[df_mese['Tipo']=='Uscita']
            if not df_uscite.empty:
                fig_u = px.pie(df_uscite, values='Importo', names='Categoria', hole=0.4)
                fig_u.update_traces(textinfo='percent+label')
                st.plotly_chart(fig_u, use_container_width=True)
            else:
                st.info("Nessuna uscita.")

        with c2:
            st.subheader("🟢 Entrate")
            df_entrate = df_mese[df_mese['Tipo']=='Entrata']
            if not df_entrate.empty:
                fig_e = px.pie(df_entrate, values='Importo', names='Categoria', hole=0.4)
                fig_e.update_traces(textinfo='percent+label')
                st.plotly_chart(fig_e, use_container_width=True)
            else:
                st.info("Nessuna entrata.")
        
        # Lista ultimi movimenti
        st.write("📋 **Ultimi movimenti del mese:**")
        st.dataframe(df_mese.sort_values(by="Data", ascending=False).head(5), hide_index=True, use_container_width=True)

    else:
        st.info("Nessun dato registrato in questo mese.")

# --- AGGIUNGI MOVIMENTO ---
elif scelta == "➕ Aggiungi Movimento":
    st.subheader("Nuovo Movimento")
    tipo = st.radio("Tipo", ["Uscita", "Entrata"], horizontal=True)
    
    with st.form("add_mov"):
        c1, c2 = st.columns(2)
        d = c1.date_input("Data", oggi)
        i = c2.number_input("Importo (€)", min_value=0.0, step=1.0)
        
        lista_cat = CATEGORIE_USCITE if tipo == "Uscita" else CATEGORIE_ENTRATE
        cat = st.selectbox("Categoria", lista_cat)
        note = st.text_input("Note (opzionale)")
        
        if st.form_submit_button("💾 SALVA"):
            if i > 0:
                nuova = pd.DataFrame([{
                    'Data': d, 'Categoria': cat, 'Importo': i, 
                    'Note': note, 'Tipo': tipo
                }])
                df = pd.concat([df, nuova], ignore_index=True)
                salva_csv(df, FILE_DATI, f"Nuovo: {cat} - {i}€")
                st.success("Salvato!")
                st.rerun()
            else:
                st.error("Inserisci un importo maggiore di 0.")

# --- SPESE RICORRENTI (ex Abbonamenti) ---
elif scelta == "🔄 Spese Ricorrenti (Rate/Sub)":
    st.subheader("Gestione Spese Fisse")
    
    # CALCOLO TOTALE MENSILE
    totale_fisso = 0.0
    if not df_rec.empty:
        totale_fisso = df_rec[df_rec['Attivo'] == True]['Costo'].sum()
    
    # Mostriamo il totale in grande
    st.metric("Totale Spese Fisse Mensili", f"€ {totale_fisso:,.2f}")
    st.caption("Questo importo viene detratto automaticamente ogni mese nel giorno indicato.")
    
    st.divider()

    with st.expander("➕ Aggiungi nuova spesa ricorrente", expanded=False):
        with st.form("add_rec"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome (es. Netflix, Rata Auto)")
            costo = c2.number_input("Costo Mensile (€)", min_value=0.0, step=0.5)
            
            c3, c4 = st.columns(2)
            giorno = c3.slider("Giorno del mese", 1, 31, 1)
            etichetta = c4.selectbox("Etichetta", ["Abbonamento", "Rata", "Affitto", "Altro"])
            
            if st.form_submit_button("Aggiungi Ricorrenza"):
                if nome and costo > 0:
                    nuova = pd.DataFrame([{
                        'Nome': nome, 'Costo': costo, 'Giorno': giorno, 
                        'Etichetta': etichetta, 'Attivo': True
                    }])
                    df_rec = pd.concat([df_rec, nuova], ignore_index=True)
                    salva_csv(df_rec, FILE_RICORRENTI, f"Nuova ricorrenza: {nome}")
                    st.success("Aggiunto!")
                    st.rerun()
                else:
                    st.error("Compila nome e costo.")

    # Lista modificabile ed eliminabile
    if not df_rec.empty:
        st.write("🔻 **Lista Attiva:**")
        
        # Creiamo una tabella visiva pulita
        st.dataframe(
            df_rec, 
            column_config={
                "Attivo": st.column_config.CheckboxColumn("Attivo", help="Deseleziona per mettere in pausa"),
                "Costo": st.column_config.NumberColumn("€ Costo", format="€ %.2f")
            },
            hide_index=True,
            use_container_width=True
        )
        
        st.caption("Per eliminare definitivamente:")
        col_del1, col_del2 = st.columns([0.7, 0.3])
        da_eliminare = col_del1.selectbox("Seleziona da eliminare:", df_rec['Nome'].unique(), label_visibility="collapsed")
        if col_del2.button("🗑️ ELIMINA"):
            df_rec = df_rec[df_rec['Nome'] != da_eliminare]
            salva_csv(df_rec, FILE_RICORRENTI, f"Eliminato: {da_eliminare}")
            st.rerun()

# --- MODIFICA DATI ---
elif scelta == "📝 Modifica Dati":
    st.warning("⚠️ Qui modifichi direttamente il database storico.")
    df_edited = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    if not df.equals(df_edited):
        salva_csv(df_edited, FILE_DATI, "Modifica manuale database")
        st.rerun()
