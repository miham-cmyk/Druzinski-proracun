import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
import io
import shutil

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

# --- BAZA PODATKOV ---
conn = sqlite3.connect("druzinski_proracun.db", check_same_thread=False)
cursor = conn.cursor()

# Tabele
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

# Privzete vrednosti za člane in kategorije, če je tabela prazna
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

# Dinamično branje članov in kategorij
CLANI = [row[0] for row in cursor.execute("SELECT ime FROM clani_seznam ORDER BY ime").fetchall()]
KATEGORIJE = [row[0] for row in cursor.execute("SELECT ime FROM kategorije_seznam ORDER BY ime").fetchall()]

# --- STRANSKA VRSTICA: ODJAVA, BACKUP & RESTORE ---
with st.sidebar:
    st.write("👤 **Prijavljen uporabnik**")
    if st.button("Odjava", use_container_width=True):
        st.session_state.avtenticiran = False
        varno_osvezi()
    
    st.divider()
    st.subheader("💾 Varnostna kopija")
    
    # Prenos kopije
    with open("druzinski_proracun.db", "rb") as f:
        st.download_button(
            label="Prenesi bazo (.db)",
            data=f.read(),
            file_name=f"backup_proracun_{date.today().isoformat()}.db",
            mime="application/x-sqlite3",
            use_container_width=True
        )

    # Obnova baze (Restore)
    st.write("**Obnovi bazo iz datoteke:**")
    nalozena_baza = st.file_uploader("Naloži .db datoteko", type=["db"])
    if nalozena_baza is not None:
        if st.button("⚠️ Potrdi obnovo baze", type="primary", use_container_width=True):
            conn.close()
            with open("druzinski_proracun.db", "wb") as f:
                f.write(nalozena_baza.getbuffer())
            st.success("Baza je bila uspešno obnovljena!")
            varno_osvezi()

st.title("💰 Družinski Proračun Pro Ultimate")

# --- ZAVIHKI ---
z_vnos, z_pregled, z_letno, z_varcevanje, z_fiksni, z_limiti, z_uredi, z_nastavitve = st.tabs([
    "➕ Vnos & Bližnjice", 
    "📊 Mesec & Iskanje", 
    "📈 Letni pregled",
    "🏦 Varčevanje & Cilji",
    "🔁 Fiksni stroški",
    "🎯 Limiti", 
    "✏️ Urejanje & Brisanje",
    "⚙️ Nastavitve & Uvoz"
])

# ==========================================
# 1. ZAVIHEK: VNOS IN HITRI GUMBI
# ==========================================
with z_vnos:
    st.subheader("⚡ Hitri vnos nakupa za danes")
    q1, q2, q3, q4 = st.columns(4)
    with q1:
        if st.button("☕ Kruh (2.00 €)", use_container_width=True):
            cursor.execute("INSERT INTO transakcije (datum, clan, tip, kategorija, znesek, opis) VALUES (?, ?, ?, ?, ?, ?)",
                           (date.today().isoformat(), "Miha", "odhodek", "Hrana", 2.00, "Kruh"))
            conn.commit()
            st.toast("Zabeleženo: Kruh 2 €")
            varno_osvezi()
    with q2:
        if st.button("🥪 Malica (10 €)", use_container_width=True):
            cursor.execute("INSERT INTO transakcije (datum, clan, tip, kategorija, znesek, opis) VALUES (?, ?, ?, ?, ?, ?)",
                           (date.today().isoformat(), "Miha", "odhodek", "Hrana", 10, "Malica"))
            conn.commit()
            st.toast("Zabeleženo: Malica 10 €")
            varno_osvezi()
    with q3:
        if st.button("🛒 Trgovina (30.00 €)", use_container_width=True):
            cursor.execute("INSERT INTO transakcije (datum, clan, tip, kategorija, znesek, opis) VALUES (?, ?, ?, ?, ?, ?)",
                           (date.today().isoformat(), "Lana", "odhodek", "Hrana", 30.00, "Mercator"))
            conn.commit()
            st.toast("Zabeleženo: Trgovina 30 €")
            varno_osvezi()
    with q4:
        if st.button("⛽ Bencin / Polnjenje (50.00 €)", use_container_width=True):
            cursor.execute("INSERT INTO transakcije (datum, clan, tip, kategorija, znesek, opis) VALUES (?, ?, ?, ?, ?, ?)",
                           (date.today().isoformat(), "Miha", "odhodek", "Bencin", 50.00, "Bencin"))
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

        if st.form_submit_button("Shrani transakcijo", type="primary"):
            cursor.execute("""
                INSERT INTO transakcije (datum, clan, tip, kategorija, znesek, opis)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (izbran_datum.isoformat(), clan, tip, kategorija, znesek, opis))
            conn.commit()
            st.success("Transakcija uspešno shranjena!")
            varno_osvezi()

# ==========================================
# 2. ZAVIHEK: PREGLED, ISKANJE & IZVOZ
# ==========================================
with z_pregled:
    df = pd.read_sql_query("SELECT * FROM transakcije ORDER BY datum DESC, id DESC", conn)
    if not df.empty:
        df["datum_dt"] = pd.to_datetime(df["datum"])
        df["leto_mesec"] = df["datum_dt"].dt.strftime("%Y-%m")

        f1, f2, f3, f4 = st.columns([1.5, 1.5, 1.5, 2.5])
        with f1:
            seznam_mesecev = ["Vsi meseci"] + sorted(df["leto_mesec"].unique().tolist(), reverse=True)
            filter_mesec = st.selectbox("📅 Mesec:", seznam_mesecev)
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
        st.dataframe(dff[["id", "datum", "clan", "tip", "kategorija", "znesek", "opis"]], use_container_width=True)

        st.download_button(
            label="📥 Prenesi podatke v Excel / CSV",
            data=dff.to_csv(index=False).encode('utf-8'),
            file_name=f"proracun_{filter_mesec}.csv",
            mime="text/csv"
        )
    else:
        st.info("Baza je prazna. Dodajte prvi vnos v prvem zavihku.")

# ==========================================
# 3. ZAVIHEK: LETNI PREGLED IN PRIMERJAVA
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

        st.dataframe(pregled_letni.style.format("{:,.2f} €"), use_container_width=True)
        st.write("**Graf gibanja prihodkov in odhodkov skozi mesece:**")
        st.line_chart(pregled_letni[["Prihodki (€)", "Odhodki (€)"]])
    else:
        st.info("Ni še podatkov za letni pregled.")

# ==========================================
# 4. ZAVIHEK: VARČEVANJE & CILJI
# ==========================================
with z_varcevanje:
    st.subheader("🏦 Varčevalni sklad & Cilji varčevanja")
    st.caption("Beležite gotovino in spremljajte napredek do določenih varčevalnih ciljev.")
    
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
                
                st.write(f"🎯 **{cilj_ime}**: {trenutno:,.2f} € od {cilj_znesek:,.2f} € ({procent*100:.1f} %)")
                st.progress(procent)
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
            st.dataframe(df_varc[["datum", "clan", "vrsta", "znesek", "namen"]].head(6), use_container_width=True)
        else:
            st.caption("Ni zabeleženega varčevanja.")

# ==========================================
# 5. ZAVIHEK: PONAVLJAJOČI FIKSNI STROŠKI
# ==========================================
with z_fiksni:
    st.subheader("🔁 Ponavljajoči se fiksni stroški")
    st.caption("Tukaj vnesete mesečne naročnine, položnice in kredite, ki jih nato vsak mesec vnesete z enim klikom.")
    
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
            st.dataframe(df_fiksni[["id", "clan", "kategorija", "znesek", "opis"]], use_container_width=True)
            skupaj_fiksni = df_fiksni["znesek"].sum()
            st.write(f"Vsak mesec skupaj fiksno: **{skupaj_fiksni:,.2f} €**")
            
            st.markdown("---")
            if st.button("🚀 Vnesi vse fiksne stroške v proračun za danes", type="primary"):
                danes_iso = date.today().isoformat()
                for _, r in df_fiksni.iterrows():
                    cursor.execute("""
                        INSERT INTO transakcije (datum, clan, tip, kategorija, znesek, opis)
                        VALUES (?, ?, 'odhodek', ?, ?, ?)
                    """, (danes_iso, r["clan"], r["kategorija"], r["znesek"], f"[Fiksno] {r['opis']}"))
                conn.commit()
                st.success("Vsi fiksni stroški so bili uspešno zabeleženi!")
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
            c1, c2 = st.columns([3, 1])
            with c1:
                st.write(f"**{kat}**: {porabljeno:,.2f} € / {lim:,.2f} € ({porabljeno/lim*100:.1f} %)")
                st.progress(odstotek)
            with c2:
                if porabljeno > lim:
                    st.error(f"⚠️ Preseženo za {porabljeno - lim:,.2f} €!")
                elif porabljeno >= 0.8 * lim:
                    st.warning("Bližate se limitu!")
                else:
                    st.success("V okviru limita")
    else:
        st.info("Nimate še določenih limitov. Nastavite jih zgoraj.")

# ==========================================
# 7. ZAVIHEK: UREJANJE IN BRISANJE
# ==========================================
with z_uredi:
    df_vsi = pd.read_sql_query("SELECT * FROM transakcije ORDER BY id DESC", conn)
    if not df_vsi.empty:
        st.subheader("✏️ Uredi transakcijo")
        seznam_idjev = df_vsi["id"].tolist()
        izbran_id = st.selectbox("Izberite ID transakcije:", seznam_idjev)
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
        st.subheader("🗑️ Brisanje")
        b1, b2 = st.columns(2)
        with b1:
            if st.button("Izbriši izbrani vnos", type="secondary"):
                cursor.execute("DELETE FROM transakcije WHERE id = ?", (izbran_id,))
                conn.commit()
                st.warning(f"Vnos ID {izbran_id} izbrisan!")
                varno_osvezi()
        with b2:
            if st.button("⚠️ Izbriši VSE transakcije", type="primary"):
                cursor.execute("DELETE FROM transakcije")
                conn.commit()
                st.error("Baza je izpraznjena!")
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
        st.dataframe(pd.DataFrame(CLANI, columns=["Član"]), use_container_width=True, hide_index=True)
        
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
        st.dataframe(pd.DataFrame(KATEGORIJE, columns=["Kategorija"]), use_container_width=True, hide_index=True)
        
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
    st.caption("Izvozite mesečni CSV izpisek iz svoje spletne banke in ga naložite spodaj.")

    csv_file = st.file_uploader("Izberite bančno datoteko (CSV)", type=["csv", "txt"])
    
    if csv_file is not None:
        locilo = st.radio("Ločilo v CSV datoteki:", ["; (podpičje)", ", (vejica)"], horizontal=True)
        sep_char = ";" if ";" in locilo else ","
        
        try:
            df_banka = pd.read_csv(csv_file, sep=sep_char)
            st.write("**Predogled naložene datoteke:**")
            st.dataframe(df_banka.head(3), use_container_width=True)

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
                privzeti_clan = st.selectbox("Privzeti član za uvožene transakcije:", CLANI)
            with icol5:
                privzeta_kat = st.selectbox("Privzeta kategorija:", KATEGORIJE)

            if st.button("🚀 Uvozi vse transakcije v proračun", type="primary"):
                uspesno = 0
                for _, row in df_banka.iterrows():
                    try:
                        # Branje in pretvorba zneska
                        surov_znesek = str(row[kol_znesek]).replace("€", "").replace(" ", "").replace(".", "").replace(",", ".")
                        val = float(surov_znesek)
                        
                        tip_tr = "prihodek" if val > 0 else "odhodek"
                        abs_znesek = abs(val)

                        # Branje datuma
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