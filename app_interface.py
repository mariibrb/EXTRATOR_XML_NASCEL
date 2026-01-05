import streamlit as st
import os, io, pandas as pd
from motor_fiscal import extrair_dados_xml, gerar_excel_final

# 1. Configuração de Página (Forçando ocultar Sidebar)
st.set_page_config(page_title="Sentinela Nascel", page_icon="🧡", layout="wide", initial_sidebar_state="collapsed")

# 2. CSS para eliminar a sidebar e limpar o erro DeltaGenerator
st.markdown("""
<style>
    [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
    .stApp { background-color: #F7F7F7; }
    h1, h2, h3 { color: #FF6F00 !important; font-weight: 700; text-align: center; }
    .stButton>button { background-color: #FF6F00; color: white; border-radius: 20px; font-weight: bold; width: 100%; height: 50px; border: none; }
    .stFileUploader { border: 1px dashed #FF6F00; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 3. TELA CENTRAL ---
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    # Exibição do Soldadinho de forma isolada (evita o erro Creator of Delta)
    logo_path = ".streamlit/Sentinela.png"
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
    else:
        st.title("🚀 SENTINELA NASCEL")

st.markdown("---")

# Seção de Uploads (Apenas os botões principais)
col_ent, col_sai = st.columns(2, gap="large")

with col_ent:
    st.subheader("📥 FLUXO DE ENTRADAS")
    xml_e = st.file_uploader("📂 XMLs de Entrada", type='xml', accept_multiple_files=True, key="xe_m")
    ger_e = st.file_uploader("📊 Gerencial Entrada", type=['csv'], key="ge_m")

with col_sai:
    st.subheader("📤 FLUXO DE SAÍDAS")
    xml_s = st.file_uploader("📂 XMLs de Saída", type='xml', accept_multiple_files=True, key="xs_m")
    ger_s = st.file_uploader("📊 Gerencial Saída", type=['csv'], key="gs_m")

st.markdown("<br>", unsafe_allow_html=True)

# Botão de Execução
if st.button("🚀 EXECUTAR AUDITORIA COMPLETA", type="primary"):
    with st.spinner("🧡 Analisando regras tributárias..."):
        try:
            df_xe = extrair_dados_xml(xml_e)
            df_xs = extrair_dados_xml(xml_s)
            relatorio = gerar_excel_final(df_xe, df_xs, ger_e, ger_s)
            st.success("Auditoria tributária concluída com sucesso! 🧡")
            st.download_button("💾 BAIXAR RELATÓRIO FINAL", relatorio, "Auditoria_Sentinela.xlsx", use_container_width=True)
        except Exception as e:
            st.error(f"Erro no processamento: {e}")
