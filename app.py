import streamlit as st
import pandas as pd
from datetime import date
import random
import time
from supabase import create_client, Client

# Varna osvežitev
def varno_osvezi():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

st.set_page_config(page_title="Družinski Proračun Pro", page_icon="💰", layout="wide")

# --- MOBILNA ŠTEVILČNICA & AUTO-LOGOUT ---
PRAVILNI_PIN = "18122018"
CAS_NEDEJAVNOSTI_SEKUNDE = 15 * 60

if "avtenticiran" not in st.session_state:
    st.session_state.avtenticiran = False
if "zadnja_aktivnost" not in st.session_state:
    st.session_state.zadnja_aktivnost = time.time()
if "vnos_pin_buffer" not in st.session_state:
    st.session_state.vnos_pin_buffer = ""

if st.session_state.avtenticiran:
    trenutni_cas = time.time()
    if trenutni_cas - st.session_state.zadnja_aktivnost > CAS_NEDEJAVNOSTI_SEKUNDE:
        st.session_state.avtenticiran = False
        st.warning("Seja je potekla zaradi 15 minut nedejavnosti. Prosimo, ponovno vnesite PIN.")
    st.session_state.zadnja_aktivnost = trenutni_cas

if not st.session_state.avtenticiran:
    # Ključni CSS, ki prepreči zlaganje stolpcev na mobilnih napravah
    st.markdown("""
        <style>
        /* Prisili vodoravno postavitev 3 stolpcev na vseh napravah */
        div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: 10px !important;
            max-width: 330px !important;
            margin: 0 auto 10px auto !important;
        }

        div[data-testid="stHorizontalBlock"] > div {
            flex: 1 1 0px !important;
            min-width: 0 !important;
        }

        /* Oblikovanje gumbov številčnice */
        div[data-testid="stHorizontalBlock"] button {
            height: 64px !important;
            font-size: 1.8rem !important;
            font-weight: 600 !important;
            border-radius: 16px !important;
            border: 1px solid #334155 !important;
            background-color: #1e293b !important;
            color: #f8fafc !important;
            box-shadow: 0 3px 6px rgba(0,0,0,0.18) !important;
        }

        div[data-testid="stHorizontalBlock"] button:active {
            transform: scale(0.95);
            background-color: #2563eb !important;
        }

        /* Zaslonček za prikaz PIN pikic */
        .pin-zaslon {
            text-align: center;
            font-size: 2.2rem;
            letter-spacing: 8px;
            padding: 12px;
            background: #0f172a;
            border: 2px solid #3b82f6;
            border-radius: 16px;
            color: #60a5fa;
            margin: 10px auto 20px auto;
            max-width: 330px;
            min-height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h3 style='text-align: center; margin-bottom: 0;'>🔒 Družinski Proračun</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 0.9rem;'>Vnesite PIN za vstop</p>", unsafe_allow_html=True)

    # Zaslonček s pikicami
    prikaz_pin = "●" * len(st.session_state.vnos_pin_buffer) if st.session_state.vnos_pin_buffer else "· · · · · · · ·"
    st.markdown(f'<div class="pin-zaslon">{prikaz_pin}</div>', unsafe_allow_html=True)

    # Preverjanje vnosa
    if len(st.session_state.vnos_pin_buffer) == len(PRAVILNI_PIN):
        if st.session_state.vnos_pin_buffer == PRAVILNI_PIN:
            st.session_state.avtenticiran = True
            st.session_state.zadnja_aktivnost = time.time()
            st.session_state.vnos_pin_buffer = ""
            varno_osvezi()
        else:
            st.error("Napačen PIN!")
            st.session_state.vnos_pin_buffer = ""
            time.sleep(0.5)
            varno_osvezi()

    # Mreža 4x3 gumbov
    vrstice = [
        ["1", "2", "3"],
        ["4", "5", "6"],
        ["7", "8", "9"],
        ["C", "0", "⌫"]
    ]

    for vrstica in vrstice:
        c1, c2, c3 = st.columns(3)
        for col, znak in zip([c1, c2, c3], vrstica):
            with col:
                if znak == "C":
                    if st.button("C", key="btn_pocisti", width="stretch"):
                        st.session_state.vnos_pin_buffer = ""
                        varno_osvezi()
                elif znak == "⌫":
                    if st.button("⌫", key="btn_brisi", width="stretch"):
                        st.session_state.vnos_pin_buffer = st.session_state.vnos_pin_buffer[:-1]
                        varno_osvezi()
                else:
                    if st.button(znak, key=f"numpad_{znak}", width="stretch"):
                        if len(st.session_state.vnos_pin_buffer) < len(PRAVILNI_PIN):
                            st.session_state.vnos_pin_buffer += znak
                            varno_osvezi()

    st.stop()

# --- SUPABASE POVEZAVA ---
@st.cache_resource
def init_supabase() -> Client:
    url = "https://hvgwewvlagozqfbxwjdm.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh2Z3dld3ZsYWdvenFmYnh3amRtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTMxNzE5MTgsImV4cCI6MjEwODc0NzkxOH0.xYigE2z3iWFkYR-a3PVDIoax490wrp1wN20DAo_cHvk"
    return create_client(url, key)

supabase = init_supabase()

# Pomožne funkcije za branje tabel v DataFrame
def nalozi_podatke(tabela: str, order_col: str = "id", asc: bool = False) -> pd.DataFrame:
    try:
        res = supabase.table(tabela).select("*").order(order_col, desc=not asc).execute()
        if res.data:
            return pd.DataFrame(res.data)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# Preverjanje privzetih članov in kategorij
df_clani_db = nalozi_podatke("clani_seznam", "ime", asc=True)
if df_clani_db.empty:
    for c in ["Miha", "Lana", "Rea", "Oli"]:
        try:
            supabase.table("clani_seznam").insert({"ime": c}).execute()
        except Exception:
            pass
    df_clani_db = nalozi_podatke("clani_seznam", "ime", asc=True)

df_kat_db = nalozi_podatke("kategorije_seznam", "ime", asc=True)
if df_kat_db.empty:
    for k in ["Hrana", "Položnice", "Bencin", "Zabava", "Plača", "Drugo", "Kredit", "Elektrika Avto"]:
        try:
            supabase.table("kategorije_seznam").insert({"ime": k}).execute()
        except Exception:
            pass
    df_kat_db = nalozi_podatke("kategorije_seznam", "ime", asc=True)

CLANI = df_clani_db["ime"].tolist() if not df_clani_db.empty else ["Miha", "Lana", "Rea", "Oli"]
KATEGORIJE = df_kat_db["ime"].tolist() if not df_kat_db.empty else ["Hrana", "Položnice", "Bencin", "Zabava", "Plača"]

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

# --- STRANSKA VRSTICA ---
with st.sidebar:
    st.write("👤 **Prijavljen uporabnik**")
    if st.button("Odjava", width="stretch"):
        st.session_state.avtenticiran = False
        varno_osvezi()
    
    st.divider()
    st.caption("☁️ Baza: Supabase Cloud (trajno shranjeno)")

st.title("💰 Družinski Proračun Pro")

# ==========================================
# PAMETNA OPOZORILA NA VRHU (DASHBOARD ALERT)
# ==========================================
mesec_danes = date.today().strftime("%Y-%m")

df_vse_tr = nalozi_podatke("transakcije", "datum", asc=False)
df_vsi_fiksni = nalozi_podatke("fiksni_stroski", "id", asc=True)
df_lim_check = nalozi_podatke("limiti", "kategorija", asc=True)

st_fiksnih = len(df_vsi_fiksni)
st_vnesenih_fiksnih = 0

if not df_vse_tr.empty:
    df_vse_tr["znesek"] = pd.to_numeric(df_vse_tr["znesek"], errors="coerce").fillna(0.0)
    df_vse_tr["datum_dt"] = pd.to_datetime(df_vse_tr["datum"])
    df_vse_tr["leto_mesec"] = df_vse_tr["datum_dt"].dt.strftime("%Y-%m")
    tr_ta_mesec = df_vse_tr[df_vse_tr["leto_mesec"] == mesec_danes]
    st_vnesenih_fiksnih = tr_ta_mesec[tr_ta_mesec["opis"].fillna("").str.startswith("[Fiksno]")].shape[0]

    # Preverjanje limitov
    presezeni_limiti = []
    opozorilni_limiti = []
    if not df_lim_check.empty:
        odhodki_mesec = tr_ta_mesec[tr_ta_mesec["tip"] == "odhodek"]
        poraba_dict = odhodki_mesec.groupby("kategorija")["znesek"].sum().to_dict()
        for _, r in df_lim_check.iterrows():
            k = r["kategorija"]
            lim = float(r["limit_znesek"])
            por = poraba_dict.get(k, 0.0)
            if por > lim:
                presezeni_limiti.append(f"{k} (+{por - lim:,.2f} €)")
            elif por >= 0.85 * lim:
                opozorilni_limiti.append(k)

    if st_fiksnih > 0 and st_vnesenih_fiksnih == 0:
        st.info(f"💡 **Opomnik za fiksne stroške:** Za tekoči mesec ({mesec_danes}) fiksni stroški še niso vneseni.")

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
# 1. ZAVIHEK: VNOS TRANSAKCIJE S SPLETNIM PREVERJANJEM LIMITA
# ==========================================
with z_vnos:
    st.subheader("📝 Vnos nove transakcije")
    col1, col2 = st.columns(2)
    with col1:
        clan = st.selectbox("Družinski član", CLANI)
        tip = st.radio("Vrsta", ["odhodek", "prihodek"], horizontal=True)
        znesek = st.number_input("Znesek (€)", min_value=0.0, step=1.0, format="%.2f")
    with col2:
        izbran_datum = st.date_input("Datum transakcije", value=date.today())
        kategorija = st.selectbox("Kategorija", KATEGORIJE)
        opis = st.text_input("Opis transakcije")

    # Takojšnje preverjanje stanja limita ob tipkanju
    if tip == "odhodek" and not df_lim_check.empty and znesek > 0:
        lim_vrstica = df_lim_check[df_lim_check["kategorija"] == kategorija]
        if not lim_vrstica.empty:
            lim_val = float(lim_vrstica.iloc[0]["limit_znesek"])
            mesec_vnosa = izbran_datum.strftime("%Y-%m")
            if not df_vse_tr.empty:
                porabljeno_do_sedaj = df_vse_tr[
                    (df_vse_tr["leto_mesec"] == mesec_vnosa) & 
                    (df_vse_tr["tip"] == "odhodek") & 
                    (df_vse_tr["kategorija"] == kategorija)
                ]["znesek"].sum()
            else:
                porabljeno_do_sedaj = 0.0

            napoved = porabljeno_do_sedaj + znesek
            razlika = lim_val - napoved

            if napoved > lim_val:
                st.error(f"🚨 **Pozor!** S tem vnosom boste presegli limit ({lim_val:.2f} €) za {abs(razlika):.2f} €! (Trenutna poraba: {porabljeno_do_sedaj:.2f} €)")
            elif napoved >= 0.8 * lim_val:
                st.warning(f"⚠️ **Opozorilo:** Po tem vnosu vam v kategoriji '{kategorija}' ostaja le še {razlika:.2f} € (Limit: {lim_val:.2f} €).")
            else:
                st.info(f"✅ V okviru limita. Po tem vnosu ostaja še {razlika:.2f} € od {lim_val:.2f} €.")

    if st.button("💾 Shrani transakcijo", type="primary", width="stretch"):
        if znesek <= 0:
            st.error("Prosimo, vnesite znesek večji od 0 €.")
        else:
            supabase.table("transakcije").insert({
                "datum": izbran_datum.isoformat(),
                "clan": clan,
                "tip": tip,
                "kategorija": kategorija,
                "znesek": float(znesek),
                "opis": opis
            }).execute()
            st.success("Transakcija uspešno shranjena v oblak!")
            time.sleep(0.5)
            varno_osvezi()

# ==========================================
# 2. ZAVIHEK: PREGLED, ISKANJE & HITRI FILTRI
# ==========================================
with z_pregled:
    df = df_vse_tr.copy()
    if not df.empty:
        if "izbran_filter_mesec" not in st.session_state:
            st.session_state.izbran_filter_mesec = mesec_danes

        st.write("**Hitri izbor obdobja:**")
        hf1, hf2, hf3, _ = st.columns([1, 1, 1, 3])
        with hf1:
            if st.button("📅 Tekoči mesec", width="stretch"):
                st.session_state.izbran_filter_mesec = mesec_danes
                varno_osvezi()
        with hf2:
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
                        supabase.table("transakcije").delete().eq("id", izbran_id_del).execute()
                        st.warning(f"Transakcija {izbran_id_del} je bila izbrisana!")
                        varno_osvezi()
    else:
        st.info("Baza je prazna. Dodajte prvi vnos v prvem zavihku.")

# ==========================================
# 3. ZAVIHEK: LETNI PREGLED
# ==========================================
with z_letno:
    st.subheader("📈 Letna primerjava po mesecih")
    if not df_vse_tr.empty:
        df_letno = df_vse_tr.copy()
        pivot_prihodki = df_letno[df_letno["tip"] == "prihodek"].groupby("leto_mesec")["znesek"].sum()
        pivot_odhodki = df_letno[df_letno["tip"] == "odhodek"].groupby("leto_mesec")["znesek"].sum()

        pregled_letni = pd.DataFrame({"Prihodki (€)": pivot_prihodki, "Odhodki (€)": pivot_odhodki}).fillna(0)
        pregled_letni["Saldo (€)"] = pregled_letni["Prihodki (€)"] - pregled_letni["Odhodki (€)"]
        pregled_letni = pregled_letni.sort_index(ascending=False)

        st.dataframe(pregled_letni.style.format("{:,.2f} €"), width="stretch")
        st.line_chart(pregled_letni[["Prihodki (€)", "Odhodki (€)"]])
    else:
        st.info("Ni še podatkov za letni pregled.")

# ==========================================
# 4. ZAVIHEK: VARČEVANJE & CILJI
# ==========================================
with z_varcevanje:
    st.subheader("🏦 Varčevalni sklad & Cilji varčevanja")
    df_cilji = nalozi_podatke("varcevalni_cilji", "ime_cilja", asc=True)
    df_varc = nalozi_podatke("varcevanje", "datum", asc=False)

    col_c1, col_c2 = st.columns([1, 2])
    with col_c1:
        st.write("**Dodaj nov varčevalni cilj:**")
        with st.form("obrazec_cilj", clear_on_submit=True):
            ime_c = st.text_input("Ime cilja (npr. Dopust, Rezerva):")
            znesek_c = st.number_input("Ciljni znesek (€):", min_value=50.0, step=50.0, value=1000.0)
            if st.form_submit_button("Dodaj cilj"):
                if ime_c.strip():
                    try:
                        supabase.table("varcevalni_cilji").insert({"ime_cilja": ime_c.strip(), "ciljni_znesek": float(znesek_c)}).execute()
                        st.success(f"Cilj {ime_c} dodan!")
                        varno_osvezi()
                    except Exception as e:
                        st.error(f"Napaka ali cilj že obstaja: {e}")

    with col_c2:
        st.write("**Sledenje napredku ciljev:**")
        if not df_cilji.empty and not df_varc.empty:
            df_varc["znesek"] = pd.to_numeric(df_varc["znesek"], errors="coerce").fillna(0.0)
            for _, r in df_cilji.iterrows():
                cilj_ime = r["ime_cilja"]
                cilj_znesek = float(r["ciljni_znesek"])
                pol = df_varc[(df_varc["vrsta"] == "Polog v varčevanje") & (df_varc["namen"] == cilj_ime)]["znesek"].sum()
                por = df_varc[(df_varc["vrsta"] == "Poraba iz varčevanja") & (df_varc["namen"] == cilj_ime)]["znesek"].sum()
                trenutno = pol - por
                procent = min(max(trenutno / cilj_znesek, 0.0), 1.0) if cilj_znesek > 0 else 0.0
                
                c_lbl, c_del_btn = st.columns([4, 1])
                with c_lbl:
                    st.write(f"🎯 **{cilj_ime}**: {trenutno:,.2f} € od {cilj_znesek:,.2f} € ({procent*100:.1f} %)")
                    st.progress(procent)
                with c_del_btn:
                    if st.button("Briši", key=f"del_c_{cilj_ime}"):
                        supabase.table("varcevalni_cilji").delete().eq("ime_cilja", cilj_ime).execute()
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
                supabase.table("varcevanje").insert({
                    "datum": v_datum.isoformat(),
                    "clan": v_clan,
                    "vrsta": v_vrsta,
                    "znesek": float(v_znesek),
                    "namen": koncni_namen
                }).execute()
                st.success("Zabeleženo v varčevalni sklad!")
                varno_osvezi()

    with vcol2:
        st.write("**📊 Stanje prihrankov:**")
        if not df_varc.empty:
            df_varc["znesek"] = pd.to_numeric(df_varc["znesek"], errors="coerce").fillna(0.0)
            pol_vsi = df_varc[df_varc["vrsta"] == "Polog v varčevanje"]["znesek"].sum()
            por_vsi = df_varc[df_varc["vrsta"] == "Poraba iz varčevanja"]["znesek"].sum()
            st.metric("Skupaj v prihrankih", f"{pol_vsi - por_vsi:,.2f} €")
            st.dataframe(df_varc[["id", "datum", "clan", "vrsta", "znesek", "namen"]], width="stretch")

            with st.expander("🗑️ Izbriši vnos iz varčevanja"):
                v_izb_del = st.selectbox("Izberite ID varčevanja:", df_varc["id"].tolist(), key="del_varc_id")
                if st.button("Izbriši ta zapis varčevanja"):
                    supabase.table("varcevanje").delete().eq("id", v_izb_del).execute()
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
                    supabase.table("fiksni_stroski").insert({
                        "clan": f_clan,
                        "kategorija": f_kat,
                        "znesek": float(f_znesek),
                        "opis": f_opis.strip()
                    }).execute()
                    st.success("Dodan na seznam!")
                    varno_osvezi()

    with col_f2:
        df_fiksni = df_vsi_fiksni.copy()
        st.write("**Seznam fiksnih mesečnih stroškov:**")
        if not df_fiksni.empty:
            df_fiksni["znesek"] = pd.to_numeric(df_fiksni["znesek"], errors="coerce").fillna(0.0)
            st.dataframe(df_fiksni[["id", "clan", "kategorija", "znesek", "opis"]], width="stretch")
            skupaj_fiksni = df_fiksni["znesek"].sum()
            st.write(f"Vsak mesec skupaj fiksno: **{skupaj_fiksni:,.2f} €**")
            
            c_f_vnesi, c_f_del = st.columns([1.5, 1])
            with c_f_vnesi:
                if st.button("🚀 Vnesi vse fiksne stroške v proračun za danes", type="primary", width="stretch"):
                    danes_iso = date.today().isoformat()
                    novi_vnosi = []
                    for _, r in df_fiksni.iterrows():
                        novi_vnosi.append({
                            "datum": danes_iso,
                            "clan": r["clan"],
                            "tip": "odhodek",
                            "kategorija": r["kategorija"],
                            "znesek": float(r["znesek"]),
                            "opis": f"[Fiksno] {r['opis']}"
                        })
                    if novi_vnosi:
                        supabase.table("transakcije").insert(novi_vnosi).execute()
                    st.success("Vsi fiksni stroški zabeleženi!")
                    varno_osvezi()
            with c_f_del:
                with st.expander("🗑️ Odstrani fiksen strošek"):
                    izb_f_del = st.selectbox("Izberite ID stroška:", df_fiksni["id"].tolist(), key="del_fiks_id")
                    if st.button("Odstrani ta strošek"):
                        supabase.table("fiksni_stroski").delete().eq("id", izb_f_del).execute()
                        st.warning("Fiksni strošek odstranjen!")
                        varno_osvezi()
        else:
            st.info("Nimate še shranjenih ponavljajočih se stroškov.")

# ==========================================
# 6. ZAVIHEK: LIMITI PRORAČUNA Z BARVNIMI KARTICAMI
# ==========================================
with z_limiti:
    st.subheader("🎯 Mesečni proračunski limiti z merilniki napredka")
    
    df_lim = nalozi_podatke("limiti", "kategorija", asc=True)
    if not df_lim.empty:
        df_lim["limit_znesek"] = pd.to_numeric(df_lim["limit_znesek"], errors="coerce").fillna(0.0)
        odhodki_danes = df_vse_tr[(df_vse_tr["tip"] == "odhodek") & (df_vse_tr["leto_mesec"] == mesec_danes)] if not df_vse_tr.empty else pd.DataFrame()
        poraba_po_kat = odhodki_danes.groupby("kategorija")["znesek"].sum().to_dict() if not odhodki_danes.empty else {}

        for _, row in df_lim.iterrows():
            kat = row["kategorija"]
            lim = float(row["limit_znesek"])
            porabljeno = poraba_po_kat.get(kat, 0.0)
            odstotek = (porabljeno / lim) * 100 if lim > 0 else 0.0
            razlika = lim - porabljeno
            delez_za_bar = min(porabljeno / lim, 1.0) if lim > 0 else 0.0

            if odstotek >= 100:
                barva = "#ef4444"
                opozorilo_tekst = f"🚨 Preseženo za {abs(razlika):.2f} €!"
            elif odstotek >= 75:
                barva = "#f59e0b"
                opozorilo_tekst = f"⚠️ Ostaja le še {razlika:.2f} €"
            else:
                barva = "#10b981"
                opozorilo_tekst = f"✅ Na voljo še {razlika:.2f} €"

            st.markdown(
                f"""
                <div style="background-color: #1e293b; border-radius: 12px; padding: 12px 16px; margin-top: 12px; margin-bottom: 6px; border-left: 6px solid {barva};">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                        <span style="font-size: 1.1rem; font-weight: 600; color: #f8fafc;">{kat}</span>
                        <span style="font-size: 0.95rem; font-weight: 600; color: {barva};">{opozorilo_tekst}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.9rem; color: #94a3b8;">
                        <span>Porabljeno: <b>{porabljeno:.2f} €</b></span>
                        <span>Limit: <b>{lim:.2f} €</b> ({odstotek:.0f} %)</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.progress(delez_za_bar)
            
            if st.button(f"🗑️ Izbriši limit za {kat}", key=f"del_lim_{kat}"):
                supabase.table("limiti").delete().eq("kategorija", kat).execute()
                st.warning(f"Limit za {kat} izbrisan!")
                varno_osvezi()
    else:
        st.info("Nimate še določenih limitov.")

    st.divider()
    st.markdown("#### ➕ Nastavi nov limit")
    with st.form("obrazec_limiti"):
        lcol1, lcol2 = st.columns(2)
        with lcol1:
            kat_za_limit = st.selectbox("Kategorija za limit", [k for k in KATEGORIJE if k != "Plača"])
        with lcol2:
            znesek_limita = st.number_input("Mesečni limit (€)", min_value=10.0, step=10.0, value=200.0)
        if st.form_submit_button("Shrani limit", width="stretch"):
            supabase.table("limiti").upsert({"kategorija": kat_za_limit, "limit_znesek": float(znesek_limita)}).execute()
            st.success(f"Limit za {kat_za_limit} nastavljen na {znesek_limita:,.2f} €")
            varno_osvezi()

# ==========================================
# 7. ZAVIHEK: UREJANJE IN BRISANJE
# ==========================================
with z_uredi:
    df_vsi = df_vse_tr.copy()
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
                supabase.table("transakcije").update({
                    "datum": u_datum.isoformat(),
                    "clan": u_clan,
                    "tip": u_tip,
                    "kategorija": u_kat,
                    "znesek": float(u_znesek),
                    "opis": u_opis
                }).eq("id", izbran_id).execute()
                st.success("Posodobljeno!")
                varno_osvezi()

        st.divider()
        st.subheader("🗑️ Brisanje vnosov")
        b1, b2 = st.columns(2)
        with b1:
            st.write("**Izbriši izbrani vnos zgoraj:**")
            if st.button(f"Izbriši vnos ID {izbran_id}", type="secondary", width="stretch"):
                supabase.table("transakcije").delete().eq("id", izbran_id).execute()
                st.warning(f"Vnos ID {izbran_id} je bil izbrisan!")
                varno_osvezi()
        with b2:
            st.write("**Ponastavitev vseh transakcij:**")
            if st.button("⚠️ Izbriši VSE transakcije", type="primary", width="stretch"):
                supabase.table("transakcije").delete().neq("id", 0).execute()
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
                    supabase.table("clani_seznam").upsert({"ime": nov_clan.strip()}).execute()
                    st.success(f"Član {nov_clan} dodan!")
                    varno_osvezi()
        
        if len(CLANI) > 1:
            clan_za_izbris = st.selectbox("Odstrani člana:", CLANI)
            if st.button("Odstrani izbranega člana", type="secondary"):
                supabase.table("clani_seznam").delete().eq("ime", clan_za_izbris).execute()
                st.warning(f"Član {clan_za_izbris} odstranjen!")
                varno_osvezi()

    with ncol2:
        st.write("**Kategorije:**")
        st.dataframe(pd.DataFrame(KATEGORIJE, columns=["Kategorija"]), width="stretch", hide_index=True)
        with st.form("dodaj_kat_form", clear_on_submit=True):
            nova_kat = st.text_input("Nova kategorija:")
            if st.form_submit_button("Dodaj kategorijo"):
                if nova_kat.strip():
                    supabase.table("kategorije_seznam").upsert({"ime": nova_kat.strip()}).execute()
                    st.success(f"Kategorija {nova_kat} dodana!")
                    varno_osvezi()
        
        if len(KATEGORIJE) > 1:
            kat_za_izbris = st.selectbox("Odstrani kategorijo:", KATEGORIJE)
            if st.button("Odstrani izbrano kategorijo", type="secondary"):
                supabase.table("kategorije_seznam").delete().eq("ime", kat_za_izbris).execute()
                st.warning(f"Kategorija {kat_za_izbris} odstranjena!")
                varno_osvezi()

    st.divider()
    st.subheader("📥 Uvoz bančnega izpiska (CSV)")
    csv_file = st.file_uploader("Izberite bančno datoteko (CSV)", type=["csv", "txt"])
    if csv_file is not None:
        locilo = st.radio("Ločilo v CSV datoteki:", ["; (podpičje)", ", (vejica)"], horizontal=True)
        sep_char = ";" if ";" in locilo else ","
        try:
            df_banka = pd.read_csv(csv_file, sep=sep_char)
            st.write("**Predogled naložene datoteke:**")
            st.dataframe(df_banka.head(3), width="stretch")

            vsi_stolpci = df_banka.columns.tolist()
            icol1, icol2, icol3 = st.columns(3)
            with icol1: kol_datum = st.selectbox("Stolpec za datum:", vsi_stolpci)
            with icol2: kol_opis = st.selectbox("Stolpec za opis / prejemnika:", vsi_stolpci)
            with icol3: kol_znesek = st.selectbox("Stolpec za znesek:", vsi_stolpci)

            icol4, icol5 = st.columns(2)
            with icol4: privzeti_clan = st.selectbox("Privzeti član:", CLANI)
            with icol5: privzeta_kat = st.selectbox("Privzeta kategorija:", KATEGORIJE)

            if st.button("🚀 Uvozi vse transakcije v proračun", type="primary"):
                uvozi_list = []
                for _, row in df_banka.iterrows():
                    try:
                        surov_znesek = str(row[kol_znesek]).replace("€", "").replace(" ", "").replace(".", "").replace(",", ".")
                        val = float(surov_znesek)
                        tip_tr = "prihodek" if val > 0 else "odhodek"
                        abs_znesek = abs(val)

                        datum_tr = pd.to_datetime(row[kol_datum], errors="coerce")
                        datum_str = datum_tr.strftime("%Y-%m-%d") if pd.notna(datum_tr) else date.today().isoformat()
                        opis_tr = str(row[kol_opis])[:100]

                        uvozi_list.append({
                            "datum": datum_str,
                            "clan": privzeti_clan,
                            "tip": tip_tr,
                            "kategorija": privzeta_kat,
                            "znesek": abs_znesek,
                            "opis": f"[Banka] {opis_tr}"
                        })
                    except Exception:
                        continue

                if uvozi_list:
                    supabase.table("transakcije").insert(uvozi_list).execute()
                st.success(f"Uspešno uvoženih {len(uvozi_list)} transakcij!")
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
