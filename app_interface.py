import streamlit as st
import os, io, pandas as pd
from motor_fiscal import extrair_dados_xml, gerar_excel_final

# 1. Configuração da página (Sidebar colapsada)
st.set_page_config(page_title="Sentinela Nascel", page_icon="🧡", layout="wide", initial_sidebar_state="collapsed")

# 2. CSS para esconder a Sidebar e estilizar a página
st.markdown("""
<style>
    /* Esconde a barra lateral permanentemente */
    [data-testid="stSidebar"] { display: none; }
    section[data-testid="stSidebarNav"] { display: none; }
    
    .stApp { background-color: #F7F7F7; }
    h1, h2, h3 { color: #FF6F00 !important; font-weight: 700; text-align: center; }
    .stButton>button { background-color: #FF6F00; color: white; border-radius: 20px; font-weight: bold; width: 100%; height: 50px; border: none; }
    .stFileUploader { border: 1px dashed #FF6F00; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 3. TELA PRINCIPAL (CENTRO) ---
# Logo Nascel / Soldadinho Centralizado
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    if os.path.exists(".streamlit/Sentinela.png"):
        st.image(".streamlit/Sentinela.png", use_container_width=True)
    else:
        st.title("🚀 SENTINELA NASCEL")

st.markdown("---")

# Seção de Fluxos
col_ent, col_sai = st.columns(2, gap="large")

with col_ent:
    st.subheader("📥 FLUXO DE ENTRADAS")
    xml_e = st.file_uploader("📂 XMLs de Entrada", type='xml', accept_multiple_files=True, key="xe_main")
    ger_e = st.file_uploader("📊 Gerencial Entrada", type=['csv'], key="ge_main")
    aut_e = st.file_uploader("🔍 Autenticidade Entrada", type=['xlsx'], key="ae_main")

with col_sai:
    st.subheader("📤 FLUXO DE SAÍDAS")
    xml_s = st.file_uploader("📂 XMLs de Saída", type='xml', accept_multiple_files=True, key="xs_main")
    ger_s = st.file_uploader("📊 Gerencial Saída", type=['csv'], key="gs_main")
    aut_s = st.file_uploader("🔍 Autenticidade Saída", type=['xlsx'], key="as_main")

st.markdown("<br>", unsafe_allow_html=True)

if st.button("🚀 EXECUTAR AUDITORIA COMPLETA", type="primary"):
    with st.spinner("🧡 O Sentinela está auditando seus dados..."):
        try:
            df_xe = extrair_dados_xml(xml_e)
            df_xs = extrair_dados_xml(xml_s)
            relat = gerar_excel_final(df_xe, df_xs, ger_e, ger_s, aut_e, aut_s)
            st.success("Análise concluída com sucesso! 🧡")
            st.download_button("💾 BAIXAR RELATÓRIO", relat, "Auditoria_Final.xlsx", use_container_width=True)
        except Exception as e:
            st.error(f"Erro no processamento: {e}")
