import streamlit as st
import os, io, pandas as pd
from motor_fiscal import extrair_dados_xml, gerar_excel_final

# 1. Configuração da Página - Forçando a Sidebar a aparecer (expanded)
st.set_page_config(page_title="Sentinela Nascel", page_icon="🧡", layout="wide", initial_sidebar_state="expanded")

# 2. Estilo CSS Nascel (Removido o display:none da sidebar)
st.markdown("""
<style>
    .stApp { background-color: #F7F7F7; }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1.5px solid #FF6F00; display: block !important; }
    h1, h2, h3 { color: #FF6F00 !important; font-weight: 700; text-align: center; }
    .stButton>button { background-color: #FF6F00; color: white; border-radius: 20px; font-weight: bold; width: 100%; height: 50px; border: none; }
    .stFileUploader { border: 1px dashed #FF6F00; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 3. LADO ESQUERDO (SIDEBAR RESTAURADA) ---
with st.sidebar:
    logo_nascel = ".streamlit/nascel sem fundo.png"
    if os.path.exists(logo_nascel):
        st.image(logo_nascel, use_container_width=True)
    
    st.markdown("---")
    st.subheader("🔄 Bases de Dados")
    st.file_uploader("Base ICMS", type=['xlsx'], key='base_icms_sidebar')
    st.file_uploader("Base PIS/COFINS", type=['xlsx'], key='base_pc_sidebar')
    
    st.markdown("---")
    st.subheader("📥 Download Modelos")
    m_buf = io.BytesIO()
    pd.DataFrame().to_excel(m_buf)
    st.download_button("Gabarito PIS/COFINS", m_buf.getvalue(), "modelo_piscofins.xlsx", use_container_width=True)
    st.download_button("Gabarito IPI", m_buf.getvalue(), "modelo_ipi.xlsx", use_container_width=True)

# --- 4. TELA PRINCIPAL ---
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    soldado_img = ".streamlit/Sentinela.png"
    if os.path.exists(soldado_img):
        st.image(soldado_img, use_container_width=True)
    else:
        st.title("🚀 SENTINELA NASCEL")

st.markdown("---")

col_e, col_s = st.columns(2, gap="large")

with col_e:
    st.subheader("📥 FLUXO ENTRADAS")
    xml_e = st.file_uploader("📂 XMLs Entrada", type='xml', accept_multiple_files=True, key="xe_input")
    ger_e = st.file_uploader("📊 Gerencial Entrada (CSV)", type=['csv'], key="ge_input")
    aut_e = st.file_uploader("🔍 Autenticidade Entrada", type=['xlsx'], key="ae_input")

with col_s:
    st.subheader("📤 FLUXO SAÍDAS")
    xml_s = st.file_uploader("📂 XMLs Saída", type='xml', accept_multiple_files=True, key="xs_input")
    ger_s = st.file_uploader("📊 Gerencial Saída (CSV)", type=['csv'], key="gs_input")
    aut_s = st.file_uploader("🔍 Autenticidade Saída", type=['xlsx'], key="as_input")

st.markdown("<br>", unsafe_allow_html=True)

if st.button("🚀 EXECUTAR AUDITORIA COMPLETA", type="primary"):
    with st.spinner("🧡 O Sentinela está auditando seus dados..."):
        try:
            df_xe = extrair_dados_xml(xml_e)
            df_xs = extrair_dados_xml(xml_s)
            
            relatorio = gerar_excel_final(df_xe, df_xs, ger_e, ger_s, aut_e, aut_s)
            
            st.success("Auditoria concluída com sucesso! 🧡")
            st.download_button("💾 BAIXAR RELATÓRIO FINAL", relatorio, "Auditoria_Sentinela.xlsx", use_container_width=True)
        except Exception as e:
            st.error(f"Erro: {e}")
