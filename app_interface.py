import streamlit as st
import os, io, pandas as pd
from motor_fiscal import extrair_dados_xml, gerar_excel_final

# 1. Configuração de Página e Sidebar
st.set_page_config(page_title="Sentinela Nascel", page_icon="🧡", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background-color: #F7F7F7; }
    h1, h2, h3 { color: #FF6F00 !important; font-weight: 700; text-align: center; }
    .stButton>button { background-color: #FF6F00; color: white; border-radius: 20px; font-weight: bold; width: 100%; height: 50px; border: none; }
    .stFileUploader { border: 1px dashed #FF6F00; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# Prevenção de erro em botões vazios
def get_empty_data():
    buf = io.BytesIO()
    pd.DataFrame().to_excel(buf)
    return buf.getvalue()
empty_file = get_empty_data()

# --- 3. LADO ESQUERDO (SIDEBAR) ---
with st.sidebar:
    st.image(".streamlit/nascel sem fundo.png", use_container_width=True) if os.path.exists(".streamlit/nascel sem fundo.png") else st.title("Nascel")
    st.markdown("---")
    st.subheader("⚙️ Configurações de Base")
    with st.expander("🔄 Upload de Bases", expanded=False):
        st.file_uploader("Base ICMS", type=['xlsx'], key='s_icms')
        st.file_uploader("Base PIS/COFINS", type=['xlsx'], key='s_pc')
        if st.button("Salvar Bases"): st.success("Bases Atualizadas!")
    
    with st.expander("📥 Download de Bases", expanded=False):
        st.download_button("Base PIS/COFINS", empty_file, "base_pis_cofins.xlsx", use_container_width=True)
        st.download_button("Base IPI", empty_file, "base_ipi.xlsx", use_container_width=True)

# --- 4. TELA PRINCIPAL ---
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    if os.path.exists(".streamlit/Sentinela.png"):
        st.image(".streamlit/Sentinela.png", use_container_width=True)
    else:
        st.title("🚀 SENTINELA NASCEL")

st.markdown("---")
col_ent, col_sai = st.columns(2, gap="large")

with col_ent:
    st.subheader("📥 ENTRADAS")
    xml_e = st.file_uploader("📂 XMLs", type='xml', accept_multiple_files=True, key="main_xe")
    ger_e = st.file_uploader("📊 Gerencial (CSV)", type=['csv'], key="main_ge")
    aut_e = st.file_uploader("🔍 Autenticidade (XLSX)", type=['xlsx'], key="main_ae")

with col_sai:
    st.subheader("📤 SAÍDAS")
    xml_s = st.file_uploader("📂 XMLs", type='xml', accept_multiple_files=True, key="main_xs")
    ger_s = st.file_uploader("📊 Gerencial (CSV)", type=['csv'], key="main_gs")
    aut_s = st.file_uploader("🔍 Autenticidade (XLSX)", type=['xlsx'], key="main_as")

st.markdown("<br>", unsafe_allow_html=True)
if st.button("🚀 EXECUTAR AUDITORIA COMPLETA", type="primary"):
    with st.spinner("🧡 Cruzando dados fiscais..."):
        try:
            df_xe = extrair_dados_xml(xml_e)
            df_xs = extrair_dados_xml(xml_s)
            relatorio = gerar_excel_final(df_xe, df_xs, ger_e, ger_s, aut_e, aut_s)
            st.success("Auditoria concluída!")
            st.download_button("💾 BAIXAR RELATÓRIO", relatorio, "Relatorio_Sentinela.xlsx", use_container_width=True)
        except Exception as e:
            st.error(f"Erro: {e}")
