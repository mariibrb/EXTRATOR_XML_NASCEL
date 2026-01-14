import streamlit as st
import zipfile
import io
import os
import xml.etree.ElementTree as ET
import re
import pandas as pd
import random

# --- MOTOR DE IDENTIFICAÇÃO (MANTIDO) ---
def identify_xml_info(content_bytes, client_cnpj, file_name):
    client_cnpj_clean = "".join(filter(str.isdigit, str(client_cnpj))) if client_cnpj else ""
    resumo_nota = {
        "Arquivo": file_name, "Chave": "", "Tipo": "Outros", "Série": "0",
        "Número": 0, "Data": "", "Valor": 0.0, "CNPJ_Emit": "",
        "Pasta": "RECEBIDOS_TERCEIROS/OUTROS", "Conteúdo": content_bytes
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
        if '<procevento' in tag_lower or '<revento' in tag_lower:
            status = "EVENTOS_CANCELAMENTOS"
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
        resumo_nota["CNPJ_Emit"] = emit_match.group(1) if emit_match else ""
        is_p = False
        if client_cnpj_clean:
            if resumo_nota["CNPJ_Emit"] == client_cnpj_clean: is_p = True
            elif resumo_nota["Chave"] and client_cnpj_clean in resumo_nota["Chave"][6:20]: is_p = True
        if is_p:
            resumo_nota["Pasta"] = f"EMITIDOS_CLIENTE/{d_type}/{status}/Serie_{resumo_nota['Série']}"
        else:
            resumo_nota["Pasta"] = f"RECEBIDOS_TERCEIROS/{d_type}"
        return resumo_nota, is_p
    except:
        return resumo_nota, False

def process_zip_recursively(file_bytes, zf_output, processed_keys, sequencias, relatorio_lista, client_cnpj):
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            for info in z.infolist():
                if info.is_dir(): continue
                content = z.read(info.filename)
                if info.filename.lower().endswith('.zip'):
                    process_zip_recursively(content, zf_output, processed_keys, sequencias, relatorio_lista, client_cnpj)
                elif info.filename.lower().endswith('.xml'):
                    resumo, is_p = identify_xml_info(content, client_cnpj, info.filename)
                    ident = resumo["Chave"] if len(resumo["Chave"]) == 44 else f"{resumo['Pasta']}_{resumo['Número']}_{info.filename}"
                    if ident not in processed_keys:
                        processed_keys.add(ident)
                        zf_output.writestr(f"{resumo['Pasta']}/{info.filename}", content)
                        relatorio_lista.append(resumo)
                        if is_p and resumo["Número"] > 0 and "EMITIDOS" in resumo["Pasta"]:
                            if resumo["Tipo"] in ["NF-e", "NFC-e", "CT-e", "MDF-e"]:
                                s_key = (resumo["Tipo"], resumo["Série"])
                                if s_key not in sequencias: sequencias[s_key] = set()
                                sequencias[s_key].add(resumo["Número"])
    except: pass

def format_cnpj(cnpj):
    cnpj = "".join(filter(str.isdigit, cnpj))
    if len(cnpj) > 14: cnpj = cnpj[:14]
    if len(cnpj) <= 2: return cnpj
    if len(cnpj) <= 5: return f"{cnpj[:2]}.{cnpj[2:]}"
    if len(cnpj) <= 8: return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:]}"
    if len(cnpj) <= 12: return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:]}"
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"

# --- DESIGN PREMIUM E BLINDAGEM AGRESSIVA ---
st.set_page_config(page_title="O Garimpeiro", layout="wide", page_icon="⛏️")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header {visibility: hidden !important;}
    .stDeployButton, .stAppDeployButton { display: none !important; visibility: hidden !important; }
    .stApp { background-color: #f7f3f0; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #EADBC8 0%, #D2B48C 100%) !important; border-right: 3px solid #b8860b; }
    [data-testid="stSidebar"] * { color: #2b1e16 !important; font-weight: 800 !important; }
    [data-testid="stSidebar"] div.stButton > button { background: linear-gradient(180deg, #fcf6ba 0%, #d4af37 100%) !important; color: #2b1e16 !important; border: 2px solid #8a6d3b !important; font-weight: 900 !important; }
    h1, h2, h3, h4, p, label, .stMetric label { color: #2b1e16 !important; font-family: 'Playfair Display', serif; font-weight: 800 !important; }
    h1 { font-size: 3.5rem !important; text-shadow: 2px 2px 0px #fff; }
    [data-testid="stMetric"] { background: linear-gradient(135deg, #ffffff 0%, #fff9e6 100%); border: 2px solid #d4af37; border-radius: 20px; padding: 25px; box-shadow: 8px 8px 20px rgba(0,0,0,0.12); }
    [data-testid="stMetricValue"] { color: #a67c00 !important; font-weight: 900 !important; font-size: 2.5rem !important; }
    
    /* ESTILO DOS BOTÕES DE DOWNLOAD */
    div.stDownloadButton > button {
        background: linear-gradient(180deg, #fcf6ba 0%, #d4af37 40%, #aa771c 100%) !important;
        color: #2b1e16 !important;
        border: 2px solid #8a6d3b !important;
        padding: 20px 10px !important;
        font-size: 18px !important;
        font-weight: 900 !important;
        border-radius: 15px !important;
        width: 100% !important;
        text-transform: uppercase !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2) !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>⛏️ O GARIMPEIRO</h1>", unsafe_allow_html=True)

# INICIALIZAÇÃO DE ESTADO
if 'confirmado' not in st.session_state: st.session_state['confirmado'] = False
if 'garimpo_ok' not in st.session_state: st.session_state['garimpo_ok'] = False

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### ⛏️ Painel de Extração")
    raw_cnpj = st.text_input("CNPJ DO CLIENTE", placeholder="Digite os números")
    cnpj_limpo = "".join(filter(str.isdigit, raw_cnpj))
    if len(cnpj_limpo) == 14:
        st.markdown(f"**CLIENTE ATIVO:**\n`{format_cnpj(raw_cnpj)}`")
        if st.button("✅ LIBERAR OPERAÇÃO"):
            st.session_state['confirmado'] = True
            st.rerun()
    st.divider()
    if st.button("🗑️ RESETAR SISTEMA"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# --- ÁREA DE TRABALHO ---
if not st.session_state['confirmado']:
    st.info("💰 Para iniciar, identifique o CNPJ no menu lateral e clique em **LIBERAR OPERAÇÃO**.")
else:
    if not st.session_state['garimpo_ok']:
        st.markdown(f"### 📦 JAZIDA DE ARQUIVOS: {format_cnpj(raw_cnpj)}")
        uploaded_files = st.file_uploader("Arraste seus XMLs ou ZIPs aqui:", accept_multiple_files=True)

        if uploaded_files:
            if st.button("🚀 INICIAR GRANDE GARIMPO"):
                processed_keys, sequencias, relatorio_lista = set(), {}, []
                
                # ZIP ORGANIZADO
                buf_org = io.BytesIO()
                with zipfile.ZipFile(buf_org, "w", zipfile.ZIP_DEFLATED) as zf:
                    for f in uploaded_files:
                        f_bytes = f.read()
                        if f.name.lower().endswith('.zip'):
                            process_zip_recursively(f_bytes, zf, processed_keys, sequencias, relatorio_lista, cnpj_limpo)
                        elif f.name.lower().endswith('.xml'):
                            resumo, is_p = identify_xml_info(f_bytes, cnpj_limpo, f.name)
                            ident = resumo["Chave"] if len(resumo["Chave"]) == 44 else f.name
                            if ident not in processed_keys:
                                processed_keys.add(ident)
                                zf.writestr(f"{resumo['Pasta']}/{f.name}", f_bytes)
                                relatorio_lista.append(resumo)
                                if is_p and resumo["Número"] > 0 and "EMITIDOS" in resumo["Pasta"]:
                                    if resumo["Tipo"] in ["NF-e", "NFC-e", "CT-e", "MDF-e"]:
                                        s_key = (resumo["Tipo"], resumo["Série"])
                                        if s_key not in sequencias: sequencias[s_key] = set()
                                        sequencias[s_key].add(resumo["Número"])
                
                # ZIP TODOS (PASTA TODOS/)
                buf_todos = io.BytesIO()
                with zipfile.ZipFile(buf_todos, "w", zipfile.ZIP_DEFLATED) as zf_t:
                    for item in relatorio_lista:
                        zf_t.writestr(f"TODOS/{item['Arquivo']}", item['Conteúdo'])

                # SALVAR NO ESTADO
                st.session_state.update({
                    'zip_org': buf_org.getvalue(),
                    'zip_todos': buf_todos.getvalue(),
                    'relatorio': relatorio_lista,
                    'garimpo_ok': True
                })
                st.rerun()

    else:
        # --- EXIBIÇÃO DOS RESULTADOS (SÓ APARECE DEPOIS DO GARIMPO) ---
        st.success("✅ Mineração concluída com sucesso!")
        
        df_res = pd.DataFrame(st.session_state['relatorio'])
        c1, c2 = st.columns(2)
        c1.metric("📦 TOTAL DE XMLs", len(df_res))
        c2.metric("✨ NOTAS DO CLIENTE", len(df_res[df_res['Pasta'].str.contains("EMITIDOS")]))

        st.divider()
        st.markdown("### 📥 ESCOLHA SEU TESOURO")
        
        # OS DOIS BOTÕES LADO A LADO
        col_down1, col_down2 = st.columns(2)
        
        with col_down1:
            st.markdown("**📂 MODELO ORGANIZADO**")
            st.caption("Arquivos separados por pastas (Emitidas/Recebidas)")
            st.download_button(
                label="📥 BAIXAR GARIMPO FINAL",
                data=st.session_state['zip_org'],
                file_name="garimpo_final.zip",
                mime="application/zip",
                use_container_width=True
            )

        with col_down2:
            st.markdown("**📦 MODELO TODOS**")
            st.caption("Tudo dentro de uma única pasta chamada 'TODOS'")
            st.download_button(
                label="📥 BAIXAR TODOS",
                data=st.session_state['zip_todos'],
                file_name="TODOS.zip",
                mime="application/zip",
                use_container_width=True
            )

        st.divider()
        if st.button("⛏️ NOVO GARIMPO"):
            st.session_state['garimpo_ok'] = False
            st.rerun()
