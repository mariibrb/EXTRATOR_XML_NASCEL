import streamlit as st
import os, io, pandas as pd
from motor_fiscal import extrair_dados_xml, gerar_excel_final

# Configuração da página - Matando a Sidebar de vez
st.set_page_config(page_title="Sentinela Nascel", page_icon="🧡", layout="wide", initial_sidebar_state="collapsed")

# CSS para garantir que a sidebar suma e a tela fique limpa
st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none !important; }
    .stApp { background-color: #F7F7F7; }
    h1, h2, h3 { color: #FF6F00 !important; font-weight: 700; text-align: center; }
    .stButton>button { background-color: #FF6F00; color: white; border-radius: 20px; font-weight: bold; width: 100%; height: 50px; border: none; }
    .stFileUploader { border: 1px dashed #FF6F00; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# Logo Centralizado
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
    xml_e = st.file_uploader("📂 XMLs", type='xml', accept_multiple_files=True, key="xe")
    ger_e = st.file_uploader("📊 Gerencial (CSV)", type=['csv'], key="ge")

with col_sai:
    st.subheader("📤 SAÍDAS")
    xml_s = st.file_uploader("📂 XMLs ", type='xml', accept_multiple_files=True, key="xs")
    ger_s = st.file_uploader("📊 Gerencial (CSV) ", type=['csv'], key="gs")

st.markdown("<br>", unsafe_allow_html=True)

if st.button("🚀 EXECUTAR AUDITORIA COMPLETA", type="primary"):
    with st.spinner("🧡 Processando..."):
        try:
            df_xe = extrair_dados_xml(xml_e)
            df_xs = extrair_dados_xml(xml_s)
            relatorio = gerar_excel_final(df_xe, df_xs, ger_e, ger_s)
            st.success("Concluído!")
            st.download_button("💾 BAIXAR RELATÓRIO", relatorio, "Auditoria.xlsx", use_container_width=True)
        except Exception as e:
            st.error(f"Erro: {e}")
