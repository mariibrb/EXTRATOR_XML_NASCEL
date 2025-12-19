import streamlit as st
import pandas as pd
from datetime import datetime
# Importação corrigida para garantir que o Streamlit encontre o arquivo local
try:
    from motor_fiscal import AnalisadorFiscalConsolidado
except ImportError:
    st.error("Erro: O arquivo motor_fiscal.py não foi encontrado no servidor.")

def main():
    st.set_page_config(page_title="Sentinela Fiscal", layout="wide")
    st.title("🛡️ Sentinela Fiscal")

    file = st.file_uploader("Carregue a planilha", type="xlsx")

    if file:
        xls = pd.ExcelFile(file)
        # Lendo abas com segurança
        df_icms = pd.read_excel(xls, 'ICMS')
        df_pis = pd.read_excel(xls, 'PIS') if 'PIS' in xls.sheet_names else pd.DataFrame()
        df_cofins = pd.read_excel(xls, 'COFINS') if 'COFINS' in xls.sheet_names else pd.DataFrame()
        df_ipi = pd.read_excel(xls, 'IPI') if 'IPI' in xls.sheet_names else pd.DataFrame()

        # Chamando o motor
        analisador = AnalisadorFiscalConsolidado(df_icms, df_pis, df_cofins, df_ipi)
        resultado = (analisador.analisar_pis()
                               .analisar_cofins()
                               .analisar_ipi()
                               .consolidar_e_aprovar())

        st.subheader("Análise Consolidada (PIS/COFINS/IPI)")
        st.dataframe(resultado, use_container_width=True)

        # Download
        st.download_button("Baixar Resultados", resultado.to_csv(index=False), "analise.csv", "text/csv")

if __name__ == "__main__":
    main()
