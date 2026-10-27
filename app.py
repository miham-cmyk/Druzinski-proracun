import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime
import random
import time

# Varna osvežitev
def varno_osvezi():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

st.set_page_config(page_title="Družinski Proračun Pro", page_icon="💰", layout="wide")

# --- PIN ZAŠČITA & AUTO-LOGOUT (15 MINUT) ---
PRAVILNI_PIN = "18122018"
CAS_NEDEJAVNOSTI_SEKUNDE = 15 * 60  # 15 minut

if "avtenticiran" not in st.session_state:
    st.session_state.avtenticiran = False
if "zadnja_aktivnost" not in st.session_state:
    st.session_state.zadnja_aktivnost = time.time()

# Preverjanje poteka seje zaradi nedejavnosti
if st.session_state.avtenticiran:
    trenutni_cas = time.time()
    if trenutni_cas - st.session_state.zadnja_aktivnost > CAS_NEDEJAVNOSTI_SEKUNDE:
        st.session_state.avtenticiran = False
        st.warning("Seja je potekla zaradi 15 minut nedejavnosti. Prosimo, ponovno vnesite PIN.")
    st.session_state.zadnja_aktivnost = trenutni_cas

if not st.session_state.avtenticiran:
    st.title("🔒 Družinski Proračun")
    vnesen_pin = st.text_input("Vnesite PIN za vstop", type="password")
    
    if st.button("Vstopi", type="primary"):
        if vnesen_pin == PRAVILNI_PIN:
            st.session_state.avtenticiran = True
            st.session_state.zadnja_aktivnost = time.time()
            varno_osvezi()
        else:
            st.error("Napačen PIN! Poskusite znova.")
    st.stop()

# --- BAZA PODATKOV ---
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

cursor.execute("""
    CREATE TABLE IF NOT EXISTS limiti (
        kategorija TEXT PRIMARY KEY,
        limit_znesek REAL NOT NULL
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS varcevanje (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        datum TEXT NOT NULL,
        clan TEXT NOT NULL,
        vrsta TEXT NOT NULL,
        znesek REAL NOT NULL,
        namen TEXT
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS varcevalni_cilji (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ime_cilja TEXT UNIQUE NOT NULL,
        ciljni_znesek REAL NOT NULL
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS fiksni_stroski (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        clan TEXT NOT NULL,
        kategorija TEXT NOT NULL,
        znesek REAL NOT NULL,
        opis TEXT NOT NULL
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS clani_seznam (
        ime TEXT PRIMARY KEY
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS kategorije_seznam (
        ime TEXT PRIMARY KEY
    )
""")
conn.commit()

# Privzete vrednosti
cursor.execute("SELECT COUNT(*) FROM clani_seznam")
if cursor.fetchone()[0] == 0:
    for c in ["Miha", "Lana", "Rea", "Oli"]:
        cursor.execute("INSERT OR IGNORE INTO clani_seznam (ime) VALUES (?)", (c,))
    conn.commit()

cursor.execute("SELECT COUNT(*) FROM kategorije_seznam")
if cursor.fetchone()[0] == 0:
    for k in ["Hrana", "Položnice", "Bencin", "Zabava", "Plača", "Drugo", "Kredit", "Elektrika Avto"]:
        cursor.execute("INSERT OR IGNORE INTO kategorije_seznam (ime) VALUES (?)", (k,))
    conn.commit()

CLANI = [row[0] for row in cursor.execute("SELECT ime FROM clani_seznam ORDER BY ime").fetchall()]
KATEGORIJE = [row[0] for row in cursor.execute("SELECT ime FROM kategorije_seznam ORDER BY ime").fetchall()]

# --- LOGIKA ZA REINO IGRO SPOMIN ---
SIMBOLI_SPOMINA = ["🐶", "🐱", "🦄", "🍦", "🍓", "🚀"]

def ponastavi_spomin():
    karte = SIMBOLI_SPOMINA * 2
    random.shuffle(karte)
    st.session_state.spomin_karte = karte
    st.session_state.spomin_odkrite = [False] * len(karte)
    st.session_state.spomin_izbrani = []
    st.session_state.spomin_poskusi = 0
    st.session_state.spomin_caka_zaprtje = False
    if "spomin_zmage" not in st.session_state:
        st.session_state.spomin_zmage = 0

if "spomin_karte" not in st.session_state:
    ponastavi_spomin()

# --- STRANSKA VRSTICA: ODJAVA & BACKUP / RESTORE ---
with st.sidebar:
    st.write("👤 **Prijavljen uporabnik**")
    if st.button("Odjava", width="stretch"):
        st.session_state.avtenticiran = False
        varno_osvezi()
    
    st.divider()
    st.subheader("💾 Varnostna kopija")
    with open("druzinski_proracun.db", "rb") as f:
        st.download_button(
            label="Prenesi bazo (.db)",
            data=f.read(),
            file_name=f"backup_proracun_{date.today().isoformat()}.db",
            mime="application/x-sqlite3",
            width="stretch"
        )

    st.write("**Obnovi bazo:**")
    nalozena_baza = st.file_uploader("Naloži .db datoteko", type=["db"], label_visibility="collapsed")
    if nalozena_baza is not None:
        if st.button("⚠️ Potrdi obnovo baze", type="primary", width="stretch"):
            conn.close()
            with open("druzinski_proracun.db", "wb") as f:
                f.write(nalozena_baza.getbuffer())
            st.success("Baza obnovljena!")
            varno_osvezi()

st.title("💰 Družinski Proračun Pro")

# ==========================================
# PAMETNA OPOZORILA NA VRHU (DASHBOARD ALERT)
# ==========================================
mesec_danes = date.today().strftime("%Y-%m")

# 1. Preverjanje fiksnih stroškov ta mesec
cursor.execute("SELECT COUNT(*) FROM fiksni_stroski")
st_fiksnih = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM transakcije WHERE strftime('%Y-%m', datum) = ? AND opis LIKE '[Fiksno]%'", (mesec_danes,))
st_vnesenih_fiksnih = cursor.fetchone()[0]

# 2. Preverjanje limitov ta mesec
df_lim_check = pd.read_sql_query("SELECT * FROM limiti", conn)
presezeni_limiti = []
opozorilni_limiti = []
if not df_lim_check.empty:
    cursor.execute("SELECT kategorija, SUM(znesek) FROM transakcije WHERE tip = 'odhodek' AND strftime('%Y-%m', datum) = ? GROUP BY kategorija", (mesec_danes,))
    poraba_kat_dict = dict(cursor.fetchall())
    for _, r in df_lim_check.iterrows():
        k = r["kategorija"]
        lim = r["limit_znesek"]
        por = poraba_kat_dict.get(k, 0.0)
        if por > lim:
            presezeni_limiti.append(f"{k} (+{por - lim:,.2f} €)")
        elif por >= 0.85 * lim:
            opozorilni_limiti.append(k)

# Prikaz pametnih obvestil, če obstajajo
if st_fiksnih > 0 and st_vnesenih_fiksnih == 0:
    st.info(f"💡 **Opomnik za fiksne stroške:** Za tekoči mesec ({mesec_danes}) fiksni stroški še niso bili vneseni. Vnesete jih lahko v zavihku *Fiksni stroški*.")

if presezeni_limiti:
    st.error(f"⚠️ **Preseženi limiti v tem mesecu:** {', '.join(presezeni_limiti)}")
elif opozorilni_limiti:
    st.warning(f"⚡ **Bližate se limitu pri:** {', '.join(opozorilni_limiti)}")

# --- ZAVIHKI ---
z_vnos, z_pregled, z_letno, z_varcevanje, z_fiksni, z_limiti, z_uredi, z_nastavitve, z_rea = st.tabs([
    "➕ Vnos transakcije", 
    "📊 Mesec & Iskanje", 
    "📈 Letni pregled",
    "🏦 Varčevanje & Cilji",
    "🔁 Fiksni stroški",
    "🎯 Limiti", 
    "✏️ Urejanje & Brisanje",
    "⚙️ Nastavitve & Uvoz",
    "🎮 Rein Spomin"
])

# ==========================================
# 1. ZAVIHEK: VNOS TRANSAKCIJE
# ==========================================
with z_vnos:
    st.subheader("📝 Vnos nove transakcije")
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

        if st.form_submit_button("Shrani transakcijo", type="primary", width="stretch"):
            cursor.execute("""
                INSERT INTO transakcije (datum, clan, tip, kategorija, znesek, opis)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (izbran_datum.isoformat(), clan, tip, kategorija, znesek, opis))
            conn.commit()
            st.success("Transakcija uspešno shranjena!")
            varno_osvezi()

# ==========================================
# 2. ZAVIHEK: PREGLED, ISKANJE & HITRI FILTRI
# ==========================================
with z_pregled:
    df = pd.read_sql_query("SELECT * FROM transakcije ORDER BY datum DESC, id DESC", conn)
    if not df.empty:
        df["datum_dt"] = pd.to_datetime(df["datum"])
        df["leto_mesec"] = df["datum_dt"].dt.strftime("%Y-%m")

        # Stanje izbranega meseca v seji za hitre gumbe
        if "izbran_filter_mesec" not in st.session_state:
            st.session_state.izbran_filter_mesec = mesec_danes

        # Hitri gumbi za mesece
        st.write("**Hitri izbor obdobja:**")
        hf1, hf2, hf3, _ = st.columns([1, 1, 1, 3])
        with hf1:
            if st.button("📅 Tekoči mesec", width="stretch"):
                st.session_state.izbran_filter_mesec = mesec_danes
                varno_osvezi()
        with hf2:
            # Izračun prejšnjega meseca
            prvi_dan_tega = date.today().replace(day=1)
            prejsnji_mesec = (prvi_dan_tega - pd.DateOffset(days=1)).strftime("%Y-%m")
            if st.button("⏪ Prejšnji mesec", width="stretch"):
                st.session_state.izbran_filter_mesec = prejsnji_mesec
                varno_osvezi()
        with hf3:
            if st.button("🌐 Vsi meseci", width="stretch"):
                st.session_state.izbran_filter_mesec = "Vsi meseci"
                varno_osvezi()

        f1, f2, f3, f4 = st.columns([1.5, 1.5, 1.5, 2.5])
        with f1:
            seznam_mesecev = ["Vsi meseci"] + sorted(df["leto_mesec"].unique().tolist(), reverse=True)
            privzeti_idx = seznam_mesecev.index(st.session_state.izbran_filter_mesec) if st.session_state.izbran_filter_mesec in seznam_mesecev else 0
            filter_mesec = st.selectbox("Izbran mesec:", seznam_mesecev, index=privzeti_idx)
        with f2:
            filter_clan = st.selectbox("👤 Član:", ["Vsi člani"] + sorted(df["clan"].unique().tolist()))
        with f3:
            filter_tip = st.selectbox("↕️ Vrsta:", ["Vse", "odhodek", "prihodek"])
        with f4:
            iskanje_tekst = st.text_input("🔎 Iskanje:")

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

        prihodki = dff[dff["tip"] == "prihodek"]["znesek"].sum()
        odhodki = dff[dff["tip"] == "odhodek"]["znesek"].sum()
        saldo = prihodki - odhodki

        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.metric("Prihodki", f"{prihodki:,.2f} €")
        m2.metric("Odhodki", f"{odhodki:,.2f} €")
        m3.metric("Saldo", f"{saldo:,.2f} €")

        odhodki_df = dff[dff["tip"] == "odhodek"]
        if not odhodki_df.empty:
            st.write("**Stroški po kategorijah:**")
            kat_sum = odhodki_df.groupby("kategorija")["znesek"].sum().reset_index()
            st.bar_chart(kat_sum.set_index("kategorija"))

        st.subheader("Tabela transakcij")
        st.dataframe(dff[["id", "datum", "clan", "tip", "kategorija", "znesek", "opis"]], width="stretch")

        col_izvoz, col_brisanje_hitro = st.columns([1, 1])
        with col_izvoz:
            st.download_button(
                label="📥 Prenesi podatke v CSV",
                data=dff.to_csv(index=False).encode('utf-8'),
                file_name=f"proracun_{filter_mesec}.csv",
                mime="text/csv",
                width="stretch"
            )
        with col_brisanje_hitro:
            with st.expander("🗑️ Hitri izbris transakcije"):
                mozni_id = dff["id"].tolist()
                if mozni_id:
                    izbran_id_del = st.selectbox("Izberite ID za izbris:", mozni_id, key="del_hitro_id")
                    if st.button("Izbriši izbrani vnos", key="btn_del_hitro", type="secondary"):
                        cursor.execute("DELETE FROM transakcije WHERE id = ?", (izbran_id_del,))
                        conn.commit()
                        st.warning(f"Transakcija {izbran_id_del} je bila izbrisana!")
                        varno_osvezi()
    else:
        st.info("Baza je prazna. Dodajte prvi vnos v prvem zavihku.")

# ==========================================
# 3. ZAVIHEK: LETNI PREGLED
# ==========================================
with z_letno:
    st.subheader("📈 Letna primerjava po mesecih")
    df_letno = pd.read_sql_query("SELECT * FROM transakcije", conn)
    if not df_letno.empty:
        df_letno["datum_dt"] = pd.to_datetime(df_letno["datum"])
        df_letno["mesec"] = df_letno["datum_dt"].dt.strftime("%Y-%m")

        pivot_prihodki = df_letno[df_letno["tip"] == "prihodek"].groupby("mesec")["znesek"].sum()
        pivot_odhodki = df_letno[df_letno["tip"] == "odhodek"].groupby("mesec")["znesek"].sum()

        pregled_letni = pd.DataFrame({"Prihodki (€)": pivot_prihodki, "Odhodki (€)": pivot_odhodki}).fillna(0)
        pregled_letni["Saldo (€)"] = pregled_letni["Prihodki (€)"] - pregled_letni["Odhodki (€)"]
        pregled_letni = pregled_letni.sort_index(ascending=False)

        st.dataframe(pregled_letni.style.format("{:,.2f} €"), width="stretch")
        st.write("**Graf gibanja prihodkov in odhodkov skozi mesece:**")
        st.line_chart(pregled_letni[["Prihodki (€)", "Odhodki (€)"]])
    else:
        st.info("Ni še podatkov za letni pregled.")

# ==========================================
# 4. ZAVIHEK: VARČEVANJE & CILJI
# ==========================================
with z_varcevanje:
    st.subheader("🏦 Varčevalni sklad & Cilji varčevanja")
    
    col_c1, col_c2 = st.columns([1, 2])
    with col_c1:
        st.write("**Dodaj nov varčevalni cilj:**")
        with st.form("obrazec_cilj", clear_on_submit=True):
            ime_c = st.text_input("Ime cilja (npr. Dopust, Rezerva):")
            znesek_c = st.number_input("Ciljni znesek (€):", min_value=50.0, step=50.0, value=1000.0)
            if st.form_submit_button("Dodaj cilj"):
                if ime_c.strip():
                    try:
                        cursor.execute("INSERT INTO varcevalni_cilji (ime_cilja, ciljni_znesek) VALUES (?, ?)", (ime_c.strip(), znesek_c))
                        conn.commit()
                        st.success(f"Cilj {ime_c} dodan!")
                        varno_osvezi()
                    except:
                        st.error("Cilj s tem imenom že obstaja!")
    
    with col_c2:
        st.write("**Sledenje napredku ciljev:**")
        df_cilji = pd.read_sql_query("SELECT * FROM varcevalni_cilji", conn)
        df_varc = pd.read_sql_query("SELECT * FROM varcevanje", conn)

        if not df_cilji.empty and not df_varc.empty:
            for _, r in df_cilji.iterrows():
                cilj_ime = r["ime_cilja"]
                cilj_znesek = r["ciljni_znesek"]
                
                pol = df_varc[(df_varc["vrsta"] == "Polog v varčevanje") & (df_varc["namen"] == cilj_ime)]["znesek"].sum()
                por = df_varc[(df_varc["vrsta"] == "Poraba iz varčevanja") & (df_varc["namen"] == cilj_ime)]["znesek"].sum()
                trenutno = pol - por
                procent = min(max(trenutno / cilj_znesek, 0.0), 1.0)
                
                c_lbl, c_del_btn = st.columns([4, 1])
                with c_lbl:
                    st.write(f"🎯 **{cilj_ime}**: {trenutno:,.2f} € od {cilj_znesek:,.2f} € ({procent*100:.1f} %)")
                    st.progress(procent)
                with c_del_btn:
                    if st.button("Briši cilj", key=f"del_cilj_{cilj_ime}"):
                        cursor.execute("DELETE FROM varcevalni_cilji WHERE ime_cilja = ?", (cilj_ime,))
                        conn.commit()
                        st.warning(f"Cilj {cilj_ime} izbrisan!")
                        varno_osvezi()
        else:
            st.caption("Za sledenje ciljem izberite ime cilja v spodnjem obrazcu pri varčevanju.")

    st.divider()

    vcol1, vcol2 = st.columns(2)
    with vcol1:
        st.write("**➕ Zabeleži polog / dvig gotovine:**")
        with st.form("obrazec_varcevanje", clear_on_submit=True):
            v_clan = st.selectbox("Kdo:", CLANI)
            v_vrsta = st.radio("Dejanje:", ["Polog v varčevanje", "Poraba iz varčevanja"], horizontal=True)
            v_znesek = st.number_input("Znesek (€):", min_value=1.0, step=5.0, value=50.0)
            v_datum = st.date_input("Datum:", value=date.today())
            
            seznam_ciljev = ["Poljubno / Splošno"] + (df_cilji["ime_cilja"].tolist() if not df_cilji.empty else [])
            izb_cilj = st.selectbox("Poveži s ciljem (neobvezno):", seznam_ciljev)
            v_namen_tekst = st.text_input("Namen (če ni izbran cilj zgoraj):")
            koncni_namen = izb_cilj if izb_cilj != "Poljubno / Splošno" else v_namen_tekst

            if st.form_submit_button("Shrani v varčevanje", type="primary"):
                cursor.execute("""
                    INSERT INTO varcevanje (datum, clan, vrsta, znesek, namen)
                    VALUES (?, ?, ?, ?, ?)
                """, (v_datum.isoformat(), v_clan, v_vrsta, v_znesek, koncni_namen))
                conn.commit()
                st.success("Zabeleženo v varčevalni sklad!")
                varno_osvezi()

    with vcol2:
        st.write("**📊 Stanje prihrankov:**")
        if not df_varc.empty:
            pol_vsi = df_varc[df_varc["vrsta"] == "Polog v varčevanje"]["znesek"].sum()
            por_vsi = df_varc[df_varc["vrsta"] == "Poraba iz varčevanja"]["znesek"].sum()
            st.metric("Skupaj v prihrankih", f"{pol_vsi - por_vsi:,.2f} €")
            st.dataframe(df_varc[["id", "datum", "clan", "vrsta", "znesek", "namen"]], width="stretch")

            with st.expander("🗑️ Izbriši vnos iz varčevanja"):
                v_izb_del = st.selectbox("Izberite ID varčevanja:", df_varc["id"].tolist(), key="del_varc_id")
                if st.button("Izbriši ta zapis varčevanja"):
                    cursor.execute("DELETE FROM varcevanje WHERE id = ?", (v_izb_del,))
                    conn.commit()
                    st.warning("Zapis varčevanja izbrisan!")
                    varno_osvezi()
        else:
            st.caption("Ni zabeleženega varčevanja.")

# ==========================================
# 5. ZAVIHEK: PONAVLJAJOČI FIKSNI STROŠKI
# ==========================================
with z_fiksni:
    st.subheader("🔁 Ponavljajoči se fiksni stroški")
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        st.write("**Dodaj nov fiksen strošek:**")
        with st.form("obrazec_fiksni", clear_on_submit=True):
            f_clan = st.selectbox("Kdo plačuje:", CLANI)
            f_kat = st.selectbox("Kategorija:", KATEGORIJE)
            f_znesek = st.number_input("Mesečni znesek (€):", min_value=1.0, step=5.0)
            f_opis = st.text_input("Opis (npr. Kredit hiša, Položnica elektrika):")
            
            if st.form_submit_button("Dodaj na seznam"):
                if f_opis.strip():
                    cursor.execute("INSERT INTO fiksni_stroski (clan, kategorija, znesek, opis) VALUES (?, ?, ?, ?)",
                                   (f_clan, f_kat, f_znesek, f_opis.strip()))
                    conn.commit()
                    st.success("Dodan na seznam!")
                    varno_osvezi()

    with col_f2:
        df_fiksni = pd.read_sql_query("SELECT * FROM fiksni_stroski", conn)
        st.write("**Seznam fiksnih mesečnih stroškov:**")
        if not df_fiksni.empty:
            st.dataframe(df_fiksni[["id", "clan", "kategorija", "znesek", "opis"]], width="stretch")
            skupaj_fiksni = df_fiksni["znesek"].sum()
            st.write(f"Vsak mesec skupaj fiksno: **{skupaj_fiksni:,.2f} €**")
            
            c_f_vnesi, c_f_del = st.columns([1.5, 1])
            with c_f_vnesi:
                if st.button("🚀 Vnesi vse fiksne stroške v proračun za danes", type="primary", width="stretch"):
                    danes_iso = date.today().isoformat()
                    for _, r in df_fiksni.iterrows():
                        cursor.execute("""
                            INSERT INTO transakcije (datum, clan, tip, kategorija, znesek, opis)
                            VALUES (?, ?, 'odhodek', ?, ?, ?)
                        """, (danes_iso, r["clan"], r["kategorija"], r["znesek"], f"[Fiksno] {r['opis']}"))
                    conn.commit()
                    st.success("Vsi fiksni stroški zabeleženi!")
                    varno_osvezi()
            with c_f_del:
                with st.expander("🗑️ Odstrani fiksen strošek"):
                    izb_f_del = st.selectbox("Izberite ID stroška:", df_fiksni["id"].tolist(), key="del_fiks_id")
                    if st.button("Odstrani ta strošek"):
                        cursor.execute("DELETE FROM fiksni_stroski WHERE id = ?", (izb_f_del,))
                        conn.commit()
                        st.warning("Fiksni strošek odstranjen!")
                        varno_osvezi()
        else:
            st.info("Nimate še shranjenih ponavljajočih se stroškov.")

# ==========================================
# 6. ZAVIHEK: LIMITI PRORAČUNA
# ==========================================
with z_limiti:
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

    df_lim = pd.read_sql_query("SELECT * FROM limiti", conn)
    if not df_lim.empty:
        trenutni_mesec = date.today().strftime("%Y-%m")
        st.write(f"**Stanje porabe za tekoči mesec ({trenutni_mesec}):**")
        cursor.execute("SELECT kategorija, SUM(znesek) FROM transakcije WHERE tip = 'odhodek' AND strftime('%Y-%m', datum) = ? GROUP BY kategorija", (trenutni_mesec,))
        poraba_po_kat = dict(cursor.fetchall())

        for _, row in df_lim.iterrows():
            kat = row["kategorija"]
            lim = row["limit_znesek"]
            porabljeno = poraba_po_kat.get(kat, 0.0)
            odstotek = min(porabljeno / lim, 1.0)
            c1, c2, c3 = st.columns([3, 1, 0.5])
            with c1:
                st.write(f"**{kat}**: {porabljeno:,.2f} € / {lim:,.2f} € ({porabljeno/lim*100:.1f} %)")
                st.progress(odstotek)
            with c2:
                if porabljeno > lim:
                    st.error(f"Preseženo za {porabljeno - lim:,.2f} €!")
                elif porabljeno >= 0.8 * lim:
                    st.warning("Bližate se limitu!")
                else:
                    st.success("V okviru limita")
            with c3:
                if st.button("Briši", key=f"del_lim_{kat}"):
                    cursor.execute("DELETE FROM limiti WHERE kategorija = ?", (kat,))
                    conn.commit()
                    st.warning(f"Limit za {kat} izbrisan!")
                    varno_osvezi()
    else:
        st.info("Nimate še določenih limitov.")

# ==========================================
# 7. ZAVIHEK: UREJANJE IN POPOLN IZBRIS
# ==========================================
with z_uredi:
    df_vsi = pd.read_sql_query("SELECT * FROM transakcije ORDER BY id DESC", conn)
    if not df_vsi.empty:
        st.subheader("✏️ Uredi obstoječo transakcijo")
        seznam_idjev = df_vsi["id"].tolist()
        izbran_id = st.selectbox("Izberite ID transakcije za popravek:", seznam_idjev, key="edit_sel_id")
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
                    UPDATE transakcije SET datum=?, clan=?, tip=?, kategorija=?, znesek=?, opis=? WHERE id=?
                """, (u_datum.isoformat(), u_clan, u_tip, u_kat, u_znesek, u_opis, izbran_id))
                conn.commit()
                st.success("Posodobljeno!")
                varno_osvezi()

        st.divider()
        st.subheader("🗑️ Brisanje vnosov")
        b1, b2 = st.columns(2)
        with b1:
            st.write("**Izbriši izbrani vnos zgoraj:**")
            if st.button(f"Izbriši vnos ID {izbran_id}", type="secondary", width="stretch"):
                cursor.execute("DELETE FROM transakcije WHERE id = ?", (izbran_id,))
                conn.commit()
                st.warning(f"Vnos ID {izbran_id} je bil izbrisan!")
                varno_osvezi()
        with b2:
            st.write("**Ponastavitev celotne baze transakcij:**")
            if st.button("⚠️ Izbriši VSE transakcije", type="primary", width="stretch"):
                cursor.execute("DELETE FROM transakcije")
                conn.commit()
                st.error("Vse transakcije so bile izbrisane!")
                varno_osvezi()
    else:
        st.info("Baza je prazna.")

# ==========================================
# 8. ZAVIHEK: NASTAVITVE & UVOZ BANČNEGA IZPISKA
# ==========================================
with z_nastavitve:
    st.subheader("⚙️ Upravljanje članov in kategorij")
    
    ncol1, ncol2 = st.columns(2)
    with ncol1:
        st.write("**Družinski člani:**")
        st.dataframe(pd.DataFrame(CLANI, columns=["Član"]), width="stretch", hide_index=True)
        
        with st.form("dodaj_clana_form", clear_on_submit=True):
            nov_clan = st.text_input("Novo ime člana:")
            if st.form_submit_button("Dodaj člana"):
                if nov_clan.strip():
                    cursor.execute("INSERT OR IGNORE INTO clani_seznam (ime) VALUES (?)", (nov_clan.strip(),))
                    conn.commit()
                    st.success(f"Član {nov_clan} dodan!")
                    varno_osvezi()
        
        if len(CLANI) > 1:
            clan_za_izbris = st.selectbox("Odstrani člana:", CLANI)
            if st.button("Odstrani izbranega člana", type="secondary"):
                cursor.execute("DELETE FROM clani_seznam WHERE ime = ?", (clan_za_izbris,))
                conn.commit()
                st.warning(f"Član {clan_za_izbris} odstranjen!")
                varno_osvezi()

    with ncol2:
        st.write("**Kategorije:**")
        st.dataframe(pd.DataFrame(KATEGORIJE, columns=["Kategorija"]), width="stretch", hide_index=True)
        
        with st.form("dodaj_kat_form", clear_on_submit=True):
            nova_kat = st.text_input("Nova kategorija:")
            if st.form_submit_button("Dodaj kategorijo"):
                if nova_kat.strip():
                    cursor.execute("INSERT OR IGNORE INTO kategorije_seznam (ime) VALUES (?)", (nova_kat.strip(),))
                    conn.commit()
                    st.success(f"Kategorija {nova_kat} dodana!")
                    varno_osvezi()
        
        if len(KATEGORIJE) > 1:
            kat_za_izbris = st.selectbox("Odstrani kategorijo:", KATEGORIJE)
            if st.button("Odstrani izbrano kategorijo", type="secondary"):
                cursor.execute("DELETE FROM kategorije_seznam WHERE ime = ?", (kat_za_izbris,))
                conn.commit()
                st.warning(f"Kategorija {kat_za_izbris} odstranjena!")
                varno_osvezi()

    st.divider()

    st.subheader("📥 Uvoz bančnega izpiska (CSV)")
    st.caption("Izvozite CSV izpisek iz svoje spletne banke in ga naložite spodaj.")

    csv_file = st.file_uploader("Izberite bančno datoteko (CSV)", type=["csv", "txt"])
    
    if csv_file is not None:
        locilo = st.radio("Ločilo v CSV datoteki:", ["; (podpičje)", ", (vejica)"], horizontal=True)
        sep_char = ";" if ";" in locilo else ","
        
        try:
            df_banka = pd.read_csv(csv_file, sep=sep_char)
            st.write("**Predogled naložene datoteke:**")
            st.dataframe(df_banka.head(3), width="stretch")

            st.write("**Povežite stolpce bančnega izpiska:**")
            vsi_stolpci = df_banka.columns.tolist()

            icol1, icol2, icol3 = st.columns(3)
            with icol1:
                kol_datum = st.selectbox("Stolpec za datum:", vsi_stolpci)
            with icol2:
                kol_opis = st.selectbox("Stolpec za opis / prejemnika:", vsi_stolpci)
            with icol3:
                kol_znesek = st.selectbox("Stolpec za znesek:", vsi_stolpci)

            icol4, icol5 = st.columns(2)
            with icol4:
                privzeti_clan = st.selectbox("Privzeti član za transakcije:", CLANI)
            with icol5:
                privzeta_kat = st.selectbox("Privzeta kategorija:", KATEGORIJE)

            if st.button("🚀 Uvozi vse transakcije v proračun", type="primary"):
                uspesno = 0
                for _, row in df_banka.iterrows():
                    try:
                        surov_znesek = str(row[kol_znesek]).replace("€", "").replace(" ", "").replace(".", "").replace(",", ".")
                        val = float(surov_znesek)
                        tip_tr = "prihodek" if val > 0 else "odhodek"
                        abs_znesek = abs(val)

                        datum_tr = pd.to_datetime(row[kol_datum], errors="coerce")
                        datum_str = datum_tr.strftime("%Y-%m-%d") if pd.notna(datum_tr) else date.today().isoformat()
                        opis_tr = str(row[kol_opis])[:100]

                        cursor.execute("""
                            INSERT INTO transakcije (datum, clan, tip, kategorija, znesek, opis)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (datum_str, privzeti_clan, tip_tr, privzeta_kat, abs_znesek, f"[Banka] {opis_tr}"))
                        uspesno += 1
                    except Exception:
                        continue

                conn.commit()
                st.success(f"Uspešno uvoženih {uspesno} transakcij!")
                varno_osvezi()
        except Exception as e:
            st.error(f"Napaka pri branju datoteke: {e}")

# ==========================================
# 9. ZAVIHEK: REIN SPOMIN (Z VELIKIMI KARTICAMI)
# ==========================================
with z_rea:
    st.subheader("🧠 Rein Spomin (Memory Game)")
    st.caption("Klikni na karto, poglej sličico in poišči njen par!")

    st.markdown("""
        <style>
        .rea-karta-prazna button {
            height: 110px !important;
            border-radius: 14px !important;
            border: 2px solid #3b82f6 !important;
            background-color: #1e293b !important;
            font-size: 2.8rem !important;
            color: #60a5fa !important;
        }
        .rea-karta-odkrita {
            height: 110px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 4rem;
            background: linear-gradient(135deg, #f3e8ff 0%, #e9d5ff 100%);
            border: 3px solid #a855f7;
            border-radius: 14px;
            margin-bottom: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        </style>
    """, unsafe_allow_html=True)

    if len(st.session_state.spomin_izbrani) == 2:
        idx1, idx2 = st.session_state.spomin_izbrani
        karta1 = st.session_state.spomin_karte[idx1]
        karta2 = st.session_state.spomin_karte[idx2]

        if karta1 == karta2:
            st.session_state.spomin_odkrite[idx1] = True
            st.session_state.spomin_odkrite[idx2] = True
            st.session_state.spomin_izbrani = []
            st.session_state.spomin_poskusi += 1
            st.toast(f"Čudovito! Našla si par {karta1}! 🎉")
            varno_osvezi()
        else:
            st.session_state.spomin_caka_zaprtje = True

    m_col1, m_col2, m_col3 = st.columns(3)
    m_col1.metric("Število poskusov", st.session_state.spomin_poskusi)
    najdeni_pari = sum(st.session_state.spomin_odkrite) // 2
    m_col2.metric("Najdeni pari", f"{najdeni_pari} / {len(SIMBOLI_SPOMINA)}")
    m_col3.metric("Osvojene zvezdice ⭐", st.session_state.spomin_zmage)

    if st.session_state.spomin_caka_zaprtje:
        st.warning("Kartici se ne ujemata! Dobro si ju oglej in klikni spodnji gumb:")
        if st.button("➡️ Nadaljuj z igro", type="primary", width="stretch"):
            st.session_state.spomin_poskusi += 1
            st.session_state.spomin_izbrani = []
            st.session_state.spomin_caka_zaprtje = False
            varno_osvezi()

    st.write("---")

    for r in range(4):
        cols = st.columns(3)
        for c in range(3):
            idx = r * 3 + c
            with cols[c]:
                je_odkrita = st.session_state.spomin_odkrite[idx]
                je_izbrana = idx in st.session_state.spomin_izbrani
                simbol = st.session_state.spomin_karte[idx]

                if je_odkrita or je_izbrana:
                    st.markdown(f'<div class="rea-karta-odkrita">{simbol}</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="rea-karta-prazna">', unsafe_allow_html=True)
                    if st.button("❓", key=f"k_{idx}", width="stretch", disabled=st.session_state.spomin_caka_zaprtje):
                        if len(st.session_state.spomin_izbrani) < 2:
                            st.session_state.spomin_izbrani.append(idx)
                            varno_osvezi()
                    st.markdown('</div>', unsafe_allow_html=True)

    if all(st.session_state.spomin_odkrite):
        st.balloons()
        st.success(f"🎉 BRAVO REA! Čestitke, odkrila si vse pare v {st.session_state.spomin_poskusi} poskusih!")
        if st.button("⭐ Shrani zvezdico in igraj znova", type="primary", width="stretch"):
            st.session_state.spomin_zmage += 1
            ponastavi_spomin()
            varno_osvezi()

    st.write("---")
    if st.button("🔄 Nova igra (Premešaj)", type="secondary"):
        ponastavi_spomin()
        varno_osvezi()