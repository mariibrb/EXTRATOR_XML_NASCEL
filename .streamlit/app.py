import streamlit as st
import zipfile
import io
import os
import re
import pandas as pd
import random

# --- MOTOR DE IDENTIFICAÇÃO COMPLETO ---
def identify_xml_info(content_bytes, client_cnpj, file_name):
    client_cnpj_clean = "".join(filter(str.isdigit, str(client_cnpj))) if client_cnpj else ""
    resumo_nota = {
        "Arquivo": file_name, "Chave": "", "Tipo": "Outros", "Série": "0",
        "Número": 0, "Pasta": "RECEBIDOS_TERCEIROS/OUTROS", "Conteúdo": content_bytes
    }
    try:
        content_str = content_bytes.decode('utf-8', errors='ignore')
        match_ch = re.search(r'\d{44}', content_str)
        resumo_nota["Chave"] = match_ch.group(0) if match_ch else ""
        
        tag_lower = content_str.lower()
        d_type = "NF-e"
        if '<mod>65</mod>' in tag_lower: d_type = "NFC-e"
        elif '<infcte' in tag_lower: d_type = "CT-e"
        elif '<infmdfe' in tag_lower: d_type = "MDF-e"
        
        status = "NORMAIS"
        if '110111' in tag_lower: status = "CANCELADOS"
        elif '110110' in tag_lower: status = "CARTA_CORRECAO"
        elif '<inutnfe' in tag_lower or '<procinut' in tag_lower:
            status = "INUTILIZADOS"
            d_type = "Inutilizacoes"
            
        resumo_nota["Tipo"] = d_type
        s_match = re.search(r'<(?:serie|serie)>(\d+)</?:serie|serie>', content_str)
        resumo_nota["Série"] = s_match.group(1) if s_match else "0"
        n_match = re.search(r'<(?:nNF|nCT|nMDF|nNFIni)>(\d+)</(?:nNF|nCT|nMDF|nNFIni)>', content_str)
        resumo_nota["Número"] = int(n_match.group(1)) if n_match else 0
        
        emit_match = re.search(r'<(?:emit|infInut|detEvento)>.*?<CNPJ>(\d+)</CNPJ>', content_str, re.DOTALL)
        cnpj_emit = emit_match.group(1) if emit_match else ""
        
        is_p = False
        if client_cnpj_clean:
            if cnpj_emit == client_cnpj_clean: is_p = True
            elif resumo_nota["Chave"] and client_cnpj_clean in resumo_nota["Chave"][6:20]: is_p = True
            
        if is_p:
            resumo_nota["Pasta"] = f"EMITIDOS_CLIENTE/{d_type}/{status}/Serie_{resumo_nota['Série']}"
        else:
            resumo_nota["Pasta"] = f"RECEBIDOS_TERCEIROS/{d_type}"
            
        return resumo_nota, is_p
    except:
        return resumo_nota, False

# --- CONFIGURAÇÃO E BLINDAGEM ---
st.set_page_config(page_title="O Garimpeiro", layout="wide", page_icon="⛏️")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden !important;} footer {visibility: hidden !important;} header {visibility: hidden !important;}
    .stApp { background-color: #f7f3f0; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #EADBC8 0%, #D2B48C 100%) !important; border-right: 3px solid #b8860b; }
    [data-testid="stSidebar"] * { color: #2b1e16 !important; font-weight: 900 !important; }
    h1, h2, h3, h4, p, label { color: #2b1e16 !important; font-family: 'Playfair Display', serif; font-weight: 900 !important; }
    .stDownloadButton > button {
        background: linear-gradient(180deg, #fcf6ba 0%, #d4af37 40%, #aa771c 100%) !important;
        color: #2b1e16 !important; border: 2px solid #8a6d3b !important;
        padding: 20px !important; font-weight: 900 !important; font-size: 18px !important;
        border-radius: 15px !important; width: 100% !important; text-transform: uppercase !important;
    }
    .gold-item { position: fixed; top: -50px; z-index: 9999; pointer-events: none; animation: drop 3.5s linear forwards; }
    @keyframes drop { 0% { transform: translateY(0) rotate(0deg); opacity: 1; } 100% { transform: translateY(110vh) rotate(720deg); opacity: 0; } }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>⛏️ O GARIMPEIRO</h1>", unsafe_allow_html=True)

# ESTADO INICIAL
if 'confirmado' not in st.session_state: st.session_state['confirmado'] = False
if 'garimpo_ok' not in st.session_state: st.session_state['garimpo_ok'] = False

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### ⛏️ Painel de Extração")
    raw_cnpj = st.text_input("CNPJ DO CLIENTE", placeholder="Digite os números")
    cnpj_limpo = "".join(filter(str.isdigit, raw_cnpj))
    if len(cnpj_limpo) == 14:
        if st.button("✅ LIBERAR OPERAÇÃO"):
            st.session_state['confirmado'] = True
            st.rerun()
    st.divider()
    if st.button("🗑️ RESETAR"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# --- ÁREA PRINCIPAL ---
if st.session_state['confirmado']:
    if not st.session_state['garimpo_ok']:
        uploaded_files = st.file_uploader("Arraste seus XMLs ou ZIPs:", accept_multiple_files=True)
        if uploaded_files:
            if st.button("🚀 INICIAR GRANDE GARIMPO"):
                processed_keys, relatorio_lista, sequencias = set(), [], {}
                buf_org, buf_todos = io.BytesIO(), io.BytesIO()
                
                with st.status("Minerando...", expanded=True) as status:
                    with zipfile.ZipFile(buf_org, "w") as z_org, zipfile.ZipFile(buf_todos, "w") as z_todos:
                        for f in uploaded_files:
                            f_bytes = f.read()
                            contents = []
                            if f.name.lower().endswith('.zip'):
                                with zipfile.ZipFile(io.BytesIO(f_bytes)) as z_in:
                                    for name in z_in.namelist():
                                        if name.lower().endswith('.xml'): contents.append((name, z_in.read(name)))
                            else: contents.append((f.name, f_bytes))

                            for name, xml_data in contents:
                                res, is_p = identify_xml_info(xml_data, cnpj_limpo, name)
                                key = res["Chave"] if len(res["Chave"]) == 44 else name
                                if key not in processed_keys:
                                    processed_keys.add(key)
                                    z_org.writestr(f"{res['Pasta']}/{name}", xml_data)
                                    z_todos.writestr(f"TODOS/{name}", xml_data)
                                    relatorio_lista.append(res)
                                    if is_p and res["Número"] > 0 and "EMITIDOS" in res["Pasta"]:
                                        s_key = (res["Tipo"], res["Série"])
                                        if s_key not in sequencias: sequencias[s_key] = set()
                                        sequencias[s_key].add(res["Número"])
                
                # Relatório de Faltantes
                faltantes = []
                for (t, s), nums in sequencias.items():
                    if len(nums) > 1:
                        ideal = set(range(min(nums), max(nums) + 1))
                        for b in sorted(list(ideal - nums)):
                            faltantes.append({"Documento": t, "Série": s, "Nº Faltante": b})

                st.session_state.update({
                    'zip_org': buf_org.getvalue(),
                    'zip_todos': buf_todos.getvalue(),
                    'relatorio': relatorio_lista,
                    'faltantes': pd.DataFrame(faltantes),
                    'garimpo_ok': True
                })
                st.rerun()
    else:
        # RESULTADOS
        icons = ["💰", "✨", "💎"]
        rain = "".join([f'<div class="gold-item" style="left:{random.randint(0,95)}%; animation-delay:{random.uniform(0,2)}s;">{random.choice(icons)}</div>' for i in range(30)])
        st.markdown(rain, unsafe_allow_html=True)
        
        st.success(f"⛏️ Garimpo Finalizado! {len(st.session_state['relatorio'])} pepitas encontradas.")
        
        # OS DOIS BOTÕES QUE VOCÊ PEDIU
        st.markdown("### 📥 EXTRAIR RESULTADOS")
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("📦 BAIXAR TODOS (PASTA ÚNICA)", st.session_state['zip_todos'], "TODOS.zip", "application/zip", use_container_width=True)
            st.caption("Pasta única 'TODOS' com todos os XMLs.")
        with c2:
            st.download_button("📂 BAIXAR GARIMPO FINAL (ORGANIZADO)", st.session_state['zip_org'], "garimpo_final.zip", "application/zip", use_container_width=True)
            st.caption("Organizado por Tipo/Série/Status.")

        st.divider()
        
        # PENEIRA DE BUSCA INDIVIDUAL
        st.markdown("### 🔍 PENEIRA INDIVIDUAL")
        df_res = pd.DataFrame(st.session_state['relatorio'])
        busca = st.text_input("Número ou Chave:")
        if busca:
            filtro = df_res[df_res['Número'].astype(str).str.contains(busca) | df_res['Chave'].str.contains(busca)]
            for _, row in filtro.iterrows():
                st.download_button(f"📥 XML Nº {row['Número']}", row['Conteúdo'], row['Arquivo'], key=f"dl_{row['Chave']}_{random.random()}")

        # RELATÓRIO DE FALTANTES
        st.markdown("### ⚠️ AUDITORIA DE SEQUÊNCIA")
        df_f = st.session_state['faltantes']
        if not df_f.empty: st.dataframe(df_f, use_container_width=True, hide_index=True)
        else: st.success("Mina íntegra! Nenhuma nota faltante.")

        if st.button("⛏️ NOVO GARIMPO"):
            st.session_state['garimpo_ok'] = False
            st.rerun()
