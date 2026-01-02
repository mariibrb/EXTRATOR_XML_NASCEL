import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
import re
import io

def extrair_dados_xml(files, fluxo, df_autenticidade=None):
    dados_lista = []
    if not files: return pd.DataFrame()
    for f in files:
        try:
            f.seek(0)
            conteudo_bruto = f.read()
            texto_xml = conteudo_bruto.decode('utf-8', errors='replace')
            texto_xml = re.sub(r'<\?xml[^?]*\?>', '', texto_xml)
            texto_xml = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', texto_xml)
            root = ET.fromstring(texto_xml)
            
            def buscar(caminho, raiz=root):
                alvo = raiz.find(f'.//{caminho}')
                return alvo.text if alvo is not None and alvo.text is not None else ""

            inf_nfe = root.find('.//infNFe')
            chave_acesso = inf_nfe.attrib.get('Id', '')[3:] if inf_nfe is not None else ""
            
            for det in root.findall('.//det'):
                prod = det.find('prod'); imp = det.find('imposto')
                ncm_limpo = re.sub(r'\D', '', buscar('NCM', prod)).zfill(8)
                linha = {
                    "CHAVE_ACESSO": chave_acesso, "NUM_NF": buscar('nNF'),
                    "DATA_EMISSAO": pd.to_datetime(buscar('dhEmi')).replace(tzinfo=None) if buscar('dhEmi') else None,
                    "UF_EMIT": buscar('UF', root.find('.//emit')), "UF_DEST": buscar('UF', root.find('.//dest')),
                    "AC": int(det.attrib.get('nItem', '0')), "CFOP": buscar('CFOP', prod), "NCM": ncm_limpo,
                    "COD_PROD": buscar('cProd', prod), "DESCR": buscar('xProd', prod),
                    "VPROD": float(buscar('vProd', prod)) if buscar('vProd', prod) else 0.0,
                    "CST-ICMS": "", "BC-ICMS": 0.0, "VLR-ICMS": 0.0, "ALQ-ICMS": 0.0, "ICMS-ST": 0.0,
                    "CST-PIS": "", "CST-COF": "", "VAL-PIS": 0.0, "VAL-COF": 0.0, "BC-FED": 0.0,
                    "CST-IPI": "", "VAL-IPI": 0.0, "BC-IPI": 0.0, "ALQ-IPI": 0.0, "VAL-DIFAL": 0.0
                }
                if imp is not None:
                    ic = imp.find('.//ICMS')
                    if ic is not None:
                        for n in ic:
                            cst = n.find('CST') if n.find('CST') is not None else n.find('CSOSN')
                            if cst is not None: linha["CST-ICMS"] = cst.text.zfill(2)
                            if n.find('vBC') is not None: linha["BC-ICMS"] = float(n.find('vBC').text)
                            if n.find('vICMS') is not None: linha["VLR-ICMS"] = float(n.find('vICMS').text)
                            if n.find('pICMS') is not None: linha["ALQ-ICMS"] = float(n.find('pICMS').text)
                    pi = imp.find('.//PIS')
                    if pi is not None:
                        for p in pi:
                            if p.find('CST') is not None: linha["CST-PIS"] = p.find('CST').text.zfill(2)
                            if p.find('vPIS') is not None: linha["VAL-PIS"] = float(p.find('vPIS').text)
                    co = imp.find('.//COFINS')
                    if co is not None:
                        for c in co:
                            if c.find('CST') is not None: linha["CST-COF"] = c.find('CST').text.zfill(2)
                            if c.find('vCOFINS') is not None: linha["VAL-COF"] = float(c.find('vCOFINS').text)
                dados_lista.append(linha)
        except: continue
    return pd.DataFrame(dados_lista)

def gerar_excel_final(df_ent_xml, df_sai_xml, file_ger_ent=None, file_ger_sai=None):
    stats = {'total_deb': 0.0, 'total_cred': 0.0, 'icms_deb': 0.0, 'ipi_deb': 0.0}
    
    def load_gerencial_fix(f, target_cols):
        if not f: return pd.DataFrame()
        try:
            f.seek(0); raw = f.read().decode('utf-8-sig', errors='replace'); sep = ';' if raw.count(';') > raw.count(',') else ','
            df = pd.read_csv(io.StringIO(raw), sep=sep, header=None, engine='python', dtype={0: str})
            if df.shape[0] > 0 and not str(df.iloc[0, 0]).strip().isdigit(): df = df.iloc[1:]
            df = df.iloc[:, :len(target_cols)]; df.columns = target_cols
            for c in df.columns:
                if any(x in c for x in ['VC', 'VLR', 'IPI', 'ICMS', 'PIS', 'COF', 'BC']):
                    df[c] = pd.to_numeric(df[c].astype(str).str.replace('.', '').str.replace(',', '.').str.strip(), errors='coerce').fillna(0)
            return df
        except: return pd.DataFrame()

    c_sai = ['NF','DATA','CNPJ','UF','VC','AC','CFOP','ITEM','DESC','NCM','UND','UNIT','QTDE','VITEM','DESC_O','FRETE','SEG','OUTRAS','VC_ITEM','CST','BC_ICMS','ALQ_ICMS','ICMS','BC_ST','ST','IPI','CST_PIS','BC_PIS','PIS','CST_COF','BC_COF','COF']
    c_ent = ['NF','DATA','CNPJ','UF','VLR_NF','AC','CFOP','ITEM','DESC','NCM','UNID','UNIT','QTDE','VPROD','DESC_O','FRETE','SEG','DESP','VC','CST_ICMS','BC_ICMS','VLR_ICMS','BC_ST','ST','IPI','CST_PIS','BC_PIS','PIS','CST_COF','BC_COF','COF']
    
    df_gs = load_gerencial_fix(file_ger_sai, c_sai); df_ge = load_gerencial_fix(file_ger_ent, c_ent)

    # --- APURAÇÕES ---
    df_pc = pd.DataFrame(); df_ii = pd.DataFrame()
    if not df_gs.empty:
        d_pc = df_gs[df_gs['CST_PIS'].astype(str).str.zfill(2)=='01'].copy()
        d_pc['BASE'] = d_pc['VC']-d_pc['IPI']-d_pc['ICMS']; d_pc['PIS_V']=d_pc['BASE']*0.0165; d_pc['COF_V']=d_pc['BASE']*0.076
        stats['total_deb'] = d_pc['PIS_V'].sum() + d_pc['COF_V'].sum()
        df_pc = d_pc.groupby(['AC', 'CFOP']).agg({'VC':'sum','IPI':'sum','ICMS':'sum','BASE':'sum','PIS_V':'sum','COF_V':'sum'}).reset_index()
        
        d_ii = df_gs.groupby(['AC', 'CFOP']).agg({'VC':'sum','BC_ICMS':'sum','ICMS':'sum','IPI':'sum'}).reset_index()
        stats['icms_deb'], stats['ipi_deb'] = d_ii['ICMS'].sum(), d_ii['IPI'].sum()
        df_ii = d_ii

    if not df_ge.empty:
        c_pc = df_ge.copy(); c_pc['BASE']=c_pc['VLR_NF']-c_pc['IPI']
        stats['total_cred'] = (c_pc['BASE']*0.0165).sum() + (c_pc['BASE']*0.076).sum()

    mem = io.BytesIO()
    with pd.ExcelWriter(mem, engine='xlsxwriter') as wr:
        if not df_ent_xml.empty: df_ent_xml.to_excel(wr, sheet_name='ENTRADAS_XML', index=False)
        if not df_sai_xml.empty: df_sai_xml.to_excel(wr, sheet_name='SAIDAS_XML', index=False)
        if not df_pc.empty: df_pc.to_excel(wr, sheet_name='PIS e COFINS', index=False)
        if not df_ii.empty: df_ii.to_excel(wr, sheet_name='Apuração ICMS e IPI', index=False)
        if not df_ge.empty: df_ge.to_excel(wr, sheet_name='Gerencial Entradas', index=False)
        if not df_gs.empty: df_gs.to_excel(wr, sheet_name='Gerencial Saídas', index=False)
        for s in wr.sheets: wr.sheets[s].set_column('A:C', 20, wr.book.add_format({'num_format':'@'}))
    return mem.getvalue(), stats
