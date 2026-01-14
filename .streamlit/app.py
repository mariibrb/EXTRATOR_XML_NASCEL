import streamlit as st
import zipfile
import io
import os
import xml.etree.ElementTree as ET
import re
import pandas as pd
import gc

# --- MOTOR DE IDENTIFICAÇÃO (PRESERVADO) ---
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
                        if is_p and resumo["Número"] > 0 and resumo["Tipo"] != "Inutilizacoes":
                            doc_base = "NFC-e" if "NFC-e" in resumo["Pasta"] else ("NF-e" if "NF-e" in resumo["Pasta"] else resumo["Tipo"])
                            s_key = (doc_base, resumo["Série"])
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

# --- DESIGN PREMIUM (ESTILO IMAGEM + SIDEBAR DOURADA) ---
st.set_page_config(page_title="O Garimpeiro", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    /* Background Geral Champagne */
    .stApp { background: linear-gradient(180deg, #FFFFFF 0%, #D2B48C 100%); }
    
    /* Sidebar Douradinha Unificada */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FFFFFF 0%, #E6BE8A 100%);
        border-right: 2px solid #B8860B;
    }
    [data-testid="stSidebar"] * { color: #5D4037 !important; font-weight: 600; }

    /* Títulos */
    h1 { color: #5D4037 !important; font-family: 'Playfair Display', serif; font-weight: 800; text-align: center; }

    /* Botão Dourado Superior */
    div.stButton > button:first-child {
        background: linear-gradient(180deg, #FCEABB 0%, #F8B500 50%, #BB9B32 100%);
        color: #3D2B1F !important; border: 1px solid #8B4513;
        padding: 15px 40px; font-size: 20px; font-weight: bold; border-radius: 30px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3); transition: 0.3s;
    }
    div.stButton > button:first-child:hover { transform: scale(1.02); box-shadow: 0 6px 20px rgba(184, 134, 11, 0.5); }

    /* CHUVA DE OURO REALISTA */
    .gold-item {
        position: fixed; top: -50px; z-index: 9999;
        pointer-events: none; animation: drop 3s linear forwards;
        font-size: 30px;
    }
    @keyframes drop {
        0% { transform: translateY(0) rotate(0deg); opacity: 1; }
        100% { transform: translateY(110vh) rotate(720deg); opacity: 0; }
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1>⛏️ O GARIMPEIRO</h1>", unsafe_allow_html=True)

if 'garimpo_ok' not in st.session_state: st.session_state['garimpo_ok'] = False

with st.sidebar:
    st.markdown("### 💎 Mina de Dados")
    raw_cnpj = st.text_input("CNPJ do Cliente", placeholder="00.000.000/0001-00")
    cnpj_limpo = "".join(filter(str.isdigit, raw_cnpj))
    if raw_cnpj: st.markdown(f"**Identificado:** \n`{format_cnpj(raw_cnpj)}`")
    st.divider()
    if st.button("Resetar Tudo"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

if len(cnpj_limpo) < 14:
    st.info("⚠️ Identifique o CNPJ para começar a minerar.")
else:
    st.markdown(f"### 📥 Jazida: {format_cnpj(raw_cnpj)}")
    uploaded_files = st.file_uploader("Suba seus arquivos:", accept_multiple_files=True)

    if uploaded_files:
        if st.button("🚀 INICIAR GARIMPO"):
            processed_keys, sequencias, relatorio_lista = set(), {}, []
            zip_buffer = io.BytesIO()
            
            with st.status("🛠️ Lavando o cascalho...", expanded=True) as status:
                total = len(uploaded_files)
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf_final:
                    for i, file in enumerate(uploaded_files):
                        f_bytes = file.read()
                        if file.name.lower().endswith('.zip'):
                            process_zip_recursively(f_bytes, zf_final, processed_keys, sequencias, relatorio_lista, cnpj_limpo)
                        elif file.name.lower().endswith('.xml'):
                            resumo, is_p = identify_xml_info(f_bytes, cnpj_limpo, file.name)
                            ident = resumo["Chave"] if len(resumo["Chave"]) == 44 else file.name
                            if ident not in processed_keys:
                                processed_keys.add(ident)
                                zf_final.writestr(f"{resumo['Pasta']}/{file.name}", f_bytes)
                                relatorio_lista.append(resumo)
                                if is_p and resumo["Número"] > 0 and resumo["Tipo"] != "Inutilizacoes":
                                    doc_base = "NFC-e" if "NFC-e" in resumo["Pasta"] else ("NF-e" if "NF-e" in resumo["Pasta"] else resumo["Tipo"])
                                    s_key = (doc_base, resumo["Série"])
                                    if s_key not in sequencias: sequencias[s_key] = set()
                                    sequencias[s_key].add(resumo["Número"])
                status.update(label="✨ Garimpo Finalizado!", state="complete")

            if relatorio_lista:
                st.session_state.update({'relatorio': relatorio_lista, 'zip_completo': zip_buffer.getvalue(), 'garimpo_ok': True})
                
                # CHUVA DE OURO COM ÍCONES REAIS
                icons = ["💰", "🪙", "💎", "🥇", "✨"]
                rain_html = ""
                for i in range(60):
                    icon = icons[i % len(icons)]
                    left, delay = i * 1.6, i * 0.05
                    rain_html += f'<div class="gold-item" style="left:{left}%; animation-delay:{delay}s;">{icon}</div>'
                st.markdown(rain_html, unsafe_allow_html=True)

if st.session_state.get('garimpo_ok'):
    st.divider()
    df_res = pd.DataFrame(st.session_state['relatorio'])
    c1, c2, c3 = st.columns(3)
    c1.metric("📦 Minerados", f"{len(df_res)}")
    c2.metric("💎 Cliente", f"{len(df_res[df_res['Pasta'].str.contains('EMITIDOS')])}")
    st.download_button("📥 BAIXAR RESULTADO (.ZIP)", st.session_state['zip_completo'], "garimpo_v8.zip", use_container_width=True)
