import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Le Mie Spese", page_icon="💰", layout="centered")

# --- COSTANTI ---
FILE_DATI = 'spese_data.csv'
FILE_ABBONAMENTI = 'abbonamenti.csv'
CATEGORIE = ["Piacere", "Ricarica", "Abbonamento", "Spesa", "Casa", "Trasporti", "Altro", "Stipendio"]

# --- FUNZIONI DI GESTIONE DATI ---
def carica_dati():
    if not os.path.exists(FILE_DATI):
        df = pd.DataFrame(columns=['Data', 'Categoria', 'Importo', 'Note', 'Tipo'])
        df.to_csv(FILE_DATI, index=False)
        return df
    
    try:
        df = pd.read_csv(FILE_DATI)
        # Conversione robusta della data
        df['Data'] = pd.to_datetime(df['Data']).dt.date
        return df
    except Exception as e:
        st.error(f"Errore lettura file dati: {e}")
        return pd.DataFrame(columns=['Data', 'Categoria', 'Importo', 'Note', 'Tipo'])

def salva_dati(df):
    df.to_csv(FILE_DATI, index=False)

def carica_abbonamenti():
    if not os.path.exists(FILE_ABBONAMENTI):
        df = pd.DataFrame(columns=['Nome', 'Costo', 'Giorno_Rinnovo', 'Attivo'])
        df.to_csv(FILE_ABBONAMENTI, index=False)
        return df
    return pd.read_csv(FILE_ABBONAMENTI)

def salva_abbonamenti(df):
    df.to_csv(FILE_ABBONAMENTI, index=False)

# --- CSS CUSTOM PER MOBILE ---
st.markdown("""
    <style>
    .stSelectbox > div > div { background-color: #f0f2f6; border-radius: 10px; }
    .stMetric { background-color: #ffffff; border: 1px solid #e6e6e6; border-radius: 10px; padding: 10px; }
    div.block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

# --- INIZIALIZZAZIONE ---
st.title("💰 Gestione Finanze")
oggi = datetime.date.today()
mese_corrente = oggi.month
anno_corrente = oggi.year

df = carica_dati()
df_sub = carica_abbonamenti()

# --- LOGICA AUTOMATICA (STIPENDIO & RINNOVI) ---
# Eseguiamo questi controlli a prescindere dalla pagina visualizzata

# 1. Controllo Stipendio
stipendio_gia_preso = False
if not df.empty:
    check_stipendio = df[
        (df['Categoria'] == 'Stipendio') & 
        (pd.to_datetime(df['Data']).dt.month == mese_corrente) &
        (pd.to_datetime(df['Data']).dt.year == anno_corrente)
    ]
    if not check_stipendio.empty:
        stipendio_gia_preso = True

if oggi.day > 15 and not stipendio_gia_preso:
    st.warning("📅 È passato il 15 del mese.")
    col_s1, col_s2 = st.columns([0.7, 0.3])
    valore_stipendio = col_s1.number_input("Inserisci Stipendio (€)", value=1500.0, step=50.0, label_visibility="collapsed")
    if col_s2.button("💰 Salva"):
        nuova_riga = pd.DataFrame([{
            'Data': oggi, 'Categoria': 'Stipendio', 'Importo': valore_stipendio,
            'Note': 'Accredito mensile', 'Tipo': 'Entrata'
        }])
        df = pd.concat([df, nuova_riga], ignore_index=True)
        salva_dati(df)
        st.toast("Stipendio registrato!", icon="✅")
        st.rerun()

# 2. Controllo Rinnovi Abbonamenti
if st.button("🔄 Controlla Rinnovi Scaduti", use_container_width=True):
    contatore = 0
    for _, row in df_sub.iterrows():
        if row['Attivo']:
            # Cerchiamo se esiste già una spesa questo mese con il nome dell'abbonamento nelle note
            gia_pagato = df[
                (df['Note'].astype(str).str.contains(row['Nome'], case=False, na=False)) & 
                (pd.to_datetime(df['Data']).dt.month == mese_corrente) &
                (pd.to_datetime(df['Data']).dt.year == anno_corrente)
            ]
            
            # Se oggi è passato il giorno di rinnovo e non è stato pagato
            if oggi.day >= row['Giorno_Rinnovo'] and gia_pagato.empty:
                data_rinnovo = oggi.replace(day=int(row['Giorno_Rinnovo']))
                nuova_spesa = pd.DataFrame([{
                    'Data': data_rinnovo,
                    'Categoria': 'Abbonamento', 'Importo': row['Costo'],
                    'Note': f"Rinnovo {row['Nome']}", 'Tipo': 'Uscita'
                }])
                df = pd.concat([df, nuova_spesa], ignore_index=True)
                contatore += 1
    
    if contatore > 0:
        salva_dati(df)
        st.success(f"✅ Aggiunti {contatore} rinnovi automatici!")
        st.rerun()
    else:
        st.info("👍 Nessun nuovo rinnovo da registrare.")

st.divider()

# --- NAVIGAZIONE (DROPDOWN MENU) ---
# Come richiesto nelle tue preferenze, la navbar è gestita dal menu a tendina
menu_options = ["📊 Dashboard", "➕ Nuova Spesa", "⚙️ Gestione Abbonamenti", "📝 Modifica Dati"]
scelta = st.selectbox("Naviga:", menu_options, label_visibility="collapsed")

# --- PAGINA 1: DASHBOARD ---
if scelta == "📊 Dashboard":
    # Calcoli
    filtro_mese = df[pd.to_datetime(df['Data']).dt.month == mese_corrente] if not df.empty else pd.DataFrame()
    
    if not filtro_mese.empty:
        tot_u = filtro_mese[filtro_mese['Tipo'] == 'Uscita']['Importo'].sum()
        tot_e = filtro_mese[filtro_mese['Tipo'] == 'Entrata']['Importo'].sum()
        delta = tot_e - tot_u
    else:
        tot_u, tot_e, delta = 0.0, 0.0, 0.0

    # KPI
    k1, k2, k3 = st.columns(3)
    k1.metric("Entrate", f"€{tot_e:,.2f}")
    k2.metric("Uscite", f"€{tot_u:,.2f}", delta_color="inverse")
    k3.metric("Saldo", f"€{delta:,.2f}", delta_color="normal")

    # Grafico a Torta (Solo se ci sono uscite)
    if tot_u > 0:
        st.subheader("Spese per Categoria")
        dati_grafico = filtro_mese[filtro_mese['Tipo'] == 'Uscita'].groupby('Categoria')['Importo'].sum().reset_index()
        fig = px.pie(dati_grafico, values='Importo', names='Categoria', hole=0.5, color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nessuna uscita registrata questo mese.")

# --- PAGINA 2: NUOVA SPESA ---
elif scelta == "➕ Nuova Spesa":
    st.subheader("Inserisci Movimento")
    
    with st.form("form_spesa"):
        c1, c2 = st.columns(2)
        with c1:
            data_ins = st.date_input("Data", oggi)
            tipo_ins = st.selectbox("Tipo", ["Uscita", "Entrata"])
        with c2:
            importo_ins = st.number_input("Importo (€)", min_value=0.0, step=1.0)
            cat_ins = st.selectbox("Categoria", CATEGORIE)
        
        nota_ins = st.text_input("Descrizione (es. Pizza, Benzina...)")
        
        submitted = st.form_submit_button("💾 Salva Movimento", use_container_width=True)
        
        if submitted:
            if importo_ins > 0:
                nuovo_mov = pd.DataFrame([{
                    'Data': data_ins, 'Categoria': cat_ins, 'Importo': importo_ins,
                    'Note': nota_ins, 'Tipo': tipo_ins
                }])
                df = pd.concat([df, nuovo_mov], ignore_index=True)
                salva_dati(df)
                st.success("Movimento salvato!")
                st.rerun()
            else:
                st.error("L'importo deve essere maggiore di 0.")

# --- PAGINA 3: GESTIONE ABBONAMENTI ---
elif scelta == "⚙️ Gestione Abbonamenti":
    st.subheader("I tuoi Abbonamenti")
    
    # Form aggiunta
    with st.expander("➕ Aggiungi Nuovo Abbonamento"):
        with st.form("form_sub"):
            n_sub = st.text_input("Nome (es. Netflix)")
            c_sub = st.number_input("Costo Mensile", min_value=0.0, step=0.5)
            g_sub = st.slider("Giorno del rinnovo", 1, 31, 1)
            
            if st.form_submit_button("Salva Abbonamento"):
                if n_sub:
                    nuova_s = pd.DataFrame([{'Nome': n_sub, 'Costo': c_sub, 'Giorno_Rinnovo': g_sub, 'Attivo': True}])
                    df_sub = pd.concat([df_sub, nuova_s], ignore_index=True)
                    salva_abbonamenti(df_sub)
                    st.success("Abbonamento aggiunto!")
                    st.rerun()
                else:
                    st.error("Inserisci un nome.")

    # Tabella Modificabile Abbonamenti
    st.write("Modifica o cancella abbonamenti qui sotto:")
    df_sub_edited = st.data_editor(df_sub, num_rows="dynamic", use_container_width=True, key="editor_sub")
    
    # Se ci sono cambiamenti, salva
    if not df_sub.equals(df_sub_edited):
        salva_abbonamenti(df_sub_edited)
        st.toast("Modifiche agli abbonamenti salvate!", icon="💾")
        st.rerun()

# --- PAGINA 4: MODIFICA DATI ---
elif scelta == "📝 Modifica Dati":
    st.subheader("Database Completo")
    st.info("Puoi modificare celle o cancellare righe (seleziona la riga e premi Canc/Del).")
    
    # Tabella Modificabile (Data Editor è molto meglio di dataframe statico)
    df_edited = st.data_editor(
        df, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "Importo": st.column_config.NumberColumn("€ Importo", format="€ %.2f")
        }
    )

    # Salvataggio automatico se modificato
    # Nota: confrontiamo con tolleranza per evitare loop infiniti sui float
    if not df.equals(df_edited):
        salva_dati(df_edited)
        st.toast("Database aggiornato!", icon="💾")
        # Non facciamo rerun qui per evitare refresh continui mentre scrivi

    st.divider()
    if st.button("🗑️ RESET TOTALE (Attenzione!)"):
        if os.path.exists(FILE_DATI): os.remove(FILE_DATI)
        if os.path.exists(FILE_ABBONAMENTI): os.remove(FILE_ABBONAMENTI)
        st.error("Database cancellato.")
        st.rerun()
