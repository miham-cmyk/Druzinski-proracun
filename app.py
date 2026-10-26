import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

# 1. Povezava z bazo podatkov
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

# Nastavitev strani
st.set_page_config(page_title="Družinski Proračun", page_icon="💰", layout="centered")
st.title("💰 Družinski Proračun")

# 2. Obrazec za vnos transakcij
with st.expander("➕ Dodaj nov vnos", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        clan = st.selectbox("Družinski član", ["Miha", "Lana", "Rea", "Oli" ])
        tip = st.radio("Vrsta", ["odhodek", "prihodek"], horizontal=True)
        znesek = st.number_input("Znesek (€)", min_value=0.01, step=1.0)
    with col2:
        kategorije = ["Hrana", "Položnice", "Bencin", "Zabava", "Plača", "Drugo", "Kredit"]
        kategorija = st.selectbox("Kategorija", kategorije)
        opis = st.text_input("Opis (neobvezno)")

    if st.button("Shrani transakcijo", type="primary"):
        cursor.execute("""
            INSERT INTO transakcije (datum, clan, tip, kategorija, znesek, opis)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (date.today().isoformat(), clan, tip, kategorija, znesek, opis))
        conn.commit()
        st.success("Transakcija uspešno shranjena!")
        st.rerun()

# 3. Prikaz podatkov in brisanje
df = pd.read_sql_query("SELECT * FROM transakcije ORDER BY id DESC", conn)

if not df.empty:
    # Seštevki
    prihodki = df[df["tip"] == "prihodek"]["znesek"].sum()
    odhodki = df[df["tip"] == "odhodek"]["znesek"].sum()
    saldo = prihodki - odhodki

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Prihodki", f"{prihodki:,.2f} €")
    col_b.metric("Odhodki", f"{odhodki:,.2f} €")
    col_c.metric("Saldo", f"{saldo:,.2f} €")

    st.subheader("Zgodovina vnosov")
    st.dataframe(df[["id", "datum", "clan", "tip", "kategorija", "znesek", "opis"]], use_container_width=True)

    # Razdelek za brisanje
    with st.expander("🗑️ Brisanje vnosov"):
        st.write("**Izbriši posamezen vnos po ID-ju:**")
        seznam_id = df["id"].tolist()
        izbran_id = st.selectbox("Izberite ID transakcije", seznam_id)
        
        if st.button("Izbriši ta vnos", type="secondary"):
            cursor.execute("DELETE FROM transakcije WHERE id = ?", (izbran_id,))
            conn.commit()
            st.warning(f"Vnos z ID {izbran_id} je bil izbrisan!")
            st.rerun()

        st.divider()

        st.write("**Ponastavitev celotnega proračuna:**")
        if st.button("⚠️ Izbriši VSE podatke", type="primary"):
            cursor.execute("DELETE FROM transakcije")
            conn.commit()
            st.error("Vsi podatki so bili izbrisani!")
            st.rerun()
else:
    st.info("Baza je trenutno prazna. Dodajte prvi vnos zgoraj.")