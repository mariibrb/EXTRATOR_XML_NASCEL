import pandas as pd
import numpy as np
from datetime import datetime
import io

def extrair_dados_xml(xml_files, tipo, df_autenticidade=None):
    """
    Simulação da extração de dados (Mantenha sua lógica original de leitura de XML aqui).
    Esta função deve retornar um DataFrame com as colunas necessárias.
    """
    # Exemplo de estrutura que sua função atual gera:
    data = {
        'id_item': range(len(xml_files)) if xml_files else [],
        'produto': [f"Item {i}" for i in range(len(xml_files))],
        'valor_item': [1000.0] * len(xml_files),
        'base_calculo': [1000.0] * len(xml_files),
        'valor_icms': [180.0] * len(xml_files),
        'aliquota_pis': [1.65] * len(xml_files),
        'valor_pis_xml': [16.5] * len(xml_files),
        'aliquota_cofins': [7.6] * len(xml_files),
        'valor_cofins_xml': [76.0] * len(xml_files),
        'aliquota_ipi': [5.0] * len(xml_files),
        'valor_ipi_xml': [50.0] * len(xml_files)
    }
    return pd.DataFrame(data)

def gerar_excel_final(df_e, df_s):
    """
    Cria o Excel com as abas separadas e a coluna de ANÁLISE em cada uma.
    """
    output = io.BytesIO()
    
    # Unificando para análise
    df_full = pd.concat([df_e, df_s], ignore_index=True)
    
    # --- PROCESSAMENTO PIS ---
    df_pis = df_full.copy()
    df_pis['PIS_ESPERADO'] = df_pis['base_calculo'] * (df_pis['aliquota_pis'] / 100)
    df_pis['ANALISE_PIS'] = np.where(
        abs(df_pis['PIS_ESPERADO'] - df_pis['valor_pis_xml']) < 0.01, 
        "CORRETO", "DIVERGENTE (REVISAR)"
    )

    # --- PROCESSAMENTO COFINS ---
    df_cofins = df_full.copy()
    df_cofins['COFINS_ESPERADO'] = df_cofins['base_calculo'] * (df_cofins['aliquota_cofins'] / 100)
    df_cofins['ANALISE_COFINS'] = np.where(
        abs(df_cofins['COFINS_ESPERADO'] - df_cofins['valor_cofins_xml']) < 0.01, 
        "CORRETO", "DIVERGENTE (REVISAR)"
    )

    # --- PROCESSAMENTO IPI ---
    df_ipi = df_full.copy()
    df_ipi['IPI_ESPERADO'] = df_ipi['base_calculo'] * (df_ipi['aliquota_ipi'] / 100)
    df_ipi['ANALISE_IPI'] = np.where(
        abs(df_ipi['IPI_ESPERADO'] - df_ipi['valor_ipi_xml']) < 0.01, 
        "CORRETO", "DIVERGENTE (REVISAR)"
    )

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_full.to_excel(writer, sheet_name='RESUMO_GERAL', index=False)
        df_pis.to_excel(writer, sheet_name='PIS', index=False)
        df_cofins.to_excel(writer, sheet_name='COFINS', index=False)
        df_ipi.to_excel(writer, sheet_name='IPI', index=False)
        
    return output.getvalue()
