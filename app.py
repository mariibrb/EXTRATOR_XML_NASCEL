import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import io

st.set_page_config(page_title="Sentinela - Extração Base_XML", layout="wide")
st.title("📑 Extração Bruta de XML (Padrão Power Query)")

def extrair_tags_query(xml_content):
    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    try:
        root = ET.fromstring(xml_content)
    except Exception:
        return []

    infNFe = root.find('.//nfe:infNFe', ns)
    chave = infNFe.attrib['Id'][3:] if infNFe is not None else ""
    ide = root.find('.//nfe:ide', ns)
    emit = root.find('.//nfe:emit', ns)
    dest = root.find('.//nfe:dest', ns)
    total = root.find('.//nfe:total/nfe:ICMSTot', ns)

    itens = []
    for det in root.findall('.//nfe:det', ns):
        prod = det.find('nfe:prod', ns)
        imposto = det.find('nfe:imposto', ns)
        
        registro = {
            "Chave de Acesso": chave,
            "Número NF": ide.find('nfe:nNF', ns).text if ide is not None else "",
            "Série": ide.find('nfe:serie', ns).text if ide is not None else "",
            "Data Emissão": ide.find('nfe:dhEmi', ns).text[:10] if ide is not None else "",
            "Natureza da Operação": ide.find('nfe:natOp', ns).text if ide is not None else "",
            "Modelo": ide.find('nfe:mod', ns).text if ide is not None else "",
            "CNPJ Emitente": emit.find('nfe:CNPJ', ns).text if emit is not None else "",
            "Nome Emitente": emit.find('nfe:xNome', ns).text if emit is not None else "",
            "UF Emitente": emit.find('.//nfe:UF', ns).text if emit is not None else "",
            "CNPJ/CPF Destinatário": (dest.find('nfe:CNPJ', ns).text if dest.find('nfe:CNPJ', ns) is not None else dest.find('nfe:CPF', ns).text) if dest is not None else "",
            "Nome Destinatário": dest.find('nfe:xNome', ns).text if dest is not None else "",
            "UF Destinatário": dest.find('.//nfe:UF', ns).text if dest is not None else "",
            "Item": det.attrib['nItem'],
            "Código Produto": prod.find('nfe:cProd', ns).text if prod is not None else "",
            "Descrição": prod.find('nfe:xProd', ns).text if prod is not None else "",
            "NCM": prod.find('nfe:NCM', ns).text if prod is not None else "",
            "CFOP": prod.find('nfe:CFOP', ns).text if prod is not None else "",
            "Unidade": prod.find('nfe:uCom', ns).text if prod is not None else "",
            "Quantidade": float(prod.find('nfe:qCom', ns).text) if prod is not None else 0.0,
            "Valor Unitário": float(prod.find('nfe:vUnCom', ns).text) if prod is not None else 0.0,
            "Valor Total Produto": float(prod.find('nfe:vProd', ns).text) if prod is not None else 0.0,
            "CST ICMS": imposto.find('.//nfe:CST', ns).text if imposto.find('.//nfe:CST', ns) is not None else "",
            "Valor Total Nota": float(total.find('nfe:vNF', ns).text) if total is not None else 0.0
        }
        itens.append(registro)
    return itens

files = st.file_uploader("Suba seus XMLs", accept_multiple_files=True, type='xml')

if files:
    all_data = []
    bar = st.progress(0)
    for i, f in enumerate(files):
        all_data.extend(extrair_tags_query(f.read()))
        bar.progress((i + 1) / len(files))
    
    if all_data:
        df = pd.DataFrame(all_data)
        st.dataframe(df)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Base_XML')
        st.download_button("📥 Baixar Base_XML", output.getvalue(), "Base_XML.xlsx")
