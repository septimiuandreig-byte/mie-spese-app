import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import os

# --- CONFIGURAZIONE FILE ---
FILE_DATI = 'spese_data.csv'
FILE_ABBONAMENTI = 'abbonamenti.csv'

# --- FUNZIONI DI GESTIONE DATI ---
def carica_dati():
    if not os.path.exists(FILE_DATI):
        df = pd.DataFrame(columns=['Data', 'Categoria', 'Importo', 'Note', 'Tipo'])
        df.to_csv(FILE_DATI, index=False)
    else:
        df = pd.read_csv(FILE_DATI)
    return df

def salva_dati(df):
    df.to_csv(FILE_DATI, index=False)

def carica_abbonamenti():
    if not os.path.exists(FILE_ABBONAMENTI):
        df = pd.DataFrame(columns=['Nome', 'Costo', 'Giorno_Rinnovo', 'Attivo'])
        df.to_csv(FILE_ABBONAMENTI, index=False)
    else:
        df = pd.read_csv(FILE_ABBONAMENTI)
    return df

def salva_abbonamenti(df):
    df.to_csv(FILE_ABBONAMENTI, index=False)

# --- CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="Le Mie Spese", page_icon="💰", layout="centered")

# CSS per rendere l'interfaccia più carina su mobile
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #007bff; color: white; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("💰 Gestione Finanze")

# --- LOGICA PRINCIPALE ---
oggi = datetime.date.today()
df = carica_dati()
df_sub = carica_abbonamenti()

# Assicurati che la colonna Data sia nel formato corretto
if not df.empty:
    df['Data'] = pd.to_datetime(df['Data']).dt.date

mese_corrente = oggi.month
anno_corrente = oggi.year

# 1. CONTROLLO STIPENDIO (Dopo il 15 del mese)
stipendio_inserito = pd.DataFrame()
if not df.empty:
    stipendio_inserito = df[
        (df['Categoria'] == 'Stipendio') & 
        (pd.to_datetime(df['Data']).dt.month == mese_corrente) &
        (pd.to_datetime(df['Data']).dt.year == anno_corrente)
    ]

if oggi.day > 15 and stipendio_inserito.empty:
    with st.container():
        st.warning("📢 **Controllo Stipendio**")
        st.info("Siamo oltre il 15 del mese. È arrivato lo stipendio?")
        col_s1, col_s2 = st.columns([2, 1])
        with col_s1:
            valore_stipendio = st.number_input("Importo ricevuto (€)", min_value=0.0, step=50.0)
        with col_s2:
            if st.button("Sì, salva"):
                nuova_riga = pd.DataFrame([{
                    'Data': oggi, 'Categoria': 'Stipendio', 'Importo': valore_stipendio,
                    'Note': 'Accredito mensile', 'Tipo': 'Entrata'
                }])
                df = pd.concat([df, nuova_riga], ignore_index=True)
                salva_dati(df)
                st.success("Stipendio registrato!")
                st.rerun()

# 2. MENU LATERALE: ABBONAMENTI E RICORRENTI
with st.sidebar:
    st.header("⚙️ Impostazioni")
    with st.expander("🔄 Gestisci Abbonamenti"):
        n_sub = st.text_input("Nome Servizio")
        c_sub = st.number_input("Costo Mensile", min_value=0.0)
        g_sub = st.slider("Giorno Rinnovo", 1, 31, 1)
        if st.button("Aggiungi Abbonamento"):
            nuova_s = pd.DataFrame([{'Nome': n_sub, 'Costo': c_sub, 'Giorno_Rinnovo': g_sub, 'Attivo': True}])
            df_sub = pd.concat([df_sub, nuova_s], ignore_index=True)
            salva_abbonamenti(df_sub)
            st.success("Abbonamento aggiunto!")
            st.rerun()
    
    if st.button("🔄 Controlla Rinnovi Mensili"):
        contatore = 0
        for _, row in df_sub.iterrows():
            gia_pagato = df[
                (df['Note'].str.contains(row['Nome'], na=False)) & 
                (pd.to_datetime(df['Data']).dt.month == mese_corrente)
            ]
            if oggi.day >= row['Giorno_Rinnovo'] and gia_pagato.empty:
                nuova_spesa = pd.DataFrame([{
                    'Data': oggi.replace(day=int(row['Giorno_Rinnovo'])),
                    'Categoria': 'Abbonamento', 'Importo': row['Costo'],
                    'Note': f"Rinnovo {row['Nome']}", 'Tipo': 'Uscita'
                }])
                df = pd.concat([df, nuova_spesa], ignore_index=True)
                contatore += 1
        if contatore > 0:
            salva_dati(df)
            st.success(f"Aggiornati {contatore} abbonamenti!")
            st.rerun()
        else:
            st.info("Tutto aggiornato!")

# 3. INSERIMENTO MANUALE
with st.expander("➕ Inserisci Nuova Spesa/Entrata", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        data_ins = st.date_input("Data", oggi)
        tipo_ins = st.selectbox("Tipo", ["Uscita", "Entrata"])
    with c2:
        importo_ins = st.number_input("Importo (€)", min_value=0.0)
        cat_ins = st.selectbox("Categoria", ["Piacere", "Ricarica", "Abbonamento", "Spesa", "Casa", "Trasporti", "Altro"])
    
    nota_ins = st.text_input("Descrizione (opzionale)")
    if st.button("REGISTRA MOVIMENTO"):
        nuovo_mov = pd.DataFrame([{
            'Data': data_ins, 'Categoria': cat_ins, 'Importo': importo_ins,
            'Note': nota_ins, 'Tipo': tipo_ins
        }])
        df = pd.concat([df, nuovo_mov], ignore_index=True)
        salva_dati(df)
        st.success("Registrato con successo!")
        st.rerun()

# 4. ANALISI E GRAFICI
st.divider()
df['Data'] = pd.to_datetime(df['Data'])
filtro_mese = df[df['Data'].dt.month == mese_corrente]

tot_u = filtro_mese[filtro_mese['Tipo'] == 'Uscita']['Importo'].sum()
tot_e = filtro_mese[filtro_mese['Tipo'] == 'Entrata']['Importo'].sum()

m1, m2, m3 = st.columns(3)
m1.metric("Entrate", f"€{tot_e:.2f}")
m2.metric("Uscite", f"€{tot_u:.2f}")
m3.metric("Residuo", f"€{tot_e - tot_u:.2f}")

if not filtro_mese[filtro_mese['Tipo'] == 'Uscita'].empty:
    st.subheader("Analisi Spese per Categoria")
    fig = px.pie(filtro_mese[filtro_mese['Tipo'] == 'Uscita'], values='Importo', names='Categoria', hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Ultimi Movimenti")
st.dataframe(df.sort_values(by='Data', ascending=False).head(10), use_container_width=True, hide_index=True)

# Funzione Reset
with st.sidebar:
    st.divider()
    if st.button("🗑️ Svuota Database"):
        if os.path.exists(FILE_DATI): os.remove(FILE_DATI)
        if os.path.exists(FILE_ABBONAMENTI): os.remove(FILE_ABBONAMENTI)
        st.rerun()
