import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

# Varna osvežitev
def varno_osvezi():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

st.set_page_config(page_title="Družinski Proračun Pro", page_icon="💰", layout="wide")

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

# --- ODJAVA V STRANSKEM MENIJU ---
with st.sidebar:
    st.write("👤 Prijavljeni v proračun")
    if st.button("Odjava"):
        st.session_state.avtenticiran = False
        varno_osvezi()

# --- BAZA PODATKOV ---
conn = sqlite3.connect("druzinski_proracun.db", check_same_thread=False)
cursor = conn.cursor()

# Tabela transakcij
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

# Tabela mesečnih limitov
cursor.execute("""
    CREATE TABLE IF NOT EXISTS limiti (
        kategorija TEXT PRIMARY KEY,
        limit_znesek REAL NOT NULL
    )
""")
conn.commit()

# VAŠI ČLANI IN KATEGORIJE
CLANI = ["Miha", "Lana", "Rea", "Oli"]
KATEGORIJE = ["Hrana", "Položnice", "Bencin", "Zabava", "Plača", "Drugo", "Kredit", "Elektrika Avto"]

st.title("💰 Družinski Proračun Pro")

# --- ZAVIHKI ZA PREGLEDNOST ---
zavihek_vnos, zavihek_pregled, zavihek_limiti, zavihek_uredi = st.tabs([
    "➕ Vnos & Hitri gumbi", 
    "📊 Pregled & Analitika", 
    "🎯 Limiti proračuna", 
    "✏️ Urejanje & Brisanje"
])

# ==========================================
# 1. ZAVIHEK: VNOS IN HITRI GUMBI
# ==========================================
with zavihek_vnos:
    st.subheader("⚡ Hitri vnos z enim klikom")
    st.caption("Takojšnja zabeležba pogostih nakupov za današnji dan:")
    
    qcol1, qcol2, qcol3, qcol4 = st.columns(4)
    with qcol1:
        if st.button("☕ Kava / Pijača (2.00 €)"):
            cursor.execute("INSERT INTO transakcije (datum, clan, tip, kategorija, znesek, opis) VALUES (?, ?, ?, ?, ?, ?)",
                           (date.today().isoformat(), "Miha", "odhodek", "Zabava", 2.00, "Kava"))
            conn.commit()
            st.toast("Zabeleženo: Kava 2 €")
            varno_osvezi()
    with qcol2:
        if st.button("🥪 Malica (10 €)"):
            cursor.execute("INSERT INTO transakcije (datum, clan, tip, kategorija, znesek, opis) VALUES (?, ?, ?, ?, ?, ?)",
                           (date.today().isoformat(), "Miha", "odhodek", "Hrana", 10, "Malica"))
            conn.commit()
            st.toast("Zabeleženo: Malica 10 €")
            varno_osvezi()
    with qcol3:
        if st.button("🛒 Trgovina (30.00 €)"):
            cursor.execute("INSERT INTO transakcije (datum, clan, tip, kategorija, znesek, opis) VALUES (?, ?, ?, ?, ?, ?)",
                           (date.today().isoformat(), "Lana", "odhodek", "Hrana", 30.00, "Trgovina"))
            conn.commit()
            st.toast("Zabeleženo: Trgovina 30 €")
            varno_osvezi()
    with qcol4:
        if st.button("⛽ Bencin / Polnjenje (50.00 €)"):
            cursor.execute("INSERT INTO transakcije (datum, clan, tip, kategorija, znesek, opis) VALUES (?, ?, ?, ?, ?, ?)",
                           (date.today().isoformat(), "Miha", "odhodek", "Bencin", 50.00, "Bencin / Polnjenje"))
            conn.commit()
            st.toast("Zabeleženo: Bencin 50 €")
            varno_osvezi()

    st.divider()

    st.subheader("📝 Običajen vnos")
    with st.form("obrazec_vnos", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            clan = st.selectbox("Družinski član", CLANI)
            tip = st.radio("Vrsta", ["odhodek", "prihodek"], horizontal=True)
            znesek = st.number_input("Znesek (€)", min_value=0.01, step=1.0)
        with col2:
            izbran_datum = st.date_input("Datum transakcije", value=date.today())
            kategorija = st.selectbox("Kategorija", KATEGORIJE)
            opis = st.text_input("Opis transakcije")

        poslji = st.form_submit_button("Shrani vnos", type="primary")
        if poslji:
            cursor.execute("""
                INSERT INTO transakcije (datum, clan, tip, kategorija, znesek, opis)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (izbran_datum.isoformat(), clan, tip, kategorija, znesek, opis))
            conn.commit()
            st.success("Transakcija uspešno shranjena!")
            varno_osvezi()

# ==========================================
# 2. ZAVIHEK: PREGLED, ANALITIKA & IZVOZ
# ==========================================
with zavihek_pregled:
    df = pd.read_sql_query("SELECT * FROM transakcije ORDER BY datum DESC, id DESC", conn)

    if not df.empty:
        df["datum_dt"] = pd.to_datetime(df["datum"])
        df["leto_mesec"] = df["datum_dt"].dt.strftime("%Y-%m")

        # Filtri v vrstici
        f1, f2, f3, f4 = st.columns([1.5, 1.5, 1.5, 2.5])
        with f1:
            seznam_mesecev = ["Vsi meseci"] + sorted(df["leto_mesec"].unique().tolist(), reverse=True)
            filter_mesec = st.selectbox("📅 Mesec:", seznam_mesecev)
        with f2:
            filter_clan = st.selectbox("👤 Član:", ["Vsi člani"] + sorted(df["clan"].unique().tolist()))
        with f3:
            filter_tip = st.selectbox("↕️ Vrsta:", ["Vse", "odhodek", "prihodek"])
        with f4:
            iskanje_tekst = st.text_input("🔎 Iskanje (opis ali kategorija):")

        # Filtriranje tabele
        dff = df.copy()
        if filter_mesec != "Vsi meseci":
            dff = dff[dff["leto_mesec"] == filter_mesec]
        if filter_clan != "Vsi člani":
            dff = dff[dff["clan"] == filter_clan]
        if filter_tip != "Vse":
            dff = dff[dff["tip"] == filter_tip]
        if iskanje_tekst.strip():
            niz = iskanje_tekst.strip().lower()
            dff = dff[dff["opis"].fillna("").str.lower().str.contains(niz) | dff["kategorija"].str.lower().str.contains(niz)]

        # Finančni povzetek
        prihodki = dff[dff["tip"] == "prihodek"]["znesek"].sum()
        odhodki = dff[dff["tip"] == "odhodek"]["znesek"].sum()
        saldo = prihodki - odhodki

        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.metric("Prihodki", f"{prihodki:,.2f} €")
        m2.metric("Odhodki", f"{odhodki:,.2f} €")
        m3.metric("Saldo", f"{saldo:,.2f} €")

        # Prikaz stroškov po kategorijah
        odhodki_df = dff[dff["tip"] == "odhodek"]
        if not odhodki_df.empty:
            st.write("**Stroški po kategorijah:**")
            kat_sum = odhodki_df.groupby("kategorija")["znesek"].sum().reset_index()
            st.bar_chart(kat_sum.set_index("kategorija"))

        st.subheader("Tabela transakcij")
        st.dataframe(dff[["id", "datum", "clan", "tip", "kategorija", "znesek", "opis"]], use_container_width=True)

        # Gumb za prenos podatkov v Excel / CSV
        csv_data = dff.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Prenesi filtrirane podatke v Excel / CSV",
            data=csv_data,
            file_name=f"proracun_{filter_mesec}.csv",
            mime="text/csv"
        )
    else:
        st.info("Baza je prazna. Dodajte prvi vnos v prvem zavihku.")

# ==========================================
# 3. ZAVIHEK: MESEČNI LIMITI & OPOZORILA
# ==========================================
with zavihek_limiti:
    st.subheader("🎯 Mesečni proračunski limiti po kategorijah")
    
    with st.form("obrazec_limiti"):
        lcol1, lcol2 = st.columns(2)
        with lcol1:
            kat_za_limit = st.selectbox("Kategorija za limit", [k for k in KATEGORIJE if k != "Plača"])
        with lcol2:
            znesek_limita = st.number_input("Mesečni limit (€)", min_value=10.0, step=10.0, value=200.0)
        if st.form_submit_button("Shrani limit"):
            cursor.execute("INSERT OR REPLACE INTO limiti (kategorija, limit_znesek) VALUES (?, ?)", (kat_za_limit, znesek_limita))
            conn.commit()
            st.success(f"Limit za {kat_za_limit} nastavljen na {znesek_limita:,.2f} €")
            varno_osvezi()

    # Preverjanje porabe glede na tekoči mesec
    df_lim = pd.read_sql_query("SELECT * FROM limiti", conn)
    if not df_lim.empty:
        trenutni_mesec = date.today().strftime("%Y-%m")
        st.write(f"**Stanje porabe za tekoči mesec ({trenutni_mesec}):**")
        
        cursor.execute("""
            SELECT kategorija, SUM(znesek) FROM transakcije 
            WHERE tip = 'odhodek' AND strftime('%Y-%m', datum) = ?
            GROUP BY kategorija
        """, (trenutni_mesec,))
        poraba_po_kat = dict(cursor.fetchall())

        for _, row in df_lim.iterrows():
            kat = row["kategorija"]
            lim = row["limit_znesek"]
            porabljeno = poraba_po_kat.get(kat, 0.0)
            odstotek = min(porabljeno / lim, 1.0)

            c1, c2 = st.columns([3, 1])
            with c1:
                st.write(f"**{kat}**: {porabljeno:,.2f} € / {lim:,.2f} € ({porabljeno/lim*100:.1f} %)")
                st.progress(odstotek)
            with c2:
                if porabljeno > lim:
                    st.error(f"⚠️ Preseženo za {porabljeno - lim:,.2f} €!")
                elif porabljeno >= 0.8 * lim:
                    st.warning("Opozorilo: Bližate se limitu!")
                else:
                    st.success("V okviru limita")
    else:
        st.info("Nimate še določenih limitov. Nastavite jih zgoraj.")

# ==========================================
# 4. ZAVIHEK: UREJANJE IN BRISANJE
# ==========================================
with zavihek_uredi:
    df_vsi = pd.read_sql_query("SELECT * FROM transakcije ORDER BY id DESC", conn)
    if not df_vsi.empty:
        st.subheader("✏️ Uredi obstoječ vnos")
        seznam_idjev = df_vsi["id"].tolist()
        izbran_id = st.selectbox("Izberite ID vnosa za popravek:", seznam_idjev)
        
        vrstica = df_vsi[df_vsi["id"] == izbran_id].iloc[0]
        
        with st.form("obrazec_uredi"):
            ucol1, ucol2 = st.columns(2)
            with ucol1:
                u_clan = st.selectbox("Član", CLANI, index=CLANI.index(vrstica["clan"]) if vrstica["clan"] in CLANI else 0)
                u_tip = st.radio("Tip", ["odhodek", "prihodek"], index=0 if vrstica["tip"] == "odhodek" else 1, horizontal=True)
                u_znesek = st.number_input("Znesek (€)", value=float(vrstica["znesek"]), step=1.0)
            with ucol2:
                u_datum = st.date_input("Datum", value=pd.to_datetime(vrstica["datum"]).date())
                u_kat = st.selectbox("Kategorija", KATEGORIJE, index=KATEGORIJE.index(vrstica["kategorija"]) if vrstica["kategorija"] in KATEGORIJE else 0)
                u_opis = st.text_input("Opis", value=str(vrstica["opis"]) if pd.notna(vrstica["opis"]) else "")

            if st.form_submit_button("Posodobi vnos"):
                cursor.execute("""
                    UPDATE transakcije 
                    SET datum = ?, clan = ?, tip = ?, kategorija = ?, znesek = ?, opis = ?
                    WHERE id = ?
                """, (u_datum.isoformat(), u_clan, u_tip, u_kat, u_znesek, u_opis, izbran_id))
                conn.commit()
                st.success(f"Vnos ID {izbran_id} je bil uspešno posodobljen!")
                varno_osvezi()

        st.divider()

        st.subheader("🗑️ Brisanje")
        bcol1, bcol2 = st.columns(2)
        with bcol1:
            if st.button("Izbriši izbrani vnos", type="secondary"):
                cursor.execute("DELETE FROM transakcije WHERE id = ?", (izbran_id,))
                conn.commit()
                st.warning(f"Vnos z ID {izbran_id} je bil izbrisan!")
                varno_osvezi()
        with bcol2:
            if st.button("⚠️ Izbriši VSE transakcije", type="primary"):
                cursor.execute("DELETE FROM transakcije")
                conn.commit()
                st.error("Celotna baza je izpraznjena!")
                varno_osvezi()
    else:
        st.info("Baza je prazna.")