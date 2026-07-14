import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# ==========================================
# CONFIGURAZIONE E FUNZIONI DI BASE
# ==========================================
st.set_page_config(page_title="Calcio Engine", page_icon="⚽", layout="wide")

FILE_DATI = "data/processed/database_calcio.json"
os.makedirs("data/processed", exist_ok=True)

def carica_db():
    if os.path.exists(FILE_DATI):
        with open(FILE_DATI, "r", encoding="utf-8") as f:
            db = json.load(f)
            # Retro-compatibilità
            if "partite" not in db: db["partite"] = []
            if "classifiche" not in db: db["classifiche"] = {}
            return db
    return {"leghe": [], "squadre": [], "partite": [], "classifiche": {}} # Rimosso 'giocatori'

def salva_db(db):
    with open(FILE_DATI, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

def trova_squadra_giocatore(partita, nome_giocatore):
    nome_g = nome_giocatore.lower().strip()
    for sq in [partita["casa"], partita["trasferta"]]:
        for t in partita["formazioni"].get(sq, {}).get("titolari", []):
            if t["nome"].lower().strip() == nome_g: return sq
        for s in partita["eventi"]["sostituzioni"]:
            if s["entrato"].lower().strip() == nome_g: return sq
    return None

def aggiorna_classifiche(db):
    classifiche = {}
    
    def get_girone(nome_sq, nome_lega):
        for s in db.get("squadre", []):
            if s["nome"].lower() == nome_sq.lower() and s["lega"].lower() == nome_lega.lower():
                return s.get("girone", "Unico")
        return "Unico"

    for squadra in db.get("squadre", []):
        lega = squadra["lega"]
        nome = squadra["nome"]
        girone = squadra.get("girone", "Unico")
        
        if lega not in classifiche: classifiche[lega] = {}
        if girone not in classifiche[lega]: classifiche[lega][girone] = {}
        classifiche[lega][girone][nome] = {"punti": 0, "giocate": 0, "vinte": 0, "pareggiate": 0, "perse": 0, "gf": 0, "gs": 0, "dr": 0}
        
    for partita in db.get("partite", []):
        if partita.get("fase") == "eliminazione": continue
            
        lega = partita["lega"]
        casa = partita["casa"]
        trasferta = partita["trasferta"]
        
        gir_casa = get_girone(casa, lega)
        gir_trasf = get_girone(trasferta, lega)
        
        if lega not in classifiche: classifiche[lega] = {}
        if gir_casa not in classifiche[lega]: classifiche[lega][gir_casa] = {}
        if gir_trasf not in classifiche[lega]: classifiche[lega][gir_trasf] = {}
        
        if casa not in classifiche[lega][gir_casa]: classifiche[lega][gir_casa][casa] = {"punti": 0, "giocate": 0, "vinte": 0, "pareggiate": 0, "perse": 0, "gf": 0, "gs": 0, "dr": 0}
        if trasferta not in classifiche[lega][gir_trasf]: classifiche[lega][gir_trasf][trasferta] = {"punti": 0, "giocate": 0, "vinte": 0, "pareggiate": 0, "perse": 0, "gf": 0, "gs": 0, "dr": 0}
        
        gol_casa = sum(1 for g in partita["eventi"]["goal"] if g["squadra"] == casa)
        gol_trasf = sum(1 for g in partita["eventi"]["goal"] if g["squadra"] == trasferta)
        
        classifiche[lega][gir_casa][casa]["giocate"] += 1
        classifiche[lega][gir_trasf][trasferta]["giocate"] += 1
        classifiche[lega][gir_casa][casa]["gf"] += gol_casa
        classifiche[lega][gir_casa][casa]["gs"] += gol_trasf
        classifiche[lega][gir_trasf][trasferta]["gf"] += gol_trasf
        classifiche[lega][gir_trasf][trasferta]["gs"] += gol_casa
        
        if gol_casa > gol_trasf:
            classifiche[lega][gir_casa][casa]["vinte"] += 1
            classifiche[lega][gir_casa][casa]["punti"] += 3
            classifiche[lega][gir_trasf][trasferta]["perse"] += 1
        elif gol_casa < gol_trasf:
            classifiche[lega][gir_trasf][trasferta]["vinte"] += 1
            classifiche[lega][gir_trasf][trasferta]["punti"] += 3
            classifiche[lega][gir_casa][casa]["perse"] += 1
        else:
            classifiche[lega][gir_casa][casa]["pareggiate"] += 1
            classifiche[lega][gir_trasf][trasferta]["pareggiate"] += 1
            classifiche[lega][gir_casa][casa]["punti"] += 1
            classifiche[lega][gir_trasf][trasferta]["punti"] += 1

    for lega, gironi in classifiche.items():
        for girone, squadre in gironi.items():
            for sq, stats in squadre.items():
                stats["dr"] = stats["gf"] - stats["gs"]
            
    db["classifiche"] = classifiche
    return db

db = carica_db()

# ==========================================
# MENU LATERALE
# ==========================================
st.sidebar.title("⚽ Gestionale Calcio")
menu = st.sidebar.radio(
    "Navigazione:",
    [
        "🏆 Classifiche", 
        "➕ Nuovo (Lega/Squadra)", 
        "➕ Inserisci Partita", 
        "👟 Marcatori e Assist",
        "🔍 Cerca Risultati",
        "📊 Statistiche & Query Builder"
    ]
)
st.sidebar.markdown("---")
if st.sidebar.button("Forza Ricalcolo Dati"):
    db = aggiorna_classifiche(db)
    salva_db(db)
    st.sidebar.success("Dati ricalcolati!")

# ==========================================
# 1. CLASSIFICHE
# ==========================================
if menu == "🏆 Classifiche":
    st.title("Classifiche")
    
    if not db.get("classifiche"):
        st.warning("Nessuna classifica. Inserisci prima qualche lega e squadra.")
    else:
        leghe_disponibili = list(db["classifiche"].keys())
        lega_scelta = st.selectbox("Seleziona la Competizione", leghe_disponibili)
        
        gironi_lega = db["classifiche"][lega_scelta]
        nomi_gironi = [g for g in gironi_lega.keys() if g != "Unico"]
        
        # Filtro Gironi (MODIFICA RICHIESTA)
        gironi_selezionati = ["Unico"]
        if nomi_gironi:
            scelta_gironi = st.multiselect("Quali gironi vuoi visualizzare?", sorted(nomi_gironi))
            gironi_selezionati = scelta_gironi if scelta_gironi else nomi_gironi
        
        for nome_girone in sorted(gironi_selezionati):
            squadre_girone = gironi_lega.get(nome_girone, {})
            if not squadre_girone: continue
            
            if nome_girone != "Unico":
                st.subheader(f"Girone {nome_girone}")
            
            gruppi_punti = {}
            for nome, stats in squadre_girone.items():
                p = stats['punti']
                if p not in gruppi_punti: gruppi_punti[p] = []
                gruppi_punti[p].append(nome)
                
            classifica_ordinata = []
            for punti in sorted(gruppi_punti.keys(), reverse=True):
                squadre_a_pari = gruppi_punti[punti]
                if len(squadre_a_pari) == 1:
                    classifica_ordinata.append((squadre_a_pari[0], squadre_girone[squadre_a_pari[0]]))
                else:
                    class_avulsa = {sq: {"punti": 0, "dr": 0} for sq in squadre_a_pari}
                    for p in db.get("partite", []):
                        if p["lega"].lower() == lega_scelta.lower() and p.get("fase") != "eliminazione":
                            casa, trasf = p["casa"], p["trasferta"]
                            if casa in squadre_a_pari and trasf in squadre_a_pari:
                                gc = sum(1 for g in p["eventi"]["goal"] if g["squadra"] == casa)
                                gt = sum(1 for g in p["eventi"]["goal"] if g["squadra"] == trasf)
                                class_avulsa[casa]["dr"] += (gc - gt)
                                class_avulsa[trasf]["dr"] += (gt - gc)
                                if gc > gt: class_avulsa[casa]["punti"] += 3
                                elif gc < gt: class_avulsa[trasf]["punti"] += 3
                                else:
                                    class_avulsa[casa]["punti"] += 1
                                    class_avulsa[trasf]["punti"] += 1
                                    
                    sq_ordinate_avulsa = sorted(
                        squadre_a_pari,
                        key=lambda x: (-class_avulsa[x]["punti"], -class_avulsa[x]["dr"], -squadre_girone[x]["dr"], x.lower())
                    )
                    for nome in sq_ordinate_avulsa:
                        classifica_ordinata.append((nome, squadre_girone[nome]))
            
            dati_tabella = []
            for pos, (nome, stats) in enumerate(classifica_ordinata, start=1):
                dati_tabella.append({
                    "Pos": pos, "Squadra": nome, "PT": stats["punti"], "G": stats["giocate"],
                    "V": stats["vinte"], "P": stats["pareggiate"], "S": stats["perse"],
                    "GF": stats["gf"], "GS": stats["gs"], "DR": stats["dr"]
                })
            
            st.dataframe(pd.DataFrame(dati_tabella), hide_index=True, use_container_width=True)

# ==========================================
# 2. ANAGRAFICHE
# ==========================================
elif menu == "➕ Nuovo (Lega/Squadra)":
    st.title("Gestione Anagrafiche")
    # Rimosso il tab Giocatore (MODIFICA RICHIESTA)
    tab1, tab2 = st.tabs(["🏆 Nuova Lega", "🛡️ Nuova Squadra"])
    
    with tab1:
        with st.form("form_lega", clear_on_submit=True):
            nome_lega = st.text_input("Nome competizione (es. Serie A)")
            nazione = st.text_input("Nazione/Continente")
            tipo = st.selectbox("Tipo di competizione", ["Campionato Normale", "Torneo a Gironi"])
            if st.form_submit_button("Salva Lega"):
                tipo_str = "gironi" if "Gironi" in tipo else "campionato"
                db["leghe"].append({"nome": nome_lega, "nazione": nazione, "tipo": tipo_str})
                salva_db(db)
                st.success(f"Competizione '{nome_lega}' salvata!")

    with tab2:
        with st.form("form_squadra", clear_on_submit=True):
            nome_squadra = st.text_input("Nome Squadra")
            stadio = st.text_input("Stadio")
            nomi_leghe = [l["nome"] for l in db.get("leghe", [])]
            lega_sel = st.selectbox("Lega di appartenenza", ["Nessuna"] + nomi_leghe)
            girone = st.text_input("Girone (es. A) - Lascia vuoto se campionato unico")
            if st.form_submit_button("Salva Squadra"):
                gir_val = girone.upper().strip() if girone else "Unico"
                db["squadre"].append({"nome": nome_squadra, "stadio": stadio, "lega": lega_sel, "girone": gir_val})
                salva_db(db)
                db = aggiorna_classifiche(db)
                st.success(f"Squadra '{nome_squadra}' salvata!")

# ==========================================
# 3. INSERISCI PARTITA
# ==========================================
elif menu == "➕ Inserisci Partita":
    st.title("Inserisci Nuova Partita")
    
    leghe = [l["nome"] for l in db.get("leghe", [])]
    if not leghe:
        st.error("Crea prima una Lega!")
    else:
        lega_sel = st.selectbox("Seleziona Lega", leghe)
        lega_info = next((l for l in db.get("leghe", []) if l["nome"] == lega_sel), {})
        
        is_eliminazione = False
        fase = "campionato"
        
        if lega_info.get("tipo") == "gironi":
            fase_scelta = st.radio("Fase del torneo", ["Girone", "Eliminazione Diretta"], horizontal=True)
            if fase_scelta == "Eliminazione Diretta":
                is_eliminazione = True
                fase = "eliminazione"
                giornata = st.text_input("Turno (es. Ottavi, Finale)")
            else:
                fase = "girone"
                giornata = st.text_input("Giornata (es. 1)")
        else:
            giornata = st.text_input("Giornata (es. 1)")

        squadre = [s["nome"] for s in db.get("squadre", []) if s["lega"] == lega_sel]
        
        # --- MODIFICA: Caselle Rigori spostate FUORI dal form per aggiornarsi subito ---
        col1, col2 = st.columns(2)
        with col1:
            casa = st.selectbox("Squadra Casa", squadre, key="c")
            gol_c = st.number_input(f"Gol {casa}", min_value=0, max_value=20, value=0, key="gol_c_input")
            rs_c = st.number_input(f"Rigori Sbagliati {casa}", min_value=0, max_value=10, value=0, key="rs_c_in")
        with col2:
            index_t = 1 if len(squadre) > 1 else 0
            trasf = st.selectbox("Squadra Trasferta", squadre, index=index_t, key="t")
            gol_t = st.number_input(f"Gol {trasf}", min_value=0, max_value=20, value=0, key="gol_t_input")
            rs_t = st.number_input(f"Rigori Sbagliati {trasf}", min_value=0, max_value=10, value=0, key="rs_t_in")

        st.markdown("---")
        
        with st.form("form_partita", clear_on_submit=True):
            
            # --- SEZIONE GOAL ---
            st.subheader("⚽ Dettagli Goal")
            eventi_c = []
            if gol_c > 0:
                st.write(f"**Marcatori {casa}**")
                for i in range(gol_c):
                    c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 1, 1])
                    m = c1.text_input(f"Marcatore {i+1}", key=f"mc_{i}", label_visibility="collapsed", placeholder="Nome")
                    minuto = c2.text_input("Minuto", key=f"minc_{i}", label_visibility="collapsed", placeholder="Min")
                    ass = c3.text_input("Assist", key=f"assc_{i}", label_visibility="collapsed", placeholder="Assist")
                    rig = c4.checkbox("Rig", key=f"rigc_{i}", help="Rigore?")
                    auto = c5.checkbox("Aut", key=f"autoc_{i}", help="Autogoal?")
                    eventi_c.append({"squadra": casa, "marcatore": m, "minuto": minuto, "assist": ass, "rigore": rig, "autogoal": auto})

            eventi_t = []
            if gol_t > 0:
                st.write(f"**Marcatori {trasf}**")
                for i in range(gol_t):
                    c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 1, 1])
                    m = c1.text_input(f"Marcatore {i+1}", key=f"mt_{i}", label_visibility="collapsed", placeholder="Nome")
                    minuto = c2.text_input("Minuto", key=f"mint_{i}", label_visibility="collapsed", placeholder="Min")
                    ass = c3.text_input("Assist", key=f"asst_{i}", label_visibility="collapsed", placeholder="Assist")
                    rig = c4.checkbox("Rig", key=f"rigt_{i}", help="Rigore?")
                    auto = c5.checkbox("Aut", key=f"autot_{i}", help="Autogoal?")
                    eventi_t.append({"squadra": trasf, "marcatore": m, "minuto": minuto, "assist": ass, "rigore": rig, "autogoal": auto})
                
            st.markdown("---")
            
            # --- SEZIONE RIGORI SBAGLIATI ---
            eventi_rs = []
            if rs_c > 0 or rs_t > 0:
                st.subheader("❌ Dettagli Rigori Sbagliati")
                col_rs1, col_rs2 = st.columns(2)
                
                with col_rs1:
                    if rs_c > 0:
                        st.write(f"**{casa}**")
                        for i in range(rs_c):
                            c1, c2, c3 = st.columns([3, 2, 3])
                            tir = c1.text_input("Tir", key=f"rsc_tir_{i}", label_visibility="collapsed", placeholder="Nome Tiratore")
                            minu = c2.text_input("Min", key=f"rsc_min_{i}", label_visibility="collapsed", placeholder="Min")
                            esit = c3.selectbox("Esito", ["Parato", "Fuori/Palo"], key=f"rsc_esito_{i}", label_visibility="collapsed")
                            eventi_rs.append({"squadra": casa, "tiratore": tir, "minuto": minu, "esito": esit})
                
                with col_rs2:
                    if rs_t > 0:
                        st.write(f"**{trasf}**")
                        for i in range(rs_t):
                            c1, c2, c3 = st.columns([3, 2, 3])
                            tir = c1.text_input("Tir", key=f"rst_tir_{i}", label_visibility="collapsed", placeholder="Nome Tiratore")
                            minu = c2.text_input("Min", key=f"rst_min_{i}", label_visibility="collapsed", placeholder="Min")
                            esit = c3.selectbox("Esito", ["Parato", "Fuori/Palo"], key=f"rst_esito_{i}", label_visibility="collapsed")
                            eventi_rs.append({"squadra": trasf, "tiratore": tir, "minuto": minu, "esito": esit})

                st.markdown("---")

            # --- SEZIONE FORMAZIONI UNIFICATE ---
            st.subheader("📋 Formazioni (11 Titolari)")
        
            col_mc, col_mt = st.columns(2)
            mod_c = col_mc.text_input(f"Modulo {casa}", value="4-3-3")
            mod_t = col_mt.text_input(f"Modulo {trasf}", value="4-3-3")
        
            def get_ruoli(modulo_str):
                ruoli = ["Portiere"]
                try:
                    numeri = [int(n.strip()) for n in modulo_str.split('-')]
                    if len(numeri) == 3:
                        ruoli.extend(["Difensore"] * numeri[0])
                        ruoli.extend(["Centrocampista"] * numeri[1])
                        ruoli.extend(["Attaccante"] * numeri[2])
                    elif len(numeri) == 4:
                        ruoli.extend(["Difensore"] * numeri[0])
                        ruoli.extend(["Centrocampista"] * numeri[1])
                        ruoli.extend(["Trequartista"] * numeri[2])
                        ruoli.extend(["Attaccante"] * numeri[3])
                    else:
                        ruoli.extend(["Giocatore"] * 10)
                except:
                    ruoli.extend(["Giocatore"] * 10)
                return ruoli[:11]

            roles_c = get_ruoli(mod_c)
            roles_t = get_ruoli(mod_t)
            
            st.write("Inserisci i nomi dei titolari. Se inserisci un sostituto e il minuto, il sistema registra il cambio.")
            
            c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([1, 2, 2, 1, 1, 2, 2, 1])
            c1.write("**Ruolo**"); c2.write(f"**Tit. {casa}**"); c3.write("**Sub**"); c4.write("**Min**")
            c5.write("**Ruolo**"); c6.write(f"**Tit. {trasf}**"); c7.write("**Sub**"); c8.write("**Min**")
            
            form_c_data, form_t_data = [], []
        
            for i in range(11):
                cols = st.columns([1, 2, 2, 1, 1, 2, 2, 1])
                role_c = roles_c[i] if i < len(roles_c) else "Giocatore"
                cols[0].text(role_c)
                t_c = cols[1].text_input(f"T_C_{i}", key=f"t_c_{i}", label_visibility="collapsed")
                s_c = cols[2].text_input(f"S_C_{i}", key=f"s_c_{i}", label_visibility="collapsed", placeholder="Sub")
                m_c = cols[3].text_input(f"M_C_{i}", key=f"m_c_{i}", label_visibility="collapsed", placeholder="Min")
                
                role_t = roles_t[i] if i < len(roles_t) else "Giocatore"
                cols[4].text(role_t)
                t_t = cols[5].text_input(f"T_T_{i}", key=f"t_t_{i}", label_visibility="collapsed")
                s_t = cols[6].text_input(f"S_T_{i}", key=f"s_t_{i}", label_visibility="collapsed", placeholder="Sub")
                m_t = cols[7].text_input(f"M_T_{i}", key=f"m_t_{i}", label_visibility="collapsed", placeholder="Min")
                
                form_c_data.append({"t": t_c, "s": s_c, "m": m_c, "r": role_c})
                form_t_data.append({"t": t_t, "s": s_t, "m": m_t, "r": role_t})

            st.markdown("---")

            # --- CARTELLINI E RIGORI ---
            st.subheader("🟥 Cartellini ed Esito")
            amm = st.text_input("Ammoniti totali (nomi separati da virgola)")
            esp = st.text_input("Espulsi totali (nomi separati da virgola)")
            
            rigori_dcr = False
            qualificata = ""
            if is_eliminazione:
                st.write("🏆 **Esito Eliminazione**")
                rigori_dcr = st.checkbox("Decisa ai rigori finali (d.c.r)?")
                if gol_c > gol_t: qualificata = casa
                elif gol_t > gol_c: qualificata = trasf
                qualificata = st.text_input("Squadra Qualificata/Vincitrice (in caso di parità o rigori)", value=qualificata)

            # === SALVATAGGIO ===
            if st.form_submit_button("💾 Salva Referto Partita"):
                if casa == trasf:
                    st.error("Le squadre devono essere diverse!")
                else:
                    goal_tot = [g for g in (eventi_c + eventi_t) if g["marcatore"].strip() != ""]
                    tit_c, tit_t, subs = [], [], []
                    
                    for r in form_c_data:
                        nome_tit = r["t"].strip()
                        if nome_tit:
                            tit_c.append({"ruolo": r["r"], "nome": nome_tit})
                            nome_sub = r["s"].strip()
                            if nome_sub:
                                subs.append({"squadra": casa, "uscito": nome_tit, "entrato": nome_sub, "minuto": r["m"].strip()})
                                
                    for r in form_t_data:
                        nome_tit = r["t"].strip()
                        if nome_tit:
                            tit_t.append({"ruolo": r["r"], "nome": nome_tit})
                            nome_sub = r["s"].strip()
                            if nome_sub:
                                subs.append({"squadra": trasf, "uscito": nome_tit, "entrato": nome_sub, "minuto": r["m"].strip()})
                    
                    partita = {
                        "lega": lega_sel, "giornata": giornata, "fase": fase,
                        "casa": casa, "trasferta": trasf, 
                        "formazioni": {
                            casa: {"modulo": mod_c, "titolari": tit_c},
                            trasf: {"modulo": mod_t, "titolari": tit_t}
                        },
                        "eventi": {
                            "goal": goal_tot,
                            "sostituzioni": subs,
                            "rigori_sbagliati": [r for r in eventi_rs if r["tiratore"].strip() != ""],
                            "ammonizioni": [x.strip() for x in amm.split(",")] if amm else [],
                            "espulsioni": [x.strip() for x in esp.split(",")] if esp else []
                        },
                        "risultato": f"{gol_c}-{gol_t}"
                    }
                    
                    if is_eliminazione:
                        if rigori_dcr: partita["risultato"] += " (d.c.r.)"
                        if qualificata: partita["qualificata"] = qualificata
                        
                    db["partite"].append(partita)
                    db = aggiorna_classifiche(db)
                    salva_db(db)
                    st.success("Partita e formazioni registrate con successo!")

# ==========================================
# 4. MARCATORI E ASSIST
# ==========================================
elif menu == "👟 Marcatori e Assist":
    st.title("Statistiche Individuali")
    leghe = list(db["classifiche"].keys())
    
    if leghe:
        lega_sel = st.selectbox("Filtra per Lega", leghe)
        marcatori, assistmen = {}, {}
        
        for p in db.get("partite", []):
            if p["lega"] == lega_sel:
                for g in p["eventi"]["goal"]:
                    m, s, a, r = g.get("marcatore"), g["squadra"], g.get("assist"), g.get("rigore")
                    is_auto = g.get("autogoal")
                    if m and not is_auto:
                        if m not in marcatori: marcatori[m] = {"gol": 0, "rigori": 0, "sq": s}
                        marcatori[m]["gol"] += 1
                        if r: marcatori[m]["rigori"] += 1
                    if a and a.strip() and not is_auto:
                        if a not in assistmen: assistmen[a] = {"assist": 0, "sq": s}
                        assistmen[a]["assist"] += 1
                        
        t1, t2 = st.tabs(["⚽ Capocannonieri", "👟 Assistmen"])
        with t1:
            df_m = pd.DataFrame([{"Giocatore": k, "Squadra": v["sq"], "Gol": v["gol"], "Rigori": v["rigori"]} for k,v in marcatori.items()])
            if not df_m.empty: st.dataframe(df_m.sort_values(by="Gol", ascending=False), hide_index=True)
            else: st.info("Nessun gol registrato.")
        with t2:
            df_a = pd.DataFrame([{"Giocatore": k, "Squadra": v["sq"], "Assist": v["assist"]} for k,v in assistmen.items()])
            if not df_a.empty: st.dataframe(df_a.sort_values(by="Assist", ascending=False), hide_index=True)
            else: st.info("Nessun assist registrato.")

# ==========================================
# 5. CERCA RISULTATI E DETTAGLIO PARTITA
# ==========================================
elif menu == "🔍 Cerca Risultati":
    st.title("Risultati e Dettaglio Partita")
    leghe = list(db["classifiche"].keys())
    
    if leghe:
        lega_sel = st.selectbox("Lega", leghe)
        lega_info = next((l for l in db.get("leghe", []) if l["nome"] == lega_sel), {})
        
        if lega_info.get("tipo") == "gironi":
            fase = st.radio("Fase", ["Girone", "Eliminazione"])
            if fase == "Girone":
                gir = st.text_input("Lettera Girone (es. A)")
                giornata = st.text_input("Giornata (es. 1)")
                target_fase = "girone"
            else:
                giornata = st.text_input("Turno (es. Ottavi)")
                target_fase = "eliminazione"
                gir = ""
        else:
            giornata = st.text_input("Giornata (es. 1)")
            target_fase = "campionato"
            gir = ""
            
        if st.button("Cerca"):
            trovate = []
            for p in db.get("partite", []):
                if p["lega"] == lega_sel and str(p.get("giornata", "")) == giornata:
                    if target_fase == "girone" and gir:
                        gir_casa = next((s.get("girone", "") for s in db["squadre"] if s["nome"]==p["casa"] and s["lega"]==lega_sel), "")
                        if gir_casa.upper() != gir.upper(): continue
                    elif target_fase == "eliminazione" and p.get("fase") != "eliminazione": continue
                    elif target_fase == "campionato" and p.get("fase") == "eliminazione": continue
                    trovate.append(p)
                    
            if trovate:
                for p in trovate:
                    with st.expander(f"⚽ {p['casa']} {p.get('risultato', '')} {p['trasferta']}"):
                        if p.get("qualificata"): st.success(f"Qualificata: {p['qualificata']}")
                        
                        # Goal e Rigori Sbagliati
                        for g in p["eventi"]["goal"]:
                            r_str = " (Rig.)" if g.get("rigore") else ""
                            a_str = f" (Assist: {g.get('assist')})" if g.get('assist') else ""
                            auto_str = " (AUTOGOAL!)" if g.get("autogoal") else ""
                            st.write(f"⚽ {g.get('minuto', '?')}' - {g['marcatore']} {r_str} {a_str} {auto_str} [{g['squadra']}]")
                            
                        for rs in p["eventi"].get("rigori_sbagliati", []):
                            st.write(f"❌ {rs.get('minuto', '?')}' - {rs['tiratore']} (Rigore {rs['esito']}) [{rs['squadra']}]")
                        
                        st.markdown("---")
                        
                        # Formazioni intelligenti
                        def format_giocatore(nome, squadra, eventi):
                            nome_lower = nome.lower().strip()
                            amm = [a.lower().strip() for a in eventi.get("ammonizioni", [])]
                            esp = [e.lower().strip() for e in eventi.get("espulsioni", [])]
                            subs = [s for s in eventi.get("sostituzioni", []) if s["squadra"] == squadra]
                            
                            simboli_card = ""
                            if nome_lower in amm: simboli_card += " 🟨"
                            if nome_lower in esp: simboli_card += " 🟥"
                            
                            sub_str = ""
                            for s in subs:
                                if s["uscito"].lower().strip() == nome_lower:
                                    nome_sub = s["entrato"]
                                    nome_sub_lower = nome_sub.lower().strip()
                                    card_sub = ""
                                    if nome_sub_lower in amm: card_sub += " 🟨"
                                    if nome_sub_lower in esp: card_sub += " 🟥"
                                    sub_str = f"  (🔄 {nome_sub}{card_sub} {s['minuto']}')"
                                    break
                            return f"{nome}{simboli_card}{sub_str}"

                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Titolari {p['casa']}**")
                            for t in p.get("formazioni", {}).get(p['casa'], {}).get("titolari", []):
                                st.write(f"- {format_giocatore(t['nome'], p['casa'], p['eventi'])}")
                        with col2:
                            st.write(f"**Titolari {p['trasferta']}**")
                            for t in p.get("formazioni", {}).get(p['trasferta'], {}).get("titolari", []):
                                st.write(f"- {format_giocatore(t['nome'], p['trasferta'], p['eventi'])}")
            else:
                st.warning("Nessuna partita trovata.")

# ==========================================
# 6. STATISTICHE & QUERY BUILDER
# ==========================================
elif menu == "📊 Statistiche & Query Builder":
    st.title("Esplorazione Dati Avanzata")
    t1, t2 = st.tabs(["📈 Statistiche (Dinamiche)", "🔎 Query Builder"])
    
    with t1:
        tipo_stat = st.radio("Cosa vuoi analizzare?", ["Squadra", "Giocatore"], horizontal=True)
        nome_target = st.text_input(f"Inserisci il nome esatto della/del {tipo_stat.lower()}").lower().strip()
        
        if nome_target:
            # Trova tutte le leghe in cui il nome compare
            leghe_giocate = set()
            for p in db.get("partite", []):
                if tipo_stat == "Squadra":
                    if p["casa"].lower() == nome_target or p["trasferta"].lower() == nome_target:
                        leghe_giocate.add(p["lega"])
                else:
                    if trova_squadra_giocatore(p, nome_target):
                        leghe_giocate.add(p["lega"])
            
            if not leghe_giocate:
                st.warning(f"Nessun dato trovato per '{nome_target}'. Assicurati di aver inserito il nome correttamente.")
            else:
                col_filtri1, col_filtri2 = st.columns(2)
                lega_filtro = col_filtri1.selectbox("Seleziona Lega", ["Tutte le competizioni"] + list(leghe_giocate))
                filtro_campo = col_filtri2.radio("Filtro Campo", ["Tutte", "Solo in Casa", "Solo in Trasferta"], horizontal=True)
                
                if st.button("Calcola Statistiche"):
                    if tipo_stat == "Squadra":
                        gf, gs, match = 0, 0, 0
                        elenco_partite = []
                        for p in db.get("partite", []):
                            if lega_filtro != "Tutte le competizioni" and p["lega"] != lega_filtro: continue
                            
                            is_casa = p["casa"].lower() == nome_target
                            is_trasf = p["trasferta"].lower() == nome_target
                            
                            if not is_casa and not is_trasf: continue
                            if filtro_campo == "Solo in Casa" and not is_casa: continue
                            if filtro_campo == "Solo in Trasferta" and not is_trasf: continue
                            
                            match += 1
                            elenco_partite.append(p)
                            
                            for g in p["eventi"]["goal"]:
                                if g["squadra"].lower() == nome_target: gf += 1
                                else: gs += 1
                        
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Partite Giocate", match)
                        c2.metric("Goal Fatti", gf)
                        c3.metric("Goal Subiti", gs)
                        c4.metric("Differenza Reti", gf - gs)
                        
                        st.markdown("---")
                        st.subheader(f"Risultati registrati ({match})")
                        for p_item in elenco_partite:
                            st.write(f"🔹 **{p_item['lega']} (G {p_item.get('giornata','?')})**: {p_item['casa']} **{p_item.get('risultato','?')}** {p_item['trasferta']}")
                    
                    else: # GIOCATORE
                        match, titolare, sub, gol, assist, amm, esp = 0, 0, 0, 0, 0, 0, 0
                        autogol, rig_segnati, rig_sbagliati, rig_parati, gol_subiti = 0, 0, 0, 0, 0
                        ha_giocato_in_porta = False
                        
                        for p in db.get("partite", []):
                            if lega_filtro != "Tutte le competizioni" and p["lega"] != lega_filtro: continue
                            
                            sq_giocatore = trova_squadra_giocatore(p, nome_target)
                            if not sq_giocatore: continue
                            
                            sq_avversaria = p["trasferta"] if sq_giocatore == p["casa"] else p["casa"]
                            is_casa = sq_giocatore.lower() == p["casa"].lower()
                            
                            if filtro_campo == "Solo in Casa" and not is_casa: continue
                            if filtro_campo == "Solo in Trasferta" and is_casa: continue
                            
                            match += 1
                            
                            # Verifica Presenze e se ha giocato come Portiere
                            is_tit = False
                            is_portiere_oggi = False
                            for t in p["formazioni"].get(sq_giocatore, {}).get("titolari", []):
                                if t["nome"].lower().strip() == nome_target:
                                    is_tit = True
                                    if t.get("ruolo", "") == "Portiere":
                                        is_portiere_oggi = True
                                        ha_giocato_in_porta = True
                                    break
                                    
                            if is_tit: titolare += 1
                            else: sub += 1
                            
                            # Calcolo Goal Subiti per il portiere
                            if is_portiere_oggi:
                                gol_subiti += sum(1 for g in p["eventi"]["goal"] if g["squadra"] == sq_avversaria)
                            
                            # Calcolo Goal Fatti, Autogoal, Assist
                            for g in p["eventi"]["goal"]:
                                if g.get("marcatore", "").lower().strip() == nome_target:
                                    if g.get("autogoal"):
                                        autogol += 1
                                    else:
                                        gol += 1
                                        if g.get("rigore"): rig_segnati += 1
                                        
                                if g.get("assist", "").lower().strip() == nome_target and not g.get("autogoal"): 
                                    assist += 1
                            
                            # Calcolo Rigori Sbagliati o Parati
                            for rs in p["eventi"].get("rigori_sbagliati", []):
                                if rs["tiratore"].lower().strip() == nome_target:
                                    rig_sbagliati += 1
                                if is_portiere_oggi and rs["squadra"] == sq_avversaria and rs["esito"] == "Parato":
                                    rig_parati += 1
                            
                            # Cartellini
                            amm += sum(1 for a in p["eventi"].get("ammonizioni", []) if a.lower().strip() == nome_target)
                            esp += sum(1 for e in p["eventi"].get("espulsioni", []) if e.lower().strip() == nome_target)
                        
                        st.subheader(f"Statistiche Individuali")
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Presenze (Tit/Sub)", f"{match} ({titolare}/{sub})")
                        c2.metric("Goal (di cui Rig)", f"{gol} ({rig_segnati})")
                        c3.metric("Assist", assist)
                        c4.metric("Autogoal", autogol)
                        
                        st.write("") # Spazio vuoto
                        
                        c5, c6, c7, c8 = st.columns(4)
                        c5.metric("Cartellini (🟨/🟥)", f"{amm} / {esp}")
                        c6.metric("Rigori Sbagliati", rig_sbagliati)
                        
                        # Mostra statistiche da portiere SOLO se ha giocato in quel ruolo
                        if ha_giocato_in_porta:
                            c7.metric("Goal Subiti", gol_subiti)
                            c8.metric("Rigori Parati", rig_parati)
                        else:
                            c7.metric("Goal Subiti", "-")
                            c8.metric("Rigori Parati", "-")

    with t2:
        st.write("Imposta i filtri (lascia vuoto per ignorare)")
        with st.form("query_builder"):
            col1, col2 = st.columns(2)
            with col1:
                q_sq = st.text_input("Squadra target")
                q_res = st.text_input("Risultato esatto (es. 2-1)")
                q_esito = st.selectbox("Esito", ["Qualsiasi", "Vittoria", "Pareggio", "Sconfitta"])
                q_rimonta = st.checkbox("Solo partite in Rimonta")
            with col2:
                q_marcatore = st.text_input("Nome marcatore specifico")
                q_min_fascia = st.text_input("Fascia minuti goal (es. 1-20)")
                q_gol_tot = st.text_input("Minimo goal totali nel match (es. 3)")
            
            if st.form_submit_button("Esegui Query"):
                min_start, min_end = -1, -1
                if q_min_fascia:
                    try: min_start, min_end = map(int, q_min_fascia.split('-'))
                    except: st.error("Formato minuti errato (usa es. 1-20)")
                
                risultati_query = []
                for p in db.get("partite", []):
                    c, t = p["casa"], p["trasferta"]
                    if q_sq:
                        q_sq_l = q_sq.lower()
                        if c.lower() != q_sq_l and t.lower() != q_sq_l: continue
                    if q_res and p.get("risultato", "").split(" ")[0] != q_res: continue
                    if q_gol_tot and q_gol_tot.isdigit() and len(p["eventi"]["goal"]) < int(q_gol_tot): continue
                    
                    if q_sq and q_esito != "Qualsiasi":
                        gc = sum(1 for g in p["eventi"]["goal"] if g["squadra"] == c)
                        gt = sum(1 for g in p["eventi"]["goal"] if g["squadra"] == t)
                        is_c = (c.lower() == q_sq.lower())
                        vittoria = (is_c and gc>gt) or (not is_c and gt>gc)
                        pareggio = (gc == gt)
                        if q_esito == "Vittoria" and not vittoria: continue
                        if q_esito == "Pareggio" and not pareggio: continue
                        if q_esito == "Sconfitta" and (vittoria or pareggio): continue
                        
                    if q_rimonta:
                        def get_m(g):
                            try: return int(str(g.get("minuto","0")).split('+')[0].replace("'",""))
                            except: return 0
                        gol_ord = sorted(p["eventi"]["goal"], key=get_m)
                        c_temp, t_temp = 0, 0
                        c_sotto, t_sotto = False, False
                        for g in gol_ord:
                            if g["squadra"] == c: c_temp+=1 
                            else: t_temp+=1
                            if t_temp > c_temp: c_sotto = True
                            elif c_temp > t_temp: t_sotto = True
                        
                        r_casa = c_sotto and (c_temp >= t_temp)
                        r_trasf = t_sotto and (t_temp >= c_temp)
                        if q_sq:
                            is_c = (c.lower() == q_sq.lower())
                            if is_c and not r_casa: continue
                            if not is_c and not r_trasf: continue
                        elif not (r_casa or r_trasf): continue

                    if min_start != -1 or q_marcatore:
                        goal_valido = False
                        for g in p["eventi"]["goal"]:
                            if q_sq and g["squadra"].lower() != q_sq.lower(): continue
                            cond_m = True
                            if min_start != -1:
                                try:
                                    m_effettivo = int(str(g.get("minuto","0")).split('+')[0].replace("'",""))
                                    cond_m = (min_start <= m_effettivo <= min_end)
                                except: cond_m = False
                            cond_n = (g.get("marcatore","").lower().strip() == q_marcatore.lower().strip()) if q_marcatore else True
                            
                            if cond_m and cond_n:
                                goal_valido = True
                                break
                        if not goal_valido: continue
                            
                    risultati_query.append(p)
                    
                st.success(f"Trovate {len(risultati_query)} partite!")
                for p in risultati_query:
                    st.write(f"🔹 **{p['lega']} (G {p.get('giornata','?')})**: {p['casa']} {p.get('risultato','')} {p['trasferta']}")