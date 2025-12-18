import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import io

st.set_page_config(page_title="Sentinela - Auditoria AP", layout="wide")
st.title("🛡️ Sentinela: Extração + Auditoria de Status (Coluna AP)")

def extrair_tags_estilo_query(xml_content):
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

    itens_extraidos = []
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
            "dest.IE": dest.find('nfe:IE', ns).text if dest is not None and dest.find('nfe:IE', ns) is not None else "",
            "nItem": det.attrib['nItem'],
            "Cód Prod": prod.find('nfe:cProd', ns).text if prod is not None else "",
            "Desc Prod": prod.find('nfe:xProd', ns).text if prod is not None else "",
            "NCM": prod.find('nfe:NCM', ns).text if prod is not None else "",
            "CEST": prod.find('nfe:CEST', ns).text if prod is not None and prod.find('nfe:CEST', ns) is not None else "",
            "CFOP": prod.find('nfe:CFOP', ns).text if prod is not None else "",
            "vProd": float(prod.find('nfe:vProd', ns).text) if prod is not None else 0.0,
            "vDesc": float(prod.find('nfe:vDesc', ns).text) if prod is not None and prod.find('nfe:vDesc', ns) is not None else 0.0,
            "Origem": imposto.find('.//nfe:orig', ns).text if imposto.find('.//nfe:orig', ns) is not None else "",
            "CST ICMS": imposto.find('.//nfe:CST', ns).text if imposto.find('.//nfe:CST', ns) is not None else (imposto.find('.//nfe:CSOSN', ns).text if imposto.find('.//nfe:CSOSN', ns) is not None else ""),
            "BC ICMS": float(imposto.find('.//nfe:vBC', ns).text) if imposto.find('.//nfe:vBC', ns) is not None else 0.0,
            "Alq ICMS": float(imposto.find('.//nfe:pICMS', ns).text) if imposto.find('.//nfe:pICMS', ns) is not None else 0.0,
            "ICMS": float(imposto.find('.//nfe:vICMS', ns).text) if imposto.find('.//nfe:vICMS', ns) is not None else 0.0,
            "pRedBC ICMS": float(imposto.find('.//nfe:pRedBC', ns).text) if imposto.find('.//nfe:pRedBC', ns) is not None else 0.0,
            "BC ICMS-ST": float(imposto.find('.//nfe:vBCST', ns).text) if imposto.find('.//nfe:vBCST', ns) is not None else 0.0,
            "ICMS-ST": float(imposto.find('.//nfe:vICMSST', ns).text) if imposto.find('.//nfe:vICMSST', ns) is not None else 0.0,
            "FCPST": float(imposto.find('.//nfe:vFCPST', ns).text) if imposto.find('.//nfe:vFCPST', ns) is not None else 0.0,
            "CST IPI": imposto.find('.//nfe:IPI//nfe:CST', ns).text if imposto.find('.//nfe:IPI//nfe:CST', ns) is not None else "",
            "BC IPI": float(imposto.find('.//nfe:IPI//nfe:vBC', ns).text) if imposto.find('.//nfe:IPI//nfe:vBC', ns) is not None else 0.0,
            "Aliq IPI": float(imposto.find('.//nfe:IPI//nfe:pIPI', ns).text) if imposto.find('.//nfe:IPI//nfe:pIPI', ns) is not None else 0.0,
            "IPI": float(imposto.find('.//nfe:IPI//nfe:vIPI', ns).text) if imposto.find('.//nfe:IPI//nfe:vIPI', ns) is not None else 0.0,
            "CST PIS": imposto.find('.//nfe:PIS//nfe:CST', ns).text if imposto.find('.//nfe:PIS//nfe:CST', ns) is not None else "",
            "BC PIS": float(imposto.find('.//nfe:PIS
