import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
import re
import io

def extrair_dados_xml(files):
    """Extração profunda de XML com regras tributárias completas."""
    dados_lista = []
    if not files: return pd.DataFrame()
    for f in files:
        try:
            f.seek(0)
            conteudo = f.read().decode('utf-8', errors='replace')
            root = ET.fromstring(re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', conteudo))
            
            def buscar(caminho, raiz=root):
                alvo = raiz.find(f'.//{caminho}')
                return alvo.text if alvo is not None and alvo.text is not None else ""

            inf_nfe = root.find('.//infNFe')
            chave = inf_nfe.attrib.get('Id', '')[3:] if inf_nfe is not None else ""
            emit = root.find('.//emit')
            dest = root.find('.//dest')
            
            for det in root.findall('.//det'):
                prod = det.find('prod')
                imp = det.find('imposto')
                ncm_limpo = re.sub(r'\D', '', buscar('NCM', prod)).zfill(8)
                
                linha = {
                    "CHAVE_ACESSO": chave, "NUM_NF": buscar('nNF'),
                    "DATA_EMISSAO": buscar('dhEmi')[:10] if buscar('dhEmi') else "",
                    "CNPJ_EMIT": buscar('CNPJ', emit), "UF_EMIT": buscar('UF', emit),
                    "CNPJ_DEST": buscar('CNPJ', dest), "UF_DEST": buscar('UF', dest),
                    "ITEM": det.attrib.get('nItem', '0'), "CFOP": buscar('CFOP', prod),
                    "NCM": ncm_limpo, "COD_PROD": buscar('cProd', prod), "DESCR": buscar('xProd', prod),
                    "VPROD": float(buscar('vProd', prod) or 0),
                    "CST-ICMS": "", "BC-ICMS": 0.0, "ALQ-ICMS": 0.0, "VLR-ICMS": 0.0,
                    "CST-PIS": "", "BC-PIS": 0.0, "ALQ-PIS": 0.0, "VLR-PIS": 0.0,
                    "CST-COFINS": "", "BC-COFINS": 0.0, "ALQ-COFINS": 0.0, "VLR-COFINS": 0.0
                }

                if imp is not None:
                    # Lógica de ICMS
                    icms = imp.find('.//ICMS')
                    if icms is not None:
                        for n in icms:
                            cst = n.find('CST') or n.find('CSOSN')
                            if cst is not None: linha["CST-ICMS"] = cst.text.zfill(2)
                            if n.find('vBC') is not None: linha["BC-ICMS"] = float(n.find('vBC').text)
                            if n.find('pICMS') is not None: linha["ALQ-ICMS"] = float(n.find('pICMS').text)
                            if n.find('vICMS') is not None: linha["VLR-ICMS"] = float(n.find('vICMS').text)
                    
                    # Lógica de PIS/COFINS
                    for p in imp.findall('.//PIS'):
                        for node in p:
                            if node.find('CST') is not None: linha["CST-PIS"] = node.find('CST').text.zfill(2)
                            if node.find('vBC') is not None: linha["BC-PIS"] = float(node.find('vBC').text)
                            if node.find('vPIS') is not None: linha["VLR-PIS"] = float(node.find('vPIS').text)

                    for c in imp.findall('.//COFINS'):
                        for node in c:
                            if node.find('CST') is not None: linha["CST-COFINS"] = node.find('CST').text.zfill(2)
                            if node.find('vBC') is not None: linha["BC-COFINS"] = float(node.find('vBC').text)
                            if node.find('vCOFINS') is not None: linha["VLR-COFINS"] = float(node.find('vCOFINS').text)

                dados_lista.append(linha)
        except: continue
    return pd.DataFrame(dados_lista)

def gerar_excel_final(df_xe, df_xs, ge_file=None, gs_file=None):
    """Gera o Excel com abas de análise e conferência tributária."""
    def load_csv(f, cols):
        if not f: return pd.DataFrame()
        try:
            f.seek(0); raw = f.read().decode('utf-8-sig'); sep = ';' if raw.count(';') > raw.count(',') else ','
            df = pd.read_csv(io.StringIO(raw), sep=sep, header=None, engine='python', dtype={0: str})
            if not str(df.iloc[0, 0]).strip().isdigit(): df = df.iloc[1:]
            df = df.iloc[:, :len(cols)]; df.columns = cols
            return df
        except: return pd.DataFrame()

    c_s = ['NF','DATA','CNPJ','UF','VC','AC','CFOP','COD','VUNIT','QTDE','VITEM','DESC','FRETE','SEG','OUTRO','VC_I','CST','COL2','COL3','BC_ICMS','ALQ_ICMS','V_ICMS','BC_ST','V_ST','V_IPI','CST_PIS','BC_PIS','V_PIS','CST_COF','BC_COF','V_COF']

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        if not df_xe.empty: df_xe.to_excel(writer, sheet_name='XML_ENTRADAS', index=False)
        if not df_xs.empty: df_xs.to_excel(writer, sheet_name='XML_SAIDAS', index=False)
        
        df_gs = load_csv(gs_file, c_s)
        if not df_gs.empty:
            df_gs.to_excel(writer, sheet_name='GERENCIAL_SAIDAS', index=False)
            
            # ANÁLISE TRIBUTÁRIA: Cruzamento XML vs Gerencial
            if not df_xs.empty:
                df_auditoria = pd.merge(df_xs[['NUM_NF', 'COD_PROD', 'VPROD', 'VLR-ICMS', 'ALQ-ICMS']], 
                                      df_gs[['NF', 'COD', 'VITEM', 'V_ICMS', 'ALQ_ICMS']], 
                                      left_on='NUM_NF', right_on='NF', how='left')
                df_auditoria['DIF_VALOR'] = df_auditoria['VPROD'] - df_auditoria['VITEM']
                df_auditoria['DIF_ICMS'] = df_auditoria['VLR-ICMS'] - df_auditoria['V_ICMS']
                df_auditoria.to_excel(writer, sheet_name='AUDITORIA_FISCAL', index=False)
                
    return output.getvalue()
