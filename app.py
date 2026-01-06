import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import os

# --- CONFIGURAZIONE ---
FILE_DATI = 'spese_data.csv'
FILE_ABBONAMENTI = 'abbonamenti.csv'

# --- FUNZIONI DI SUPPORTO ---
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

# --- INTERFACCIA ---
st.set_page_config(page_title="Le Mie Spese", page_icon="💰", layout="centered")

# Titolo e Stile
st.markdown("## 💰 Gestione Finanze")

# 1. LOGICA STIPENDIO (Check dopo il 15 del mese)
oggi = datetime.date.today()
df = carica_dati()

# Converti la colonna Data in datetime
df['Data'] = pd.to_datetime(df['Data']).dt.date

mese_corrente = oggi.month
anno_corrente = oggi.year

# Controlla se lo stipendio è già stato inserito questo mese
stipendio_inserito = df[
    (df['Categoria'] == 'Stipendio') & 
    (pd.to_datetime(df['Data']).dt.month == mese_corrente)
]

if today_day := today_day := oggi.day > 15 and stipendio_inserito.empty:
    st.warning("⚠️ Siamo oltre il 15 e non vedo lo stipendio!")
    col1, col2 = st.columns([2, 1])
    with col1:
        stipendio_val = st.number_input("Quanto è arrivato?", min_value=0.0, step=50.0, key="stipendio_input")
    with col2:
        if st.button("💰 Aggiungi"):
            nuova_riga = pd.DataFrame([{
                'Data': oggi,
                'Categoria': 'Stipendio',
                'Importo': stipendio_val,
                'Note': 'Stipendio mensile',
                'Tipo': 'Entrata'
            }])
            df = pd.concat([df, nuova_riga], ignore_index=True)
            salva_dati(df)
            st.rerun()

# 2. GESTIONE ABBONAMENTI (Logica rinnovo)
st.sidebar.header("🔄 Abbonamenti")
df_sub = carica_abbonamenti()
with st.sidebar.expander("Gestisci Abbonamenti"):
    nome_sub = st.text_input("Nome (es. Netflix)")
    costo_sub = st.number_input("Costo", min_value=0.0)
    giorno_sub = st.slider("Giorno del rinnovo", 1, 28, 1)
    if st.button("Salva Abbonamento"):
        nuova_sub = pd.DataFrame([{'Nome': nome_sub, 'Costo': costo_sub, 'Giorno_Rinnovo': giorno_sub, 'Attivo': True}])
        df_sub = pd.concat([df_sub, nuova_sub], ignore_index=True)
        salva_abbonamenti(df_sub)
        st.success("Abbonamento salvato!")
        st.rerun()

# Controllo se oggi è giorno di rinnovo (Manuale per sicurezza)
if st.sidebar.button("Controlla Rinnovi Oggi"):
    count_rinnovi = 0
    for index, row in df_sub.iterrows():
        # Se è il giorno giusto e non è già stato pagato questo mese (semplificato)
        gia_pagato = df[
            (df['Categoria'] == 'Abbonamento') & 
            (df['Note'].str.contains(row['Nome'], na=False)) &
            (pd.to_datetime(df['Data']).dt.month == mese_corrente)
        ]
        
        if oggi.day >= row['Giorno_Rinnovo'] and gia_pagato.empty and row['Attivo']:
            nuova_spesa = pd.DataFrame([{
                'Data': oggi,
                'Categoria': 'Abbonamento',
                'Importo': row['Costo'],
                'Note': f"Rinnovo {row['Nome']}",
                'Tipo': 'Uscita'
            }])
            df = pd.concat([df, nuova_spesa], ignore_index=True)
            count_rinnovi += 1
    
    if count_rinnovi > 0:
        salva_dati(df)
        st.success(f"Rinnovati {count_rinnovi} abbonamenti!")
    else:
        st.info("Nessun rinnovo necessario oggi.")

# 3. INSERIMENTO SPESE/ENTRATE
with st.expander("➕ Aggiungi Movimento", expanded=True):
    col_a, col_b = st.columns(2)
    with col_a:
        data_mov = st.date_input("Data", oggi)
        tipo = st.selectbox("Tipo", ["Uscita", "Entrata"])
    with col_b:
        importo = st.number_input("Importo (€)", min_value=0.0, step=1.0)
        categoria = st.selectbox("Etichetta", ["Spesa", "Piacere", "Ricarica", "Casa", "Auto", "Salute", "Altro"])
    
    note = st.text_input("Note")
    
    if st.button("Salva Movimento", use_container_width=True):
        nuova_riga = pd.DataFrame([{
            'Data': data_mov,
            'Categoria': categoria,
            'Importo': importo,
            'Note': note,
            'Tipo': tipo
        }])
        df = pd.concat([df, nuova_riga], ignore_index=True)
        salva_dati(df)
        st.success("Salvato!")
        st.rerun()

# 4. DASHBOARD E GRAFICI
st.divider()

# Filtri Mese
df['Data'] = pd.to_datetime(df['Data']) # Riconverto per sicurezza calcoli
spese_mese = df[(df['Data'].dt.month == mese_corrente) & (df['Tipo'] == 'Uscita')]
entrate_mese = df[(df['Data'].dt.month == mese_corrente) & (df['Tipo'] == 'Entrata')]

tot_uscite = spese_mese['Importo'].sum()
tot_entrate = entrate_mese['Importo'].sum()
bilancio = tot_entrate - tot_uscite

col1, col2, col3 = st.columns(3)
col1.metric("Entrate", f"€ {tot_entrate:.2f}")
col2.metric("Uscita", f"€ {tot_uscite:.2f}", delta_color="inverse")
col3.metric("Saldo", f"€ {bilancio:.2f}")

# Grafico a Torta
if not spese_mese.empty:
    st.subheader("Dove hai speso di più?")
    fig = px.pie(spese_mese, values='Importo', names='Categoria', title='Spese del Mese', hole=0.4)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nessuna spesa registrata questo mese.")

# Storico
st.subheader("Ultimi Movimenti")
st.dataframe(df.sort_values(by='Data', ascending=False).head(10), hide_index=True)

# Tasto Reset (nascosto in basso)
with st.expander("Zona Pericolo"):
    if st.button("CANCELLA TUTTI I DATI"):
        os.remove(FILE_DATI)
        st.warning("Dati cancellati.")
        st.rerun()
