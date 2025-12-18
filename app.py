import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import io
import re
import os

# --- 1. CONFIGURAÇÃO VISUAL (LAYOUT NOVO) ---
st.set_page_config(
    page_title="Nascel | Auditoria",
    page_icon="🧡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS PERSONALIZADO
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Quicksand', sans-serif; }
    div.block-container { padding-top: 2rem !important; padding-bottom: 1rem !important; }
    .stApp { background-color: #F7F7F7; }
    h1, h2, h3, h4 { color: #FF6F00 !important; font-weight: 700; }
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
        background-color: white; padding: 20px; border-radius: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    .stFileUploader { padding: 10px; border: 2px dashed #FFCC80; border-radius: 15px; text-align: center; }
    .stButton>button { background-color: #FF6F00; color: white; border-radius: 25px; border: none; font-weight: bold; padding: 10px 30px; width: 100%; }
    .stButton>button:hover { background-color: #E65100; }
    div[data-testid="metric-container"] { border-left: 5px solid #FF6F00; background-color: #FFF3E0; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. SIDEBAR COM UPLOADS DE BASE ---
with st.sidebar:
    caminho_logo = ".streamlit/nascel sem fundo.png"
    if os.path.exists(caminho_logo): st.image(caminho_logo, use_column_width=True)
    elif os.path.exists("nascel sem fundo.png"): st.image("nascel sem fundo.png", use_column_width=True)
    else: st.markdown("<h1 style='color:#FF6F00; text-align:center;'>Nascel</h1>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    with st.expander("⚙️ ATUALIZAR BASES (Upload)", expanded=False):
        st.caption("Suba aqui as planilhas preenchidas para ensinar o Sentinela.")
        
        # 1. Base ICMS
        nova_icms = st.file_uploader("Base ICMS", type=['xlsx'], key='up_icms_base')
        if nova_icms:
            with open(".streamlit/base_icms.xlsx", "wb") as f: f.write(nova_icms.getbuffer())
            st.success("✅ Base ICMS Atualizada!")

        # 2. Base TIPI
        nova_tipi = st.file_uploader("Tabela TIPI (IPI)", type=['xlsx'], key='up_tipi_base')
        if nova_tipi:
            with open(".streamlit/tipi.xlsx", "wb") as f: f.write(nova_tipi.getbuffer())
            st.success("✅ TIPI Atualizada!")
            
        # 3. Base PIS/COFINS
        nova_pc = st.file_uploader("Base PIS/COFINS", type=['xlsx'], key='up_pc_base')
        if nova_pc:
            with open(".streamlit/CST_Pis_Cofins.xlsx", "wb") as f: f.write(nova_pc.getbuffer())
            st.success("✅ PIS/COFINS Atualizada!")

# --- 3. TÍTULO PRINCIPAL ---
caminho_titulo = ".streamlit/Sentinela.png"
if os.path.exists(caminho_titulo):
    col_c1, col_tit, col_c2 = st.columns([3, 4, 3])
    with col_tit: st.image(caminho_titulo, use_column_width=True)
elif os.path.exists("Sentinela.png"):
    col_c1, col_tit, col_c2 = st.columns([3, 4, 3])
    with col_tit: st.image("Sentinela.png", use_column_width=True)
else:
    st.markdown("<h1 style='text-align: center; color: #FF6F00; margin-bottom:0;'>SENTINELA</h1>", unsafe_allow_html=True)

# --- 4. ÁREA DE GABARITOS (NOVA FUNCIONALIDADE) ---
with st.expander("📂 Baixar Modelos em Branco (Gabaritos)"):
    st.write("Não tem as planilhas ainda? Baixe os modelos abaixo, preencha e suba na barra lateral.")
    c_gab1, c_gab2, c_gab3 = st.columns(3)
    
    # Modelo ICMS
    with c_gab1:
        df_mod_icms = pd.DataFrame({'NCM': ['00000000'], 'CST_ESPERADO': ['00'], 'ALIQUOTA_ESPERADA': [18.0]})
        b_icms = io.BytesIO()
        with pd.ExcelWriter(b_icms, engine='xlsxwriter') as w: df_mod_icms.to_excel(w, index=False)
        st.download_button("📥 Modelo ICMS", b_icms.getvalue(), "modelo_icms.xlsx", use_container_width=True)

    # Modelo IPI
    with c_gab2:
        df_mod_ipi = pd.DataFrame({'NCM': ['00000000'], 'ALIQUOTA_IPI': [0.0]})
        b_ipi = io.BytesIO()
        with pd.ExcelWriter(b_ipi, engine='xlsxwriter') as w: df_mod_ipi.to_excel(w, index=False)
        st.download_button("📥 Modelo TIPI (IPI)", b_ipi.getvalue(), "modelo_tipi.xlsx", use_container_width=True)

    # Modelo PIS/COFINS
    with c_gab3:
        df_mod_pc = pd.DataFrame({'NCM': ['00000000'], 'CST_ENTRADA': ['50'], 'CST_SAIDA': ['01']})
        b_pc = io.BytesIO()
        with pd.ExcelWriter(b_pc, engine='xlsxwriter') as w: df_mod_pc.to_excel(w, index=False)
        st.download_button("📥 Modelo PIS/COFINS", b_pc.getvalue(), "modelo_pis_cofins.xlsx", use_container_width=True)

# --- 5. ÁREA DE UPLOAD XML ---
st.markdown("---")
col_ent, col_sai = st.columns(2, gap="large")
with col_ent:
    st.markdown("### 📥 1. Entradas")
    st.markdown("---")
    up_ent_xml = st.file_uploader("📂 XMLs de Notas Fiscais", type='xml', accept_multiple_files=True, key="ent_xml")
    up_ent_aut = st.file_uploader("🔍 Relatório Autenticidade (Sefaz)", type=['xlsx', 'csv'], key="ent_aut")
with col_sai:
    st.markdown("### 📤 2. Saídas")
    st.markdown("---")
    up_sai_xml = st.file_uploader("📂 XMLs de Notas Fiscais", type='xml', accept_multiple_files=True, key="sai_xml")
    up_sai_aut = st.file_uploader("🔍 Relatório Autenticidade (Sefaz)", type=['xlsx', 'csv'], key="sai_aut")

# ==============================================================================
# --- 6. LÓGICA DO SISTEMA ---
# ==============================================================================

@st.cache_data(ttl=5)
def carregar_bases_mestre():
    df_tipi = pd.DataFrame()
    df_pc_base = pd.DataFrame()
    df_icms_base = pd.DataFrame()

    def encontrar(nome):
        ps = [f".streamlit/{nome}", nome, f".streamlit/{nome.lower()}", nome.lower()]
        for p in ps:
            if os.path.exists(p): return p
        return None

    # A. ICMS
    c_icms = encontrar("base_icms.xlsx")
    if c_icms:
        try:
            df_raw = pd.read_excel(c_icms, dtype=str)
            # Tenta pegar por nome ou índice (Garante robustez)
            cols = df_raw.columns
            if 'NCM' in cols and 'CST_ESPERADO' in cols:
                df_icms_base = df_raw[['NCM', 'CST_ESPERADO', 'ALIQUOTA_ESPERADA']].copy()
            else:
                df_icms_base = df_raw.iloc[:, [0, 1, 2]].copy()
            
            df_icms_base.columns = ['NCM', 'CST', 'ALIQ']
            df_icms_base['NCM'] = df_icms_base['NCM'].str.replace(r'\D', '', regex=True).str.zfill(8)
            df_icms_base['ALIQ'] = df_icms_base['ALIQ'].str.replace(',', '.').astype(float)
        except: pass

    # B. TIPI
    c_tipi = encontrar("tipi.xlsx")
    if c_tipi:
        try:
            df_raw = pd.read_excel(c_tipi, dtype=str)
            df_tipi = df_raw.iloc[:, [0, 1]].copy()
            df_tipi.columns = ['NCM', 'ALIQ']
            df_tipi['NCM'] = df_tipi['NCM'].str.replace(r'\D', '', regex=True).str.zfill(8)
            df_tipi['ALIQ'] = df_tipi['ALIQ'].str.upper().replace('NT', '0').str.strip().str.replace(',', '.')
        except: pass

    # C. PIS/COFINS
    c_pc = encontrar("CST_Pis_Cofins.xlsx")
    if c_pc:
        try:
            df_raw = pd.read_excel(c_pc, dtype=str)
            if len(df_raw.columns) >= 3:
                df_pc_base = df_raw.iloc[:, [0, 1, 2]].copy()
                df_pc_base.columns = ['NCM', 'CST_ENT', 'CST_SAI']
                df_pc_base['NCM'] = df_pc_base['NCM'].str.replace(r'\D', '', regex=True).str.zfill(8)
                df_pc_base['CST_SAI'] = df_pc_base['CST_SAI'].str.replace(r'\D', '', regex=True).str.zfill(2)
        except: pass

    return df_icms_base, df_tipi, df_pc_base

# Carrega e converte
df_icms, df_tipi, df_pc = carregar_bases_mestre()

bases = {"ICMS": {}, "TIPI": {}, "PC": {}}
if not df_icms.empty:
    bases["ICMS"] = df_icms.set_index('NCM').to_dict('index')
if not df_tipi.empty:
    bases["TIPI"] = dict(zip(df_tipi['NCM'], df_tipi['ALIQ']))
if not df_pc.empty:
    bases["PC"] = dict(zip(df_pc['NCM'], df_pc['CST_SAI']))

# --- EXTRAÇÃO XML ---
def extrair_tags(arquivos, origem):
    lista = []
    erros = []
    for arq in arquivos:
        try:
            raw = arq.read()
            try: txt = raw.decode('utf-8')
            except: txt = raw.decode('latin-1')
            txt = re.sub(r' xmlns="[^"]+"', '', txt)
            root = ET.fromstring(txt)
            if 'resNFe' in root.tag or 'procEvento' in root.tag: continue
            inf = root.find('.//infNFe')
            if inf is None:
                erros.append(f"{arq.name}: XML Inválido")
                continue
            
            chave = inf.attrib.get('Id','')[3:]
            dets = root.findall('.//det')
            
            for det in dets:
                prod = det.find('prod')
                imp = det.find('imposto')
                
                def v(n, t, fl=False):
                    if n is None: return 0.0 if fl else ""
                    x = n.find(t)
                    return (float(x.text) if fl else x.text) if x is not None else (0.0 if fl else "")
                
                row = {
                    "Origem": origem, "Arquivo": arq.name, "Chave": chave,
                    "NCM": v(prod, 'NCM'), "CFOP": v(prod, 'CFOP'), "Valor": v(prod, 'vProd', True), "Desc Prod": v(prod, 'xProd'),
                    "CST_ICMS": "", "Aliq_ICMS": 0.0, "Aliq_IPI": 0.0, "CST_PIS": "", "CST_COFINS": ""
                }
                
                if imp:
                    icms = imp.find('ICMS')
                    if icms:
                        for c in icms:
                            if c.find('CST') is not None: row['CST_ICMS'] = c.find('CST').text
                            elif c.find('CSOSN') is not None: row['CST_ICMS'] = c.find('CSOSN').text
                            if c.find('pICMS') is not None: row['Aliq_ICMS'] = float(c.find('pICMS').text)
                    ipi = imp.find('IPI')
                    if ipi:
                        for c in ipi:
                            if c.find('pIPI') is not None: row['Aliq_IPI'] = float(c.find('pIPI').text)
                    
                    # PIS COFINS (Simplificado)
                    pis = imp.find('PIS')
                    if pis: 
                        for c in pis: 
                            if c.find('CST') is not None: row['CST_PIS'] = c.find('CST').text
                    cof = imp.find('COFINS')
                    if cof: 
                        for c in cof: 
                            if c.find('CST') is not None: row['CST_COFINS'] = c.find('CST').text

                lista.append(row)
        except: erros.append(f"{arq.name}: Erro Leitura")
    return pd.DataFrame(lista), erros

# --- STATUS ---
def check_status(df, file):
    if df.empty: return df
    if not file: 
        df['Status_Sefaz'] = "N/A"
        return df
    try:
        if file.name.endswith('xlsx'): s = pd.read_excel(file, dtype=str)
        else: s = pd.read_csv(file, dtype=str)
        m = dict(zip(s.iloc[:,0].str.replace(r'\D','',regex=True), s.iloc[:,-1]))
        df['Status_Sefaz'] = df['Chave'].map(m).fillna("Não Localizado")
    except: df['Status_Sefaz'] = "Erro"
    return df

# --- AUDITORIAS ---
def audit_ipi(df):
    if df.empty or not bases["TIPI"]: return df
    def chk(row):
        esp = bases["TIPI"].get(str(row['NCM']))
        if not esp: return "NCM Off"
        if esp == 'NT': return "OK"
        try: return "OK" if abs(row['Aliq_IPI'] - float(esp)) < 0.1 else f"Div (XML:{row['Aliq_IPI']} | TIPI:{esp})"
        except: return "Erro"
    df['Auditoria_IPI'] = df.apply(chk, axis=1)
    return df

def audit_icms(df):
    if df.empty or not bases["ICMS"]: return df
    def chk(row):
        regra = bases["ICMS"].get(str(row['NCM']))
        if not regra: return "Sem Base ICMS"
        erros = []
        if str(row['CST_ICMS']) != str(regra['CST']):
            erros.append(f"CST: {row['CST_ICMS']} (Esp: {regra['CST']})")
        try:
            if abs(row['Aliq_ICMS'] - float(regra['ALIQ'])) > 0.1:
                erros.append(f"Aliq: {row['Aliq_ICMS']} (Esp: {regra['ALIQ']})")
        except: pass
        return "OK" if not erros else " | ".join(erros)
    df['Auditoria_ICMS'] = df.apply(chk, axis=1)
    return df

# --- 6. EXECUÇÃO ---
df_e, _ = extrair_tags(up_ent_xml, "Entrada")
df_e = check_status(df_e, up_ent_aut)

df_s, _ = extrair_tags(up_
