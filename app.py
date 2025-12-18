import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import io
import re
import os

st.set_page_config(page_title="Sentinela Fiscal Pro", layout="wide")

# Título Principal
st.title("🛡️ Sentinela Fiscal: Auditoria Inteligente")
st.markdown("---")

# --- 1. CARREGAR BASES MESTRE (CONFIGURAÇÃO INTERNA) ---
@st.cache_data
def carregar_bases_mestre():
    caminho_mestre = "Sentinela_MIRÃO_Outubro2025.xlsx"
    if os.path.exists(caminho_mestre):
        xls = pd.ExcelFile(caminho_mestre)
        df_gerencial = pd.read_excel(xls, 'Entradas Gerencial', dtype=str)
        df_tribut = pd.read_excel(xls, 'Bases Tribut', dtype=str)
        return df_gerencial, df_tribut
    return None, None

df_gerencial, df_tribut = carregar_bases_mestre()

# --- 2. FUNÇÃO DE EXTRAÇÃO (PADRÃO POWER QUERY) ---
def extrair_tags_estilo_query(xml_content):
    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    try:
        root = ET.fromstring(xml_content)
    except: return []
    
    infNFe = root.find('.//nfe:infNFe', ns)
    chave = infNFe.attrib['Id'][3:] if infNFe is not None else ""
    ide = root.find('.//nfe:ide', ns)
    emit = root.find('.//nfe:emit', ns)
    dest = root.find('.//nfe:dest', ns)
    
    itens = []
    for det in root.findall('.//nfe:det', ns):
        prod = det.find('nfe:prod', ns)
        imposto = det.find('nfe:imposto', ns)
        
        registro = {
            "Natureza Operação": ide.find('nfe:natOp', ns).text if ide is not None else "",
            "Número NF": ide.find('nfe:nNF', ns).text if ide is not None else "",
            "Finalidade": ide.find('nfe:finNFe', ns).text if ide is not None else "",
            "UF Emit": emit.find('nfe:enderEmit/nfe:UF', ns).text if emit is not None else "",
            "CNPJ Emit": emit.find('nfe:CNPJ', ns).text if emit is not None else "",
            "UF Dest": dest.find('nfe:enderDest/nfe:UF', ns).text if dest is not None else "",
            "dest.CPF": dest.find('nfe:CPF', ns).text if dest is not None and dest.find('nfe:CPF', ns) is not None else "",
            "dest.CNPJ": dest.find('nfe:CNPJ', ns).text if dest is not None and dest.find('nfe:CNPJ', ns) is not None else "",
            "nItem": det.attrib['nItem'],
            "Cód Prod": prod.find('nfe:cProd', ns).text if prod is not None else "",
            "Desc Prod": prod.find('nfe:xProd', ns).text if prod is not None else "",
            "NCM": prod.find('nfe:NCM', ns).text if prod is not None else "",
            "CFOP": prod.find('nfe:CFOP', ns).text if prod is not None else "",
            "vProd": float(prod.find('nfe:vProd', ns).text) if prod is not None else 0.0,
            "CST ICMS": imposto.find('.//nfe:CST', ns).text if imposto.find('.//nfe:CST', ns) is not None else "",
            "Chave de Acesso": chave
        }
        itens.append(registro)
    return itens

# --- 3. MENU LATERAL DE UPLOAD COM EXPLICAÇÕES ---
with st.sidebar:
    st.header("📂 Central de Upload")
    st.info("Siga a ordem abaixo para processar os dados:")
    
    st.subheader("1. Vendas")
    xml_saidas = st.file_uploader("Suba aqui os XMLs de SAÍDA", accept_multiple_files=True, type='xml')
    
    st.subheader("2. Compras")
    xml_entradas = st.file_uploader("Suba aqui os XMLs de ENTRADA", accept_multiple_files=True, type='xml')
    
    st.subheader("3. Autenticidade")
    rel_status = st.file_uploader("Relatório de Status (Chave na A, Status na F)", type=['xlsx', 'csv'])

# --- 4. PROCESSAMENTO ---
if (xml_saidas or xml_entradas) and rel_status:
    # Carregar Relatório de Autenticidade
    df_status_rel = pd.read_excel(rel_status, dtype=str) if rel_status.name.endswith('.xlsx') else pd.read_csv(rel_status, dtype=str)
    # Limpa chaves do relatório
    chaves_limpas = df_status_rel.iloc[:, 0].str.replace(r'\D', '', regex=True)
    status_dict = dict(zip(chaves_limpas, df_status_rel.iloc[:, 5]))

    # Processar Saídas
    df_saida = pd.DataFrame()
    if xml_saidas:
        dados_saida = []
        for f in xml_saidas: dados_saida.extend(extrair_tags_estilo_query(f.read()))
        df_saida = pd.DataFrame(dados_saida)
        df_saida['AP'] = df_saida['Chave de Acesso'].str.replace(r'\D', '', regex=True).map(status_dict).fillna("Pendente")
        df_saida['Tipo'] = "SAÍDA"

    # Processar Entradas
    df_entrada = pd.DataFrame()
    if xml_entradas:
        dados_entrada = []
        for f in xml_entradas: dados_entrada.extend(extrair_tags_estilo_query(f.read()))
        df_entrada = pd.DataFrame(dados_entrada)
        df_entrada['AP'] = df_entrada['Chave de Acesso'].str.replace(r'\D', '', regex=True).map(status_dict).fillna("Pendente")
        df_entrada['Tipo'] = "ENTRADA"

    # Criar Base_XML (Consolidada)
    df_base = pd.concat([df_saida, df_entrada], ignore_index=True)

    # --- LÓGICA DA COLUNA ANÁLISE CST (IGUAL AO SEU EXCEL) ---
    if df_tribut is not None:
        map_tribut = dict(zip(df_tribut.iloc[:, 0], df_tribut.iloc[:, 2]))
        map_gerencial = dict(zip(df_gerencial.iloc[:, 0], df_gerencial.iloc[:, 1]))

        def analisar_cst(row):
            status = str(row['AP'])
            cst_xml = str(row['CST ICMS']).strip()
            ncm = str(row['NCM']).strip()
            if "Cancelamento" in status: return "NF cancelada"
            esperado = map_tribut.get(ncm)
            if not esperado: return "NCM não encontrado"
            if cst_xml == "60":
                if map_gerencial.get(ncm) == "60": return "Correto"
                return f"Divergente — CST informado: 60 | Esperado: {esperado}"
            if cst_xml != esperado:
                return f"Divergente — CST informado: {cst_xml} | Esperado: {esperado}"
            return "Correto"

        df_base['Análise CST ICMS'] = df_base.apply(analisar_cst, axis=1)

    # --- EXIBIÇÃO E DOWNLOAD ---
    st.success("Tudo pronto! As abas foram geradas com sucesso.")
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        if not df_saida.empty: df_saida.to_excel(writer, index=False, sheet_name='Saídas')
        if not df_entrada.empty: df_entrada.to_excel(writer, index=False, sheet_name='Entradas')
        df_base.to_excel(writer, index=False, sheet_name='Base_XML')
        df_base.to_excel(writer, index=False, sheet_name='ICMS')

    st.download_button(
        label="📥 Baixar Sentinela Completa (Saídas, Entradas, Base e ICMS)",
        data=buffer.getvalue(),
        file_name="Sentinela_Resultado_Final.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
