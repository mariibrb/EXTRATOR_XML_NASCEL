import streamlit as st
import os
import io
import pandas as pd
from motor_fiscal import extrair_dados_xml, gerar_excel_final

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Nascel | Auditoria", page_icon="🧡", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Quicksand', sans-serif; }
    .stApp { background-color: #F7F7F7; }
    h1, h2, h3, h4 { color: #FF6F00 !important; font-weight: 700; }
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
        background-color: white; padding: 20px; border-radius: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    .stButton>button { background-color: #FF6F00; color: white; border-radius: 25px; font-weight: bold; width: 100%; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    if os.path.exists(".streamlit/nascel sem fundo.png"):
        st.image(".streamlit/nascel sem fundo.png", use_container_width=True)
    st.markdown("---")
    st.subheader("📥 Baixar Modelos")
    st.button("📂 Modelo ICMS") # Exemplo simplificado
    st.markdown("---")
    st.subheader("📤 Atualizar Bases")
    st.file_uploader("Atualizar Base ICMS", type=['xlsx'], key='up_i')

# --- ÁREA CENTRAL ---
c1, c2, c3 = st.columns([3, 4, 3])
with c2:
    if os.path.exists(".streamlit/Sentinela.png"):
        st.image(".streamlit/Sentinela.png", use_container_width=True)

st.markdown("---")
col_ent, col_sai = st.columns(2, gap="large")

with col_ent:
    st.markdown("### 📥 1. Entradas")
    xml_ent = st.file_uploader("📂 XMLs", type='xml', accept_multiple_files=True, key="main_ue")
    aut_ent = st.file_uploader("🔍 Autenticidade", type=['xlsx'], key="main_ae")

with col_sai:
    st.markdown("### 2. Saídas")
    xml_sai = st.file_uploader("📂 XMLs", type='xml', accept_multiple_files=True, key="main_us")
    as_ = st.file_uploader("🔍 Autenticidade", type=['xlsx'], key="main_as")

# --- BOTÃO DE EXECUÇÃO ---
if st.button("🚀 EXECUTAR AUDITORIA COMPLETA", type="primary", use_container_width=True):
    with st.spinner("Processando..."):
        df_e = extrair_dados_xml(xml_ent, "Entrada")
        df_s = extrair_dados_xml(xml_sai, "Saída")
        excel_data = gerar_excel_final(df_e, df_s)
        
        st.success("Auditoria Concluída!")
        st.download_button("💾 BAIXAR RELATÓRIO", excel_data, "Auditoria_Nascel.xlsx")
