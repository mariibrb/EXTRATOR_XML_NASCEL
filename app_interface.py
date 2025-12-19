import streamlit as st
import pandas as pd
from motor_fiscal import extrair_dados_xml, gerar_excel_final

st.set_page_config(page_title="Sentinela Fiscal", layout="wide")

# Título original com o Coração Laranja 🧡
st.title("🛡️ Sentinela Fiscal 🧡")
st.markdown("---")

# Seção 1: Upload de Notas Fiscais (XML)
st.subheader("1. Upload de Notas Fiscais (XML)")
col_xml_e, col_xml_s = st.columns(2)

with col_xml_e:
    xmls_ent = st.file_uploader("XMLs de Entrada (Compras)", type=['xml'], accept_multiple_files=True)
with col_xml_s:
    xmls_sai = st.file_uploader("XMLs de Saída (Vendas)", type=['xml'], accept_multiple_files=True)

st.markdown("---")

# Seção 2: Gerenciamento (Acrescentado conforme pedido)
st.subheader("2. Planilhas de Gerenciamento")
col_ger_e, col_ger_s = st.columns(2)

with col_ger_e:
    file_gerenc_ent = st.file_uploader("Upload Planilha Gerenc. Entradas", type=['xlsx'], key="ger_ent")
with col_ger_s:
    file_gerenc_sai = st.file_uploader("Upload Planilha Gerenc. Saídas", type=['xlsx'], key="ger_sai")

st.markdown("---")

if st.button("🚀 Processar e Gerar Relatório"):
    if not xmls_sai:
        st.error("Por favor, envie ao menos os XMLs de Saída para processar.")
    else:
        with st.spinner("Processando dados e gerando auditoria..."):
            # Extração dos dados dos XMLs
            df_e = extrair_dados_xml(xmls_ent, "ENTRADA") if xmls_ent else None
            df_s = extrair_dados_xml(xmls_sai, "SAIDA")
            
            # Geração do Excel Final mantendo as auditorias e as novas planilhas
            excel_binario = gerar_excel_final(df_e, df_s, file_gerenc_ent, file_gerenc_sai)
            
            st.success("Processamento concluído! 🧡")
            st.download_button(
                label="📥 Baixar Relatório Fiscal Completo",
                data=excel_binario,
                file_name="Auditoria_Fiscal_Sentinela.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
