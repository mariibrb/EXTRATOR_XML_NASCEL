import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import io
import re
import os

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Sentinela Fiscal Pro", layout="wide")
st.title("🛡️ Sentinela: Auditoria Fiscal (ICMS & IPI)")

# --- 1. CARREGAR BASES MESTRE + TIPI (COM PROTEÇÃO DE ERRO) ---
@st.cache_data
def carregar_bases_mestre():
    # A. Planilha do Cliente (Regras Internas)
    caminho_mestre = "Sentinela_MIRÃO_Outubro2025.xlsx"
    if os.path.exists(caminho_mestre):
        xls = pd.ExcelFile(caminho_mestre)
        df_gerencial = pd.read_excel(xls, 'Entradas Gerencial', dtype=str)
        df_tribut = pd.read_excel(xls, 'Bases Tribut', dtype=str)
        try: df_inter = pd.read_excel(xls, 'Bases Tribut', usecols="AC:AD", dtype=str).dropna()
        except: df_inter = pd.DataFrame()
    else:
        return None, None, None, None

    # B. TIPI Oficial (Leitura Blindada contra erros de formatação)
    caminho_tipi = "TIPI.xlsx"
    df_tipi = pd.DataFrame()
    
    if os.path.exists(caminho_tipi):
        try:
            # 1. Lê tudo como texto para não quebrar
            df_raw = pd.read_excel(caminho_tipi, header=None, dtype=str)
            df_raw = df_raw.dropna(how='all') # Remove linhas vazias

            # 2. Usa Regex para encontrar onde estão os NCMs (ex: 0101.21.00)
            # A coluna 0 geralmente é o NCM
            mask_ncm = df_raw.iloc[:, 0].astype(str).str.contains(r'^\d{4}\.\d{2}\.\d{2}', regex=True, na=False)
            df_tipi = df_raw[mask_ncm].copy()
            
            # 3. Seleção de Colunas
            # Tentativa padrão: Coluna 0 (NCM) e Coluna 1 (Alíquota). 
            # OBS: Se na sua tabela a alíquota for a coluna C, mude para [0, 2]
            if df_tipi.shape[1] >= 2:
                df_tipi = df_tipi.iloc[:, [0, 1]]
                df_tipi.columns = ['NCM', 'ALIQ']
                
                # 4. Limpeza Final
                df_tipi['NCM'] = df_tipi['NCM'].str.replace('.', '', regex=False).str.strip()
                # Troca NT por 0, troca vírgula por ponto
                df_tipi['ALIQ'] = df_tipi['ALIQ'].str.upper().replace('NT', '0').str.strip().str.replace(',', '.')
            else:
                df_tipi = pd.DataFrame() # Estrutura inválida
                
        except Exception as e:
            print(f"Erro silencioso ao ler TIPI: {e}")
            df_tipi = pd.DataFrame()

    return df_gerencial, df_tribut, df_inter, df_tipi

df_gerencial, df_tribut, df_inter, df_tipi = carregar_bases_mestre()

# --- 2. EXTRAÇÃO XML ---
def extrair_tags_completo(xml_content):
    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    try: root = ET.fromstring(xml_content)
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
            "UF Emit": emit.find('nfe:enderEmit/nfe:UF', ns).text if emit is not None else "",
            "UF Dest": dest.find('nfe:enderDest/nfe:UF', ns).text if dest is not None else "",
            "nItem": det.attrib['nItem'],
            "Cód Prod": prod.find('nfe:cProd', ns).text if prod is not None else "",
            "Desc Prod": prod.find('nfe:xProd', ns).text if prod is not None else "",
            "NCM": prod.find('nfe:NCM', ns).text if prod is not None else "",
            "CFOP": prod.find('nfe:CFOP', ns).text if prod is not None else "",
            "vProd": float(prod.find('nfe:vProd', ns).text) if prod is not None else 0.0,
            # ICMS
            "CST ICMS": imposto.find('.//nfe:CST', ns).text if imposto.find('.//nfe:CST', ns) is not None else "",
            "BC ICMS": float(imposto.find('.//nfe:vBC', ns).text) if imposto.find('.//nfe:vBC', ns) is not None else 0.0,
            "Alq ICMS": float(imposto.find('.//nfe:pICMS', ns).text) if imposto.find('.//nfe:pICMS', ns) is not None else 0.0,
            "ICMS": float(imposto.find('.//nfe:vICMS', ns).text) if imposto.find('.//nfe:vICMS', ns) is not None else 0.0,
            "pRedBC ICMS": float(imposto.find('.//nfe:pRedBC', ns).text) if imposto.find('.//nfe:pRedBC', ns) is not None else 0.0,
            "BC ICMS-ST": float(imposto.find('.//nfe:vBCST', ns).text) if imposto.find('.//nfe:vBCST', ns) is not None else 0.0,
            "ICMS-ST": float(imposto.find('.//nfe:vICMSST', ns).text) if imposto.find('.//nfe:vICMSST', ns) is not None else 0.0,
            # IPI
            "CST IPI": imposto.find('.//nfe:IPI//nfe:CST', ns).text if imposto.find('.//nfe:IPI//nfe:CST', ns) is not None else "",
            "Aliq IPI": float(imposto.find('.//nfe:IPI//nfe:pIPI', ns).text) if imposto.find('.//nfe:IPI//nfe:pIPI', ns) is not None else 0.0,
            "vIPI": float(imposto.find('.//nfe:IPI//nfe:vIPI', ns).text) if imposto.find('.//nfe:IPI//nfe:vIPI', ns) is not None else 0.0,
            "Chave de Acesso": chave
        }
        itens.append(registro)
    return itens

# --- 3. INTERFACE ---
with st.sidebar:
    st.header("📂 Upload Central")
    xml_saidas = st.file_uploader("1. Notas de SAÍDA", accept_multiple_files=True, type='xml')
    xml_entradas = st.file_uploader("2. Notas de ENTRADA", accept_multiple_files=True, type='xml')
    rel_status = st.file_uploader("3. Status Sefaz", type=['xlsx', 'csv'])

# --- 4. PROCESSAMENTO ---
if (xml_saidas or xml_entradas) and rel_status:
    # Mapear Status
    try:
        df_st_rel = pd.read_excel(rel_status, dtype=str) if rel_status.name.endswith('.xlsx') else pd.read_csv(rel_status, dtype=str)
        status_dict = dict(zip(df_st_rel.iloc[:, 0].str.replace(r'\D', '', regex=True), df_st_rel.iloc[:, 5]))
    except:
        st.error("Erro ao ler relatório de status. Verifique o formato.")
        status_dict = {}

    # Extrair XMLs
    list_s = []
    if xml_saidas:
        for f in xml_saidas: list_s.extend(extrair_tags_completo(f.read()))
    df_s = pd.DataFrame(list_s)
    
    list_e = []
    if xml_entradas:
        for f in xml_entradas: list_e.extend(extrair_tags_completo(f.read()))
    df_e = pd.DataFrame(list_e)

    if not df_s.empty:
        # Coluna AP (Status)
        df_s['AP'] = df_s['Chave de Acesso'].str.replace(r'\D', '', regex=True).map(status_dict).fillna("Pendente")
        
        # --- PREPARA MAPAS (COM SEGURANÇA) ---
        map_tribut_cst = {}
        map_tribut_aliq = {}
        map_gerencial_cst = {}
        map_inter = {}
        map_tipi = {}

        if df_tribut is not None:
            map_tribut_cst = dict(zip(df_tribut.iloc[:, 0].astype(str), df_tribut.iloc[:, 2].astype(str)))
            map_tribut_aliq = dict(zip(df_tribut.iloc[:, 0].astype(str), df_tribut.iloc[:, 3].astype(str)))
        
        if df_gerencial is not None:
            map_gerencial_cst = dict(zip(df_gerencial.iloc[:, 0].astype(str), df_gerencial.iloc[:, 1].astype(str)))
        
        if not df_inter.empty:
            map_inter = dict(zip(df_inter.iloc[:, 0].astype(str), df_inter.iloc[:, 1].astype(str)))

        # Verificação da TIPI antes de mapear
        if not df_tipi.empty and 'NCM' in df_tipi.columns and 'ALIQ' in df_tipi.columns:
            map_tipi = dict(zip(df_tipi['NCM'], df_tipi['ALIQ']))
        else:
            st.warning("⚠️ Tabela TIPI não carregada ou formato inválido. A aba IPI pode vir vazia.")

        # === ABA 3: ICMS ===
        df_icms = df_s.copy()
        
        def f_analise_cst(row):
            status, cst, ncm = str(row['AP']), str(row['CST ICMS']).strip(), str(row['NCM']).strip()
            if "Cancelamento" in status: return "NF cancelada"
            cst_esp = map_tribut_cst.get(ncm)
            if not cst_esp: return "NCM não encontrado"
            # Regra de ST na Entrada vs Saída
            if map_gerencial_cst.get(ncm) == "60" and cst != "60": return f"Divergente — CST informado: {cst} | Esperado: 60"
            return "Correto" if cst == cst_esp else f"Divergente — CST informado: {cst} | Esperado: {cst_esp}"

        def f_cst_bc(row):
            if "Cancelamento" in str(row['AP']): return "NF Cancelada"
            cst, v_p, bc = str(row['CST ICMS']), row['vProd'], row['BC ICMS']
            pred = row['pRedBC ICMS']
            msgs = []
            if cst == "00" and abs(bc - v_p) > 0.02: msgs.append("Base diferente do produto")
            if cst == "20" and abs(bc - (v_p * (1 - pred/100))) > 0.02: msgs.append("Base incorreta após redução")
            if cst in ["90", "99"] and row['ICMS'] == 0: msgs.append("Sem destaque ICMS")
            return "; ".join(msgs) if msgs else "Correto"

        def f_aliq(row):
            if "Cancelamento" in str(row['AP']): return "NF Cancelada"
            ncm, uf_e, uf_d, aliq_xml = str(row['NCM']), row['UF Emit'], row['UF Dest'], row['Alq ICMS']
            if uf_e == uf_d:
                esp = map_tribut_aliq.get(ncm)
                if not esp: return "NCM não encontrado (Interno)"
            else:
                esp = map_inter.get(uf_d)
                if not esp: return "UF Destino não encontrada"
            try: esp_val = float(str(esp).replace(',', '.'))
            except: return "Erro valor esperado"
            return "Correto" if abs(aliq_xml - esp_val) < 0.1 else f"Destacado: {aliq_xml} | Esperado: {esp_val}"

        def f_complemento(row):
            analise = str(row['Analise Aliq ICMS'])
            if "Destacado" in analise:
                try:
                    dest = float(re.search(r'Destacado: ([\d.]+)', analise).group(1))
                    esp = float(re.search(r'Esperado: ([\d.]+)', analise).group(1))
                    if dest < esp: return (esp - dest) * (row['BC ICMS'] / 100)
                except: return 0.0
            return 0.0

        # Aplica fórmulas ICMS
        df_icms['Análise CST ICMS'] = df_icms.apply(f_analise_cst, axis=1)
        df_icms['CST x BC'] = df_icms.apply(f_cst_bc, axis=1)
        df_icms['Analise Aliq ICMS'] = df_icms.apply(f_aliq, axis=1)
        df_icms['Complemento ICMS Próprio'] = df_icms.apply(f_complemento, axis=1)

        # === ABA 4: IPI (Exclusiva) ===
        df_ipi = df_s.copy()

        def f_analise_ipi(row):
            if "Cancelamento" in str(row['AP']): return "NF Cancelada"
            ncm, aliq_xml = str(row['NCM']).strip(), row['Aliq IPI']
            
            if not map_tipi: return "Tabela TIPI indisponível"

            # Busca na TIPI
            esp = map_tipi.get(ncm)
            if esp is None: return "NCM não encontrado na TIPI"
            
            try: esp_val = float(str(esp).replace(',', '.'))
            except: return "Erro leitura TIPI"

            if abs(aliq_xml - esp_val) < 0.1:
                return "Correto"
            else:
                return f"Destacado: {aliq_xml} | Esperado: {esp_val}"

        df_ipi['Análise IPI'] = df_ipi.apply(f_analise_ipi, axis=1)

    # --- EXPORTAÇÃO ---
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        if not df_e.empty: df_e.to_excel(writer, index=False, sheet_name='Entradas')
        if not df_s.empty: df_s.to_excel(writer, index=False, sheet_name='Saídas')
        if not df_s.empty: df_icms.to_excel(writer, index=False, sheet_name='ICMS')
        if not df_s.empty: df_ipi.to_excel(writer, index=False, sheet_name='IPI')

    st.success("✅ Auditoria Completa: Abas de Entradas, Saídas, ICMS e IPI geradas!")
    st.download_button("📥 Baixar Sentinela Auditada", buffer.getvalue(), "Sentinela_Auditada_Final.xlsx")
