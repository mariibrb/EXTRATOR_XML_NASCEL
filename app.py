import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import io
import re
import os

st.set_page_config(page_title="Sentinela Fiscal Pro", layout="wide")
st.title("🛡️ Sentinela: Auditoria ICMS (Saídas vs Regras de Entrada)")

# --- 1. CARREGAR BASES MESTRE ---
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

# --- 2. FUNÇÃO DE EXTRAÇÃO ---
def extrair_tags(xml_content):
    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    try:
        root = ET.fromstring(xml_content)
    except: return []
    infNFe = root.find('.//nfe:infNFe', ns)
    chave = infNFe.attrib['Id'][3:] if infNFe is not None else ""
    ide, emit, dest = root.find('.//nfe:ide', ns), root.find('.//nfe:emit', ns), root.find('.//nfe:dest', ns)
    itens = []
    for det in root.findall('.//nfe:det', ns):
        prod, imposto = det.find('nfe:prod', ns), det.find('nfe:imposto', ns)
        registro = {
            "Natureza Operação": ide.find('nfe:natOp', ns).text if ide is not None else "",
            "Número NF": ide.find('nfe:nNF', ns).text if ide is not None else "",
            "UF Emit": emit.find('nfe:enderEmit/nfe:UF', ns).text if emit is not None else "",
            "UF Dest": dest.find('nfe:enderDest/nfe:UF', ns).text if dest is not None else "",
            "nItem": det.attrib['nItem'],
            "Desc Prod": prod.find('nfe:xProd', ns).text if prod is not None else "",
            "NCM": prod.find('nfe:NCM', ns).text if prod is not None else "",
            "CFOP": prod.find('nfe:CFOP', ns).text if prod is not None else "",
            "vProd": float(prod.find('nfe:vProd', ns).text) if prod is not None else 0.0,
            "CST ICMS": imposto.find('.//nfe:CST', ns).text if imposto.find('.//nfe:CST', ns) is not None else "",
            "Chave de Acesso": chave
        }
        itens.append(registro)
    return itens

# --- 3. INTERFACE ---
with st.sidebar:
    st.header("📂 Upload")
    xml_saidas = st.file_uploader("1. Notas de SAÍDA", accept_multiple_files=True, type='xml')
    xml_entradas = st.file_uploader("2. Notas de ENTRADA", accept_multiple_files=True, type='xml')
    rel_status = st.file_uploader("3. Relatório Autenticidade", type=['xlsx', 'csv'])

# --- 4. PROCESSAMENTO ---
if (xml_saidas or xml_entradas) and rel_status:
    df_st_rel = pd.read_excel(rel_status, dtype=str) if rel_status.name.endswith('.xlsx') else pd.read_csv(rel_status, dtype=str)
    status_dict = dict(zip(df_st_rel.iloc[:, 0].str.replace(r'\D', '', regex=True), df_st_rel.iloc[:, 5]))

    # Gerar DataFrames de Entradas e Saídas
    list_s = []
    for f in xml_saidas: list_s.extend(extrair_tags(f.read()))
    df_saidas = pd.DataFrame(list_s)
    
    list_e = []
    for f in xml_entradas: list_e.extend(extrair_tags(f.read()))
    df_entradas = pd.DataFrame(list_e)

    # Adicionar Status AP
    if not df_saidas.empty: df_saidas['AP'] = df_saidas['Chave de Acesso'].str.replace(r'\D', '', regex=True).map(status_dict).fillna("Pendente")
    if not df_entradas.empty: df_entradas['AP'] = df_entradas['Chave de Acesso'].str.replace(r'\D', '', regex=True).map(status_dict).fillna("Pendente")

    # Criar Aba ICMS baseada nas Saídas
    df_icms = df_saidas.copy()
    if not df_icms.empty and df_tribut is not None:
        map_tribut = dict(zip(df_tribut.iloc[:, 0].astype(str), df_tribut.iloc[:, 2].astype(str)))
        map_gerencial = dict(zip(df_gerencial.iloc[:, 0].astype(str), df_gerencial.iloc[:, 1].astype(str)))

        def auditar_cst(row):
            status, cst_xml, ncm = str(row['AP']), str(row['CST ICMS']).strip(), str(row['NCM']).strip()
            if "Cancelamento" in status: return "NF cancelada"
            
            cst_esperado_final = map_tribut.get(ncm)
            cst_entrada_gerencial = map_gerencial.get(ncm)
            
            if not cst_esperado_final: return "NCM não encontrado"

            # SE o produto entra como 60 (ST), ele não deve sair com débito de ICMS (00, 10, 20 etc)
            if cst_entrada_gerencial == "60" and cst_xml != "60":
                return f"Divergente — CST informado: {cst_xml} | Esperado: 60 (Produto com ST na Entrada)"
            
            # Validação padrão contra Bases Tribut
            if cst_xml != cst_esperado_final:
                return f"Divergente — CST informado: {cst_xml} | Esperado: {cst_esperado_final}"
            
            return "Correto"

        df_icms['Análise CST ICMS'] = df_icms.apply(auditar_cst, axis=1)

    # --- DOWNLOAD ---
    st.success("Relatório pronto! Abas: Entradas, Saídas e ICMS.")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        if not df_entradas.empty: df_entradas.to_excel(writer, index=False, sheet_name='Entradas')
        if not df_saidas.empty: df_saidas.to_excel(writer, index=False, sheet_name='Saídas')
        df_icms.to_excel(writer, index=False, sheet_name='ICMS')

    st.download_button("📥 Baixar Sentinela Auditada", buffer.getvalue(), "Sentinela_Fiscal.xlsx")
