import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

# Varna osvežitev strani
def varno_osvezi():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

st.set_page_config(page_title="Družinski Proračun", page_icon="💰", layout="centered")

# --- PIN ZAŠČITA ---
PRAVILNI_PIN = "18122018"

if "avtenticiran" not in st.session_state:
    st.session_state.avtenticiran = False

if not st.session_state.avtenticiran:
    st.title("🔒 Družinski Proračun")
    vnesen_pin = st.text_input("Vnesite PIN za vstop", type="password")
    
    if st.button("Vstopi", type="primary"):
        if vnesen_pin == PRAVILNI_PIN:
            st.session_state.avtenticiran = True
            varno_osvezi()
        else:
            st.error("Napačen PIN! Poskusite znova.")
    st.stop()

# --- GLAVNI DEL APLIKACIJE ---

with st.sidebar:
    if st.button("Odjava"):
        st.session_state.avtenticiran = False
        varno_osvezi()

conn = sqlite3.connect("druzinski_proracun.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS transakcije (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        datum TEXT NOT NULL,
        clan TEXT NOT NULL,
        tip TEXT NOT NULL,
        kategorija TEXT NOT NULL,
        znesek REAL NOT NULL,
        opis TEXT
    )
""")
conn.commit()

st.title("💰 Družinski Proračun")

# 1. Obrazec za vnos nove transakcije
with st.expander("➕ Dodaj nov vnos", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        clan = st.selectbox("Družinski član", ["Miha", "Lana", "Rea", "Oli"])
        tip = st.radio("Vrsta", ["odhodek", "prihodek"], horizontal=True)
        znesek = st.number_input("Znesek (€)", min_value=0.01, step=1.0)
    with col2:
        izbran_datum = st.date_input("Datum transakcije", value=date.today())
        kategorije = ["Hrana", "Položnice", "Bencin", "Zabava", "Plača", "Drugo", "Kredit", "Elektrika Avto"]
        kategorija = st.selectbox("Kategorija", kategorije)
        opis = st.text_input("Opis (neobvezno)")

    if st.button("Shrani transakcijo", type="primary"):
        cursor.execute("""
            INSERT INTO transakcije (datum, clan, tip, kategorija, znesek, opis)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (izbran_datum.isoformat(), clan, tip, kategorija, znesek, opis))
        conn.commit()
        st.success("Transakcija shranjena!")
        varno_osvezi()

# 2. Branje in filtriranje zgodovine
df = pd.read_sql_query("SELECT * FROM transakcije ORDER BY datum DESC, id DESC", conn)

if not df.empty:
    df["datum_dt"] = pd.to_datetime(df["datum"])
    df["leto_mesec"] = df["datum_dt"].dt.strftime("%Y-%m")

    st.subheader("🔍 Iskanje po zgodovini")

    # Filtri v dveh vrsticah
    fcol1, fcol2 = st.columns(2)
    with fcol1:
        seznam_mesecev = ["Vsi meseci"] + sorted(df["leto_mesec"].unique().tolist(), reverse=True)
        filter_mesec = st.selectbox("📅 Mesec:", seznam_mesecev)
        filter_clan = st.selectbox("👤 Član:", ["Vsi člani"] + sorted(df["clan"].unique().tolist()))

    with fcol2:
        filter_tip = st.selectbox("↕️ Vrsta:", ["Vse", "odhodek", "prihodek"])
        iskanje_besedilo = st.text_input("🔎 Iskanje po opisu ali kategoriji:")

    # Uveljavitev filtrov
    df_filtriran = df.copy()

    if filter_mesec != "Vsi meseci":
        df_filtriran = df_filtriran[df_filtriran["leto_mesec"] == filter_mesec]

    if filter_clan != "Vsi člani":
        df_filtriran = df_filtriran[df_filtriran["clan"] == filter_clan]

    if filter_tip != "Vse":
        df_filtriran = df_filtriran[df_filtriran["tip"] == filter_tip]

    if iskanje_besedilo.strip():
        pojem = iskanje_besedilo.strip().lower()
        df_filtriran = df_filtriran[
            df_filtriran["opis"].fillna("").str.lower().str.contains(pojem) |
            df_filtriran["kategorija"].str.lower().str.contains(pojem)
        ]

    # Finančni povzetek za filtrirane podatke
    prihodki = df_filtriran[df_filtriran["tip"] == "prihodek"]["znesek"].sum()
    odhodki = df_filtriran[df_filtriran["tip"] == "odhodek"]["znesek"].sum()
    saldo = prihodki - odhodki

    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("Prihodki (filter)", f"{prihodki:,.2f} €")
    m2.metric("Odhodki (filter)", f"{odhodki:,.2f} €")
    m3.metric("Saldo (filter)", f"{saldo:,.2f} €")

    # Graf za izbrane odhodke
    odhodki_df = df_filtriran[df_filtriran["tip"] == "odhodek"]
    if not odhodki_df.empty:
        st.write("**Stroški po kategorijah (izbrani zadetki):**")
        graf_podatki = odhodki_df.groupby("kategorija")["znesek"].sum().reset_index()
        st.bar_chart(graf_podatki.set_index("kategorija"))

    # Tabela z zadetki
    st.write(f"**Najdeni vnosi ({len(df_filtriran)}):**")
    st.dataframe(
        df_filtriran[["id", "datum", "clan", "tip", "kategorija", "znesek", "opis"]],
        use_container_width=True
    )

    # 3. Brisanje
    with st.expander("🗑️ Brisanje vnosov"):
        st.write("**Izbriši posamezen vnos po ID:**")
        seznam_id = df["id"].tolist()
        izbran_id = st.selectbox("Izberite ID transakcije", seznam_id)
        
        if st.button("Izbriši izbrani vnos", type="secondary"):
            cursor.execute("DELETE FROM transakcije WHERE id = ?", (izbran_id,))
            conn.commit()
            st.warning(f"Vnos z ID {izbran_id} je bil izbrisan!")
            varno_osvezi()

        st.divider()

        st.write("**Ponastavitev celotne baze:**")
        if st.button("⚠️ Izbriši VSE podatke", type="primary"):
            cursor.execute("DELETE FROM transakcije")
            conn.commit()
            st.error("Vsi podatki so bili izbrisani!")
            varno_osvezi()
else:
    st.info("Baza je trenutno prazna. Dodajte prvi vnos zgoraj.")