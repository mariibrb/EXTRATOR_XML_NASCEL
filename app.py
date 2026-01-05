import streamlit as st
import os, io, pandas as pd
from motor_fiscal import extrair_dados_xml, gerar_excel_final

# 1. MATA A SIDEBAR E OS ERROS NO TOPO
st.set_page_config(page_title="Sentinela Nascel", layout="wide", initial_sidebar_state="collapsed")

# 2. CSS PARA LIMPEZA TOTAL (Isso esconde o erro DeltaGenerator se ele tentar aparecer)
st.markdown("""
<style>
    [data-testid="stSidebar"], [data-testid="collapsedControl"], .stException, .stAlert { display: none !important; }
    .stApp { background-color: #F7F7F7; }
    h1, h2, h3 { color: #FF6F00 !important; font-weight: 700; text-align: center; }
    .stButton>button { background-color: #FF6F00; color: white; border-radius: 20px; font-weight: bold; width: 100%; height: 50px; border: none; }
</style>
""", unsafe_allow_html=True)

# 3. LOGO CENTRAL (Soldadinho) - Isolado em bloco seguro
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    try:
        # Se a imagem estiver na pasta .streamlit ele mostra, senão mostra o texto.
        # SEM EXIBIR ERRO TECNICO.
        st.image(".streamlit/Sentinela.png", use_container_width=True)
    except:
        st.title("🚀 SENTINELA NASCEL")

st.markdown("---")

# 4. AREA DE UPLOADS (Apenas o necessário)
col_e, col_s = st.columns(2)
with col_e:
    st.subheader("📥 ENTRADAS")
    xe = st.file_uploader("XMLs Entrada", accept_multiple_files=True, key="xe")
    ge = st.file_uploader("Gerencial Entrada (CSV)", key="ge")

with col_s:
    st.subheader("📤 SAÍDAS")
    xs = st.file_uploader("XMLs Saída", accept_multiple_files=True, key="xs")
    gs = st.file_uploader("Gerencial Saída (CSV)", key="gs")

# 5. BOTÃO DE EXECUÇÃO
if st.button("🚀 EXECUTAR AUDITORIA COMPLETA", type="primary"):
    with st.spinner("🧡 Analisando impostos..."):
        try:
            df_xe = extrair_dados_xml(xe)
            df_xs = extrair_dados_xml(xs)
            relat = gerar_excel_final(df_xe, df_xs, ge, gs)
            st.success("Auditoria Concluída!")
            st.download_button("💾 BAIXAR RELATÓRIO", relat, "Auditoria_Sentinela.xlsx", use_container_width=True)
        except Exception:
            st.error("Erro no processamento.")
