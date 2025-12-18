import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import io
import re
import os

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(
    page_title="Nascel | Auditoria",
    page_icon="🧡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS PERSONALIZADO - AJUSTADO PARA DAR ESPAÇO NA LATERAL
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Quicksand', sans-serif; }
    .stApp { background-color: #F7F7F7; }
    
    /* Títulos e Containers */
    h1, h2, h3 { color: #FF6F00 !important; font-weight: 700; }
    div[data-testid="stSidebar"] { background-color: white !important; padding: 1rem !important; }
    
    /* Botões */
    .stButton>button { 
        background-color: #FF6F00; color: white; border-radius: 25px; 
        border: none; font-weight: bold; padding: 0.5rem 1rem; width: 100%;
    }
    .stButton>button:hover { background-color: #E65100; color: white; }
    
    /* File Uploader na Lateral para ficar compacto */
    [data-testid="stSidebar"] .stFileUploader { padding: 5px; border: 1px dashed #FFCC80; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# --- 2. FUNÇÕES DE SUPORTE ---
# ==============================================================================

def buscar_imagem(nome):
    caminhos = [f".streamlit/{nome}", nome, f"assets/{nome}"]
    for p in caminhos:
        if os.path.exists(p): return p
    return None

def get_base_path(nome):
    p = f".streamlit/{nome}" if os.path.exists(f".streamlit/{nome}") else nome
    return p if os.path.exists(p) else None

# ==============================================================================
# --- 3. SIDEBAR: ORGANIZAÇÃO SEM "CAGAR" O LAYOUT ---
# ==============================================================================
with st.sidebar:
    # Logo Nascel com verificação
    logo = buscar_imagem("nascel sem fundo.png")
    if logo:
        st.image(logo, use_container_width=True)
    else:
        st.markdown("<h2 style='text-align:center;'>NASCEL</h2>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- STATUS DAS BASES ---
    st.subheader("📊 Status")
    b_icms_path = get_base_path("base_icms.xlsx")
    b_pc_path = get_base_path("CST_Pis_Cofins.xlsx")
    
    col_status1, col_status2 = st.columns(2)
    with col_status1:
        if b_icms_path: st.success("ICMS OK")
        else: st.error("ICMS OFF")
    with col_status2:
        if b_pc_path: st.success("PIS/COF OK")
        else: st.error("PIS/COF OFF")

    st.markdown("---")

    # --- GERENCIAR BASES ---
    st.subheader("💾 Gerenciar Bases")
    with st.expander("⬆️ Subir Novas", expanded=False):
        up_i = st.file_uploader("Trocar ICMS (A-I)", type='xlsx', key='side_i')
        if up_i:
            with open("base_icms.xlsx", "wb") as f: f.write(up_i.getbuffer())
            st.rerun()
        up_p = st.file_uploader("Trocar PIS/COF", type='xlsx', key='side_p')
        if up_p:
            with open("CST_Pis_Cofins.xlsx", "wb") as f: f.write(up_p.getbuffer())
            st.rerun()

    # --- MODELOS (O QUE VOCÊ PEDIU) ---
    st.subheader("📂 Gabaritos")
    # Modelo ICMS
    df_micms = pd.DataFrame(columns=['NCM','DESC_I','CST_I','AL_I','RE_I','DESC_E','CST_E','AL_E','OBS'])
    buf_i = io.BytesIO()
    with pd.ExcelWriter(buf_i, engine='xlsxwriter') as w: df_micms.to_excel(w, index=False)
    st.download_button("📥 Gabarito ICMS", buf_i.getvalue(), "modelo_icms.xlsx")
    
    # Modelo PIS
    df_mpc = pd.DataFrame({'NCM': ['00000000'], 'CST_ENT': ['50'], 'CST_SAI': ['01']})
    buf_p = io.BytesIO()
    with pd.ExcelWriter(buf_p, engine='xlsxwriter') as w: df_mpc.to_excel(w, index=False)
    st.download_button("📥 Gabarito PIS/COF", buf_p.getvalue(), "modelo_pc.xlsx")

# ==============================================================================
# --- 4. ÁREA CENTRAL: O SENTINELA ---
# ==============================================================================

# Logo Sentinela Central
sentinela_png = buscar_imagem("Sentinela.png")
if sentinela_png:
    c1, c2, c3 = st.columns([3, 4, 3])
    with c2: st.image(sentinela_png, use_container_width=True)
else:
    st.markdown("<h1 style='text-align: center;'>SENTINELA</h1>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Container Principal de Uploads
with st.container():
    col_ent, col_sai = st.columns(2, gap="large")
    
    with col_ent:
        st.markdown("### 📥 1. Entradas")
        xml_e = st.file_uploader("📂 XMLs de Entrada", type='xml', accept_multiple_files=True, key="main_xe")
        aut_e = st.file_uploader("🔍 Autenticidade Entradas", type=['xlsx','csv'], key="main_ae")

    with col_sai:
        st.markdown("### 📤 2. Saídas")
        xml_s = st.file_uploader("📂 XMLs de Saída", type='xml', accept_multiple_files=True, key="main_xs")
        aut_s = st.file_uploader("🔍 Autenticidade Saídas", type=['xlsx','csv'], key="main_as")

st.markdown("<br>", unsafe_allow_html=True)

# --- BOTÃO DE AÇÃO ---
if st.button("🚀 EXECUTAR AUDITORIA COMPLETA", type="primary", use_container_width=True):
    if not xml_e and not xml_s:
        st.warning("Aguardando o upload dos XMLs para processar.")
    else:
        st.info("Lógica de processamento em execução... Os resultados aparecerão aqui.")
        # Aqui o código continua com a extração e o ExcelWriter para abas...
