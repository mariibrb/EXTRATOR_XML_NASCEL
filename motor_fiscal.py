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
                prod = det.find('prod')
                imp = det.find('imposto')
                ncm_limpo = re.sub(r'\D', '', buscar('NCM', prod)).zfill(8)
                
                linha = {
                    "CHAVE_ACESSO": chave_acesso,
                    "NUM_NF": buscar('nNF'),
                    "DATA_EMISSAO": pd.to_datetime(buscar('dhEmi')).replace(tzinfo=None) if buscar('dhEmi') else None,
                    "UF_EMIT": buscar('UF', root.find('.//emit')),
                    "UF_DEST": buscar('UF', root.find('.//dest')),
                    "AC": int(det.attrib.get('nItem', '0')),
                    "CFOP": buscar('CFOP', prod),
                    "NCM": ncm_limpo,
                    "COD_PROD": buscar('cProd', prod),
                    "DESCR": buscar('xProd', prod),
                    "VPROD": float(buscar('vProd', prod)) if buscar('vProd', prod) else 0.0,
                    "CST-ICMS": "", "BC-ICMS": 0.0, "VLR-ICMS": 0.0, "ALQ-ICMS": 0.0, "ICMS-ST": 0.0,
                    "CST-PIS": "", "CST-COF": "", "VAL-PIS": 0.0, "VAL-COF": 0.0, "BC-FED": 0.0,
                    "CST-IPI": "", "VAL-IPI": 0.0, "BC-IPI": 0.0, "ALQ-IPI": 0.0,
                    "VAL-DIFAL": 0.0, "VAL-FCP": 0.0, "VAL-FCPST": 0.0 
                }

                if imp is not None:
                    # ICMS
                    icms_node = imp.find('.//ICMS')
                    if icms_node is not None:
                        for n in icms_node:
                            cst = n.find('CST') if n.find('CST') is not None else n.find('CSOSN')
                            if cst is not None: linha["CST-ICMS"] = cst.text.zfill(2)
                            if n.find('vBC') is not None: linha["BC-ICMS"] = float(n.find('vBC').text)
                            if n.find('vICMS') is not None: linha["VLR-ICMS"] = float(n.find('vICMS').text)
                            if n.find('pICMS') is not None: linha["ALQ-ICMS"] = float(n.find('pICMS').text)
                            if n.find('vICMSST') is not None: linha["ICMS-ST"] = float(n.find('vICMSST').text)
                            if n.find('vFCP') is not None: linha["VAL-FCP"] = float(n.find('vFCP').text)
                    
                    # PIS
                    pis_node = imp.find('.//PIS')
                    if pis_node is not None:
                        for p in pis_node:
                            if p.find('CST') is not None: linha["CST-PIS"] = p.find('CST').text.zfill(2)
                            if p.find('vBC') is not None: linha["BC-FED"] = float(p.find('vBC').text)
                            if p.find('vPIS') is not None: linha["VAL-PIS"] = float(p.find('vPIS').text)
                    
                    # COFINS
                    cof_node = imp.find('.//COFINS')
                    if cof_node is not None:
                        for c in cof_node:
                            if c.find('CST') is not None: linha["CST-COF"] = c.find('CST').text.zfill(2)
                            if c.find('vCOFINS') is not None: linha["VAL-COF"] = float(c.find('vCOFINS').text)

                    # IPI
                    ipi_node = imp.find('.//IPI')
                    if ipi_node is not None:
                        cst_i = ipi_node.find('.//CST')
                        if cst_i is not None: linha["CST-IPI"] = cst_i.text.zfill(2)
                        if ipi_node.find('.//vBC') is not None: linha["BC-IPI"] = float(ipi_node.find('.//vBC').text)
                        if ipi_node.find('.//vIPI') is not None: linha["VAL-IPI"] = float(ipi_node.find('.//vIPI').text)

                    # DIFAL
                    difal_node = imp.find('.//ICMSUFDest')
                    if difal_node is not None:
                        if difal_node.find('vICMSUFDest') is not None: linha["VAL-DIFAL"] = float(difal_node.find('vICMSUFDest').text)

                dados_lista.append(linha)
        except: continue
    return pd.DataFrame(dados_lista)

def gerar_excel_final(df_ent_xml, df_sai_xml, file_ger_ent=None, file_ger_sai=None):
    def format_brl(v): return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    stats = {'total_deb': 0.0, 'total_cred': 0.0, 'icms_deb': 0.0, 'icms_cred': 0.0, 'ipi_deb': 0.0, 'ipi_cred': 0.0}
    
    # 1. Carregar Bases
    try:
        base_icms = pd.read_excel(".streamlit/Base_ICMS.xlsx")
        base_icms['NCM_KEY'] = base_icms.iloc[:, 0].astype(str).str.replace(r'\D', '', regex=True).str.zfill(8)
    except: base_icms = pd.DataFrame()
    try:
        base_pc = pd.read_excel(".streamlit/Base_CST_Pis_Cofins.xlsx")
        base_pc['NCM_KEY'] = base_pc.iloc[:, 0].astype(str).str.replace(r'\D', '', regex=True).str.zfill(8)
    except: base_pc = pd.DataFrame()

    # 2. Auditoria de XML (ICMS, PIS, COFINS, IPI, DIFAL)
    df_icms_audit = df_sai_xml.copy() if not df_sai_xml.empty else pd.DataFrame()
    if not df_icms_audit.empty:
        tem_e = not df_ent_xml.empty
        ncm_st = df_ent_xml[(df_ent_xml['CST-ICMS']=="60") | (df_ent_xml['ICMS-ST'] > 0)]['NCM'].unique().tolist() if tem_e else []
        def audit_icms_row(row):
            ncm = str(row['NCM']).zfill(8); info = base_icms[base_icms['NCM_KEY'] == ncm] if not base_icms.empty else pd.DataFrame()
            st_e = "✅ ST Localizado" if ncm in ncm_st else "❌ Sem ST na Entrada" if tem_e else "⚠️ Sem Entrada"
            if info.empty: return pd.Series([st_e, "NCM Ausente", format_brl(row['VPROD']), "R$ 0,00", "Cadastrar NCM"])
            aliq_e = float(info.iloc[0, 3]) if row['UF_EMIT'] == row['UF_DEST'] else 12.0
            diag = "✅ Correto" if abs(row['ALQ-ICMS'] - aliq_e) < 0.1 else "Divergente"
            return pd.Series([st_e, diag, format_brl(row['VPROD']), format_brl(row['BC-ICMS']*aliq_e/100), "Ajustar Alíquota" if diag != "✅ Correto" else "✅"])
        df_icms_audit[['ST Entrada', 'Diagnóstico', 'Valor Prod', 'ICMS Esperado', 'Ação']] = df_icms_audit.apply(audit_icms_row, axis=1)

    # 3. Leitura Flexível dos Gerenciais (CSV)
    def load_ger(f, target_cols):
        if not f: return pd.DataFrame()
        f.seek(0); raw = f.read().decode('utf-8-sig', errors='replace'); sep = ';' if raw.count(';') > raw.count(',') else ','
        df = pd.read_csv(io.StringIO(raw), sep=sep, header=None, engine='python', dtype={0: str})
        if df.shape[0] > 0 and not str(df.iloc[0, 0]).strip().isdigit(): df = df.iloc[1:]
        df = df.iloc[:, :len(target_cols)]
        df.columns = target_cols
        for c in df.columns:
            if any(x in c for x in ['VC', 'VLR', 'IPI', 'ICMS', 'PIS', 'COF', 'BC']):
                df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        return df

    cols_sai = ['NF','DATA_EMISSAO','CNPJ','Ufp','VC','AC','CFOP','COD_ITEM','DESC_ITEM','NCM','UND','VUNIT','QTDE','VITEM','DESC','FRETE','SEG','OUTRAS','VC_ITEM','CST','BC_ICMS','ALIQ_ICMS','ICMS','BC_ICMSST','ICMSST','IPI','CST_PIS','BC_PIS','PIS','CST_COF','BC_COF','COF']
    cols_ent = ['NUM_NF','DATA_EMISSAO','CNPJ','UF','VLR_NF','AC','CFOP','COD_PROD','DESCR','NCM','UNID','VUNIT','QTDE','VPROD','DESC','FRETE','SEG','DESP','VC','CST-ICMS','BC-ICMS','VLR-ICMS','BC-ICMS-ST','ICMS-ST','VLR_IPI','CST_PIS','BC_PIS','VLR_PIS','CST_COF','BC_COF','VLR_COF']
    
    df_gs = load_ger(file_ger_sai, cols_sai)
    df_ge = load_ger(file_ger_ent, cols_ent)

    # 4. Apuração PIS/COFINS (Conforme sua planilha)
    df_apur_pc = pd.DataFrame()
    if not df_gs.empty or not df_ge.empty:
        deb_pc = df_gs[df_gs['CST_PIS'].astype(str).str.zfill(2) == '01'].copy()
        deb_pc['BASE'] = deb_pc['VC'] - deb_pc['IPI'] - deb_pc['ICMS']
        deb_pc['PIS_V'] = deb_pc['BASE'] * 0.0165; deb_pc['COF_V'] = deb_pc['BASE'] * 0.076
        stats['total_deb'] = deb_pc['PIS_V'].sum() + deb_pc['COF_V'].sum()
        
        cred_pc = df_ge.copy()
        cred_pc['BASE'] = cred_pc['VLR_NF'] - cred_pc['VLR_IPI']
        cred_pc['PIS_V'] = cred_pc['BASE'] * 0.0165; cred_pc['COF_V'] = cred_pc['BASE'] * 0.076
        stats['total_cred'] = cred_pc['PIS_V'].sum() + cred_pc['COF_V'].sum()
        df_apur_pc = pd.concat([deb_pc, cred_pc], ignore_index=True)

    # 5. Apuração ICMS/IPI (LIVRO FISCAL)
    df_apur_icms_ipi = pd.DataFrame()
    if not df_gs.empty or not df_ge.empty:
        d_ii = df_gs.groupby(['AC', 'CFOP']).agg({'VC':'sum','BC_ICMS':'sum','ICMS':'sum','IPI':'sum'}).reset_index()
        d_ii.insert(0, 'TIPO', 'DÉBITO (SAÍDA)')
        stats['icms_deb'], stats['ipi_deb'] = d_ii['ICMS'].sum(), d_ii['IPI'].sum()
        
        c_ii = df_ge.groupby(['AC', 'CFOP']).agg({'VLR_NF':'sum','BC-ICMS':'sum','VLR-ICMS':'sum','VLR_IPI':'sum'}).reset_index()
        c_ii.columns = ['AC','CFOP','VC','BC_ICMS','ICMS','IPI']
        c_ii.insert(0, 'TIPO', 'CRÉDITO (ENTRADA)')
        stats['icms_cred'], stats['ipi_cred'] = c_ii['ICMS'].sum(), c_ii['IPI'].sum()
        df_apur_icms_ipi = pd.concat([d_ii, c_ii], ignore_index=True)

    # 6. Gravação Final
    mem = io.BytesIO()
    with pd.ExcelWriter(mem, engine='xlsxwriter') as wr:
        if not df_ent_xml.empty: df_ent_xml.to_excel(wr, sheet_name='ENTRADAS_XML', index=False)
        if not df_sai_xml.empty: df_sai_xml.to_excel(wr, sheet_name='SAIDAS_XML', index=False)
        if not df_icms_audit.empty: df_icms_audit.to_excel(wr, sheet_name='AUDIT_ICMS', index=False)
        if not df_apur_pc.empty: df_apur_pc.to_excel(wr, sheet_name='PIS e COFINS', index=False)
        if not df_apur_icms_ipi.empty: df_apur_icms_ipi.to_excel(wr, sheet_name='Apuração ICMS e IPI', index=False)
        if not df_ge.empty: df_ge.to_excel(wr, sheet_name='Gerencial Entradas', index=False)
        if not df_gs.empty: df_gs.to_excel(wr, sheet_name='Gerencial Saídas', index=False)
        
        workbook = wr.book; f_txt = workbook.add_format({'num_format': '@'})
        for s in wr.sheets: wr.sheets[s].set_column('A:C', 20, f_txt)

    return mem.getvalue(), stats
