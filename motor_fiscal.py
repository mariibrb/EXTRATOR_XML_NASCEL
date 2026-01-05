import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
import re
import io

def extrair_dados_xml(files, fluxo="Saída"):
    dados_lista = []
    if not files: return pd.DataFrame()
    for f in files:
        try:
            f.seek(0)
            texto_xml = f.read().decode('utf-8', errors='replace')
            texto_xml = re.sub(r'<\?xml[^?]*\?>', '', texto_xml)
            texto_xml = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', texto_xml)
            root = ET.fromstring(texto_xml)
            
            def buscar(caminho, raiz=root):
                alvo = raiz.find(f'.//{caminho}')
                return alvo.text if alvo is not None and alvo.text is not None else ""

            inf_nfe = root.find('.//infNFe')
            chave_acesso = inf_nfe.attrib.get('Id', '')[3:] if inf_nfe is not None else ""
            emit = root.find('.//emit')
            dest = root.find('.//dest')
            
            for det in root.findall('.//det'):
                prod = det.find('prod')
                imp = det.find('imposto')
                ncm_limpo = re.sub(r'\D', '', buscar('NCM', prod)).zfill(8)
                
                linha = {
                    "CHAVE_ACESSO": chave_acesso,
                    "NUM_NF": buscar('nNF'),
                    "DATA_EMISSAO": buscar('dhEmi')[:10] if buscar('dhEmi') else "",
                    "CNPJ_EMIT": buscar('CNPJ', emit),
                    "UF_EMIT": buscar('UF', emit),
                    "CNPJ_DEST": buscar('CNPJ', dest),
                    "UF_DEST": buscar('UF', dest),
                    "ITEM": det.attrib.get('nItem', '0'),
                    "CFOP": buscar('CFOP', prod),
                    "NCM": ncm_limpo,
                    "COD_PROD": buscar('cProd', prod),
                    "DESCR": buscar('xProd', prod),
                    "UNID": buscar('uCom', prod),
                    "QTDE": float(buscar('qCom', prod) or 0),
                    "VUNIT": float(buscar('vUnCom', prod) or 0),
                    "VPROD": float(buscar('vProd', prod) or 0),
                    "CST-ICMS": "", "BC-ICMS": 0.0, "ALQ-ICMS": 0.0, "VLR-ICMS": 0.0,
                    "CST-PIS": "", "BC-PIS": 0.0, "VLR-PIS": 0.0,
                    "CST-COF": "", "BC-COF": 0.0, "VLR-COF": 0.0
                }

                if imp is not None:
                    icms = imp.find('.//ICMS')
                    if icms is not None:
                        for n in icms:
                            cst = n.find('CST') or n.find('CSOSN')
                            if cst is not None: linha["CST-ICMS"] = cst.text.zfill(2)
                            if n.find('vBC') is not None: linha["BC-ICMS"] = float(n.find('vBC').text)
                            if n.find('vICMS') is not None: linha["VLR-ICMS"] = float(n.find('vICMS').text)
                            if n.find('pICMS') is not None: linha["ALQ-ICMS"] = float(n.find('pICMS').text)
                    
                    for p in imp.findall('.//PIS'):
                        for item in p:
                            if item.find('CST') is not None: linha["CST-PIS"] = item.find('CST').text.zfill(2)
                            if item.find('vBC') is not None: linha["BC-PIS"] = float(item.find('vBC').text)
                            if item.find('vPIS') is not None: linha["VLR-PIS"] = float(item.find('vPIS').text)
                            
                    for c in imp.findall('.//COFINS'):
                        for item in c:
                            if item.find('CST') is not None: linha["CST-COF"] = item.find('CST').text.zfill(2)
                            if item.find('vBC') is not None: linha["BC-COF"] = float(item.find('vBC').text)
                            if item.find('vCOFINS') is not None: linha["VLR-COF"] = float(item.find('vCOFINS').text)

                dados_lista.append(linha)
        except: continue
    return pd.DataFrame(dados_lista)

def gerar_excel_final(df_xe, df_xs, ge_file=None, gs_file=None, ae_file=None, as_file=None):
    def load_csv(f, cols):
        if not f: return pd.DataFrame()
        try:
            f.seek(0); raw = f.read().decode('utf-8-sig'); sep = ';' if raw.count(';') > raw.count(',') else ','
            df = pd.read_csv(io.StringIO(raw), sep=sep, header=None, engine='python', dtype={0: str})
            if not str(df.iloc[0, 0]).strip().isdigit(): df = df.iloc[1:]
            df = df.iloc[:, :len(cols)]; df.columns = cols
            return df
        except: return pd.DataFrame()

    c_e = ['NF','DATA','CNPJ','UF','VLR_NF','AC','CFOP','COD','DESC','NCM','UNID','VUNIT','QTDE','VPROD','DESC_P','FRETE','SEG','DESP','VC','CST_ICMS','COL2','BC_ICMS','V_ICMS','BC_ST','V_ST','V_IPI','CST_PIS','BC_PIS','V_PIS','CST_COF','BC_COF','V_COF']
    c_s = ['NF','DATA','CNPJ','UF','VC','AC','CFOP','COD','VUNIT','QTDE','VITEM','DESC','FRETE','SEG','OUTRO','VC_I','CST','COL2','COL3','BC_ICMS','ALQ_ICMS','V_ICMS','BC_ST','V_ST','V_IPI','CST_PIS','BC_PIS','V_PIS','CST_COF','BC_COF','COF']

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        if not df_xe.empty: df_xe.to_excel(writer, sheet_name='XML_ENTRADAS', index=False)
        if not df_xs.empty: df_xs.to_excel(writer, sheet_name='XML_SAIDAS', index=False)
        load_csv(ge_file, c_e).to_excel(writer, sheet_name='GERENCIAL_ENT', index=False)
        load_csv(gs_file, c_s).to_excel(writer, sheet_name='GERENCIAL_SAI', index=False)
    return output.getvalue()
