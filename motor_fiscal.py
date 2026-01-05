import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
import re
import io

def extrair_dados_xml(files):
    dados_lista = []
    if not files: return pd.DataFrame()
    for f in files:
        try:
            f.seek(0)
            root = ET.fromstring(re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', f.read().decode('utf-8', errors='replace')))
            def buscar(caminho, raiz=root):
                alvo = raiz.find(f'.//{caminho}')
                return alvo.text if alvo is not None and alvo.text is not None else ""
            inf_nfe = root.find('.//infNFe')
            chave = inf_nfe.attrib.get('Id', '')[3:] if inf_nfe is not None else ""
            for det in root.findall('.//det'):
                prod = det.find('prod'); imp = det.find('imposto')
                linha = {
                    "CHAVE_ACESSO": chave, "NUM_NF": buscar('nNF'),
                    "DATA_EMISSAO": buscar('dhEmi')[:10] if buscar('dhEmi') else "",
                    "UF_EMIT": buscar('UF', root.find('.//emit')), "UF_DEST": buscar('UF', root.find('.//dest')),
                    "AC": int(det.attrib.get('nItem', '0')), "CFOP": buscar('CFOP', prod),
                    "NCM": re.sub(r'\D', '', buscar('NCM', prod)).zfill(8),
                    "COD_PROD": buscar('cProd', prod), "DESCR": buscar('xProd', prod),
                    "VPROD": float(buscar('vProd', prod) or 0),
                    "CST-ICMS": "", "BC-ICMS": 0.0, "VLR-ICMS": 0.0
                }
                if imp is not None:
                    ic = imp.find('.//ICMS')
                    if ic is not None:
                        for n in ic:
                            cst = n.find('CST') or n.find('CSOSN')
                            if cst is not None: linha["CST-ICMS"] = cst.text.zfill(2)
                            if n.find('vBC') is not None: linha["BC-ICMS"] = float(n.find('vBC').text)
                dados_lista.append(linha)
        except: continue
    return pd.DataFrame(dados_lista)

def gerar_excel_final(df_xe, df_xs, ge=None, gs=None, ae=None, as_f=None):
    def load(f, cols):
        if not f: return pd.DataFrame()
        try:
            f.seek(0); raw = f.read().decode('utf-8-sig'); sep = ';' if raw.count(';') > raw.count(',') else ','
            df = pd.read_csv(io.StringIO(raw), sep=sep, header=None, engine='python', dtype={0: str})
            if not str(df.iloc[0,0]).isdigit(): df = df.iloc[1:]
            df = df.iloc[:, :len(cols)]; df.columns = cols
            return df
        except: return pd.DataFrame()
    c_e = ['NUM_NF','DATA_EMISSAO','CNPJ','UF','VLR_NF','AC','CFOP','COD_PROD','DESCR','NCM','UNID','VUNIT','QTDE','VPROD','DESC','FRETE','SEG','DESP','VC','CST-ICMS','Coluna2','BC-ICMS','VLR-ICMS','BC-ICMS-ST','ICMS-ST','VLR_IPI','CST_PIS','BC_PIS','VLR_PIS','CST_COF','BC_COF','VLR_COF']
    c_s = ['NF','DATA_EMISSAO','CNPJ','Ufp','VC','AC','CFOP','COD_ITEM','VUNIT','QTDE','VITEM','DESC','FRETE','SEG','OUTRAS','VC_ITEM','CST','Coluna2','Coluna3','BC_ICMS','ALIQ_ICMS','ICMS','BC_ICMSST','ICMSST','IPI','CST_PIS','BC_PIS','PIS','CST_COF','BC_COF','COF']
    df_ge = load(ge, c_e); df_gs = load(gs, c_s)
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as wr:
        if not df_xe.empty: df_xe.to_excel(wr, sheet_name='XML_ENTRADAS', index=False)
        if not df_xs.empty: df_xs.to_excel(wr, sheet_name='XML_SAIDAS', index=False)
        if not df_ge.empty: df_ge.to_excel(wr, sheet_name='GER_ENT', index=False)
        if not df_gs.empty: df_gs.to_excel(wr, sheet_name='GER_SAI', index=False)
    return out.getvalue()
