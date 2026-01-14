import streamlit as st
import zipfile
import io
import os
import xml.etree.ElementTree as ET
import re
import pandas as pd
import gc

# --- MOTOR DE IDENTIFICAÇÃO (INTOCADO) ---
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
                        if is_p and resumo["Número"] > 0:
                            if resumo["Tipo"] != "Inutilizacoes":
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

# --- DESIGN PREMIUM GOLD RUSH ---
st.set_page_config(page_title="O Garimpeiro XML", layout="wide", page_icon="⛏️")

st.markdown("""
    <style>
    /* Fundo Elegante */
    .stApp { background: linear-gradient(180deg, #ffffff 0%, #f3e5ab 100%); }
    
    h1 { color: #8e6e1e !important; font-family: 'Playfair Display', serif; font-weight: 900; text-align: center; font-size: 3rem; margin-bottom: 0px; }
    
    /* Botão Gold */
    div.stButton > button:first-child {
        background: linear-gradient(145deg, #bf953f, #fcf6ba, #b38728, #fbf5b7, #aa771c);
        color: #4a3701; border: none; padding: 18px 50px; font-size: 22px; font-weight: 800; border-radius: 12px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.15); transition: all 0.4s ease; text-transform: uppercase; letter-spacing: 2px;
    }
    div.stButton > button:first-child:hover { transform: translateY(-3px); box-shadow: 0 15px 25px rgba(184, 134, 11, 0.4); border: 1px solid #fff; }

    /* Efeito de Chuva de Ouro */
    .gold-rain {
        position: fixed; top: -50px; width: 25px; height: 25px;
        background: radial-gradient(circle, #fff700 0%, #b8860b 100%);
        border-radius: 50%; box-shadow: 0 0 10px #ffd700;
        z-index: 9999; pointer-events: none;
        animation: fall linear forwards;
    }

    @keyframes fall {
        to { transform: translateY(110vh) rotate(360deg); }
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1>⛏️ O GARIMPEIRO</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #5d4037; font-size: 1.2rem;'>A arte de minerar arquivos e descobrir tesouros fiscais.</p>", unsafe_allow_html=True)

if 'garimpo_ok' not in st.session_state: st.session_state['garimpo_ok'] = False

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### ✨ Perfil da Mina")
    raw_cnpj = st.text_input("CNPJ do Cliente", placeholder="00.000.000/0001-00")
    cnpj_limpo = "".join(filter(str.isdigit, raw_cnpj))
    if raw_cnpj:
        st.markdown(f"**Identificado:** `{format_cnpj(raw_cnpj)}`")
    
    st.divider()
    if st.button("🗑️ Abandonar Jazida"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()
    st.caption("v7.5 | Gold Rush Edition")

# --- ÁREA DE UPLOAD ---
if len(cnpj_limpo) < 14:
    st.warning("⚠️ **Atenção:** Identifique o CNPJ da mina no menu lateral para liberar o maquinário.")
else:
    st.markdown(f"### 🏺 Escavação: {format_cnpj(raw_cnpj)}")
    uploaded_files = st.file_uploader("Solte aqui o material bruto (XML ou ZIP):", accept_multiple_files=True)

    if uploaded_files:
        if st.button("🚀 INICIAR GRANDE GARIMPO", use_container_width=True):
            processed_keys, sequencias, relatorio_lista = set(), {}, []
            zip_buffer = io.BytesIO()
            
            with st.status("💎 Lavando o cascalho e separando o ouro...", expanded=True) as status:
                prog_bar = st.progress(0)
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
                        prog_bar.progress((i + 1) / total)
                    
                    faltantes_lista = []
                    for (t, s), nums in sequencias.items():
                        if nums:
                            ideal = set(range(min(nums), max(nums) + 1))
                            for b in sorted(list(ideal - nums)):
                                faltantes_lista.append({"Tipo": t, "Série": s, "Nº Faltante": b})
                    st.session_state['df_faltantes'] = pd.DataFrame(faltantes_lista) if faltantes_lista else None
                
                status.update(label="💰 Tesouro encontrado!", state="complete", expanded=False)

            if relatorio_lista:
                st.session_state.update({'relatorio': relatorio_lista, 'zip_completo': zip_buffer.getvalue(), 'garimpo_ok': True})
                
                # SCRIPT PARA CHUVA DE OURO
                gold_script = ""
                for i in range(50):
                    left = i * 2
                    delay = i * 0.1
                    size = 15 + (i % 15)
                    gold_script += f'<div class="gold-rain" style="left:{left}%; width:{size}px; height:{size}px; animation-duration:{2+delay%2}s; animation-delay:{delay}s;"></div>'
                st.markdown(gold_script, unsafe_allow_html=True)

# --- RESULTADOS ---
if st.session_state.get('garimpo_ok'):
    st.divider()
    df_res = pd.DataFrame(st.session_state['relatorio'])
    
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("📦 Volume Extraído", f"{len(df_res)} itens")
    col_m2.metric("✨ Ouro Puro (Emitidas)", f"{len(df_res[df_res['Pasta'].str.contains('EMITIDOS')])}")
    col_m3.metric("🕳️ Falhas na Escavação", f"{len(st.session_state['df_faltantes']) if st.session_state['df_faltantes'] is not None else 0}")

    c_v1, c_v2 = st.columns(2)
    with c_v1:
        st.markdown("#### 📂 Estrutura de Armazenamento")
        st.dataframe(df_res['Pasta'].value_counts().reset_index().rename(columns={'Pasta': 'Caminho', 'count': 'Qtd'}), use_container_width=True, hide_index=True)
    with c_v2:
        st.markdown("#### ⚠️ Buracos no Sequencial")
        if st.session_state['df_faltantes'] is not None:
            st.dataframe(st.session_state['df_faltantes'], use_container_width=True, hide_index=True)
        else:
            st.success("Mina 100% íntegra. Sem falhas de sequência!")

    st.divider()
    st.download_button("📥 RECOLHER TODO O TESOURO (.ZIP)", st.session_state['zip_completo'], "garimpo_gold_rush.zip", use_container_width=True)
