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
        df['Data'] = pd.to_datetime(df['Data']).dt.date
        return df
    except Exception:
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

# --- CSS MINIMALE (RISOLVE IL PROBLEMA GRAFICO) ---
# Ho rimosso le regole che forzavano il bianco. 
# Ora si adatta automaticamente alla Dark Mode del tuo telefono.
st.markdown("""
    <style>
    div.block-container { padding-top: 1rem; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; font-weight: bold; }
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
# Controllo Stipendio
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
    st.warning("📅 È passato il 15. Hai preso lo stipendio?")
    if st.button("💰 Sì, registra 1500€ (Click rapido)"):
        nuova_riga = pd.DataFrame([{
            'Data': oggi, 'Categoria': 'Stipendio', 'Importo': 1500.0,
            'Note': 'Accredito mensile', 'Tipo': 'Entrata'
        }])
        df = pd.concat([df, nuova_riga], ignore_index=True)
        salva_dati(df)
        st.rerun()

# Controllo Rinnovi
if st.button("🔄 Controlla Rinnovi Scaduti", use_container_width=True):
    contatore = 0
    for _, row in df_sub.iterrows():
        if row['Attivo']:
            gia_pagato = df[
                (df['Note'].astype(str).str.contains(row['Nome'], case=False, na=False)) & 
                (pd.to_datetime(df['Data']).dt.month == mese_corrente)
            ]
            if oggi.day >= row['Giorno_Rinnovo'] and gia_pagato.empty:
                data_rinnovo = oggi.replace(day=int(row['Giorno_Rinnovo']))
                nuova_spesa = pd.DataFrame([{
                    'Data': data_rinnovo, 'Categoria': 'Abbonamento', 'Importo': row['Costo'],
                    'Note': f"Rinnovo {row['Nome']}", 'Tipo': 'Uscita'
                }])
                df = pd.concat([df, nuova_spesa], ignore_index=True)
                contatore += 1
    if contatore > 0:
        salva_dati(df)
        st.success(f"✅ Aggiornati {contatore} rinnovi!")
        st.rerun()
    else:
        st.info("👍 Nessun rinnovo da pagare oggi.")

st.divider()

# --- NAVIGAZIONE (DROPDOWN) ---
menu_options = ["📊 Dashboard", "➕ Nuova Spesa", "⚙️ Gestione Abbonamenti", "📝 Modifica Dati"]
scelta = st.selectbox("Naviga:", menu_options, label_visibility="collapsed")

# --- 1. DASHBOARD ---
if scelta == "📊 Dashboard":
    filtro_mese = df[pd.to_datetime(df['Data']).dt.month == mese_corrente] if not df.empty else pd.DataFrame()
    
    if not filtro_mese.empty:
        tot_u = filtro_mese[filtro_mese['Tipo'] == 'Uscita']['Importo'].sum()
        tot_e = filtro_mese[filtro_mese['Tipo'] == 'Entrata']['Importo'].sum()
        delta = tot_e - tot_u
    else:
        tot_u, tot_e, delta = 0.0, 0.0, 0.0

    k1, k2, k3 = st.columns(3)
    k1.metric("Entrate", f"€{tot_e:,.2f}")
    k2.metric("Uscite", f"€{tot_u:,.2f}")
    k3.metric("Saldo", f"€{delta:,.2f}", delta_color="normal")

    if tot_u > 0:
        st.subheader("Spese del mese")
        dati_grafico = filtro_mese[filtro_mese['Tipo'] == 'Uscita'].groupby('Categoria')['Importo'].sum().reset_index()
        fig = px.pie(dati_grafico, values='Importo', names='Categoria', hole=0.5)
        st.plotly_chart(fig, use_container_width=True)

# --- 2. NUOVA SPESA ---
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
        
        nota_ins = st.text_input("Descrizione")
        if st.form_submit_button("💾 Salva", use_container_width=True):
            if importo_ins > 0:
                nuovo_mov = pd.DataFrame([{
                    'Data': data_ins, 'Categoria': cat_ins, 'Importo': importo_ins,
                    'Note': nota_ins, 'Tipo': tipo_ins
                }])
                df = pd.concat([df, nuovo_mov], ignore_index=True)
                salva_dati(df)
                st.success("Salvato!")
                st.rerun()

# --- 3. GESTIONE ABBONAMENTI ---
elif scelta == "⚙️ Gestione Abbonamenti":
    st.subheader("I tuoi Abbonamenti")
    
    # SEZIONE AGGIUNTA
    with st.expander("➕ Aggiungi Nuovo", expanded=False):
        with st.form("form_sub"):
            n_sub = st.text_input("Nome (es. Netflix)")
            c_sub = st.number_input("Costo", min_value=0.0, step=0.5)
            g_sub = st.slider("Giorno Rinnovo", 1, 31, 1)
            if st.form_submit_button("Salva"):
                if n_sub:
                    nuova_s = pd.DataFrame([{'Nome': n_sub, 'Costo': c_sub, 'Giorno_Rinnovo': g_sub, 'Attivo': True}])
                    df_sub = pd.concat([df_sub, nuova_s], ignore_index=True)
                    salva_abbonamenti(df_sub)
                    st.rerun()

    # SEZIONE LISTA E MODIFICA RAPIDA
    st.write("📋 **Lista Attivi:**")
    st.dataframe(df_sub, use_container_width=True, hide_index=True)

    # SEZIONE ELIMINAZIONE (NUOVA E PIÙ FACILE)
    st.divider()
    st.subheader("🗑️ Elimina Abbonamento")
    if not df_sub.empty:
        col_del1, col_del2 = st.columns([2, 1])
        with col_del1:
            # Dropdown per scegliere quale eliminare (più facile da usare su mobile)
            nome_da_eliminare = st.selectbox("Scegli quale eliminare:", df_sub['Nome'].unique())
        with col_del2:
            st.write("") # Spaziatore
            st.write("") 
            if st.button("Elimina ❌"):
                df_sub = df_sub[df_sub['Nome'] != nome_da_eliminare]
                salva_abbonamenti(df_sub)
                st.success(f"{nome_da_eliminare} eliminato!")
                st.rerun()
    else:
        st.info("Nessun abbonamento attivo.")

# --- 4. MODIFICA DATI ---
elif scelta == "📝 Modifica Dati":
    st.subheader("Tutti i movimenti")
    st.info("Per eliminare: clicca la riga, poi clicca l'icona del cestino che appare a destra (o premi Canc).")
    
    df_edited = st.data_editor(
        df, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "Importo": st.column_config.NumberColumn("€", format="%.2f €")
        }
    )

    if not df.equals(df_edited):
        salva_dati(df_edited)
        st.rerun()
