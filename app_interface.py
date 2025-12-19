import streamlit as st
import pandas as pd
from motor_fiscal import extrair_dados_xml, gerar_excel_final

st.set_page_config(page_title="Sentinela Fiscal", layout="wide")

# Menu Lateral (Sidebar) mais delicado
with st.sidebar:
    st.title("🛡️ Sentinela 🧡")
    st.markdown("---")
    
    st.subheader("1. Notas Fiscais (XML)")
    xmls_ent = st.file_uploader("Entradas (Compras)", type=['xml'], accept_multiple_files=True)
    xmls_sai = st.file_uploader("Saídas (Vendas)", type=['xml'], accept_multiple_files=True)
    
    st.markdown("---")
    
    st.subheader("2. Gerenciamento")
    file_gerenc_ent = st.file_uploader("Gerenc. Entradas", type=['xlsx'], key="ger_ent")
    file_gerenc_sai = st.file_uploader("Gerenc. Saídas", type=['xlsx'], key="ger_sai")
    
    st.markdown("---")
    processar = st.button("🚀 Processar Relatório")

# Área Principal
st.title("🛡️ Sentinela Fiscal 🧡")
st.info("Aguardando o processamento dos arquivos via menu lateral.")

if processar:
    if not xmls_sai:
        st.error("Por favor, envie ao menos os XMLs de Saída no menu lateral.")
    else:
        with st.spinner("Processando auditoria... 🧡"):
            # Extração dos dados
            df_e = extrair_dados_xml(xmls_ent, "ENTRADA") if xmls_ent else None
            df_s = extrair_dados_xml(xmls_sai, "SAIDA")
            
            # Geração do Excel Final
            excel_binario = gerar_excel_final(df_e, df_s, file_gerenc_ent, file_gerenc_sai)
            
            st.success("Processamento concluído com sucesso! 🧡")
            st.download_button(
                label="📥 Baixar Relatório Fiscal Completo",
                data=excel_binario,
                file_name="Auditoria_Fiscal_Sentinela.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
