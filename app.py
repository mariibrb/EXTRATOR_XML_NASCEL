import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import io
import re
import os

# --- 1. CONFIGURAÇÃO VISUAL (ORIGINAL) ---
st.set_page_config(
    page_title="Nascel | Auditoria",
    page_icon="🧡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS PERSONALIZADO (MANTIDO)
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
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# --- 2. FUNÇÕES TÉCNICAS (EXTRAÇÃO E AUDITORIA) ---
# ==============================================================================

def extrair_dados_xml(files, fluxo):
    data = []
    for f in files:
        try:
            raw = f.read()
            try: txt = raw.decode('utf-8')
            except: txt = raw.decode('latin-1')
            # Remove namespaces para facilitar busca
            txt = re.sub(r' xmlns="[^"]+"', '', txt)
            root = ET.fromstring(txt)
            
            infNFe = root.find('.//infNFe')
            if infNFe is None: continue
            chave = infNFe.attrib.get('Id', '')[3:]
            
            for det in root.findall('.//det'):
                prod = det.find('prod')
                ncm = prod.find('NCM').text if prod.find('NCM') is not None else ""
                cfop = prod.find('CFOP').text if prod.find('CFOP') is not None else ""
                vProd = float(prod.find('vProd').text) if prod.find('vProd') is not None else 0.0
                
                # Extração de Impostos
                imposto = det.find('imposto')
                cst_icms = ""
                pICMS = 0.0
                if imposto is not None:
                    icms = imposto.find('ICMS')
                    if icms is not None:
                        for c in icms:
                            cst_node = c.find('CST') or c.find('CSOSN')
                            if cst_node is not None: cst_icms = cst_node.text
                            if c.find('pICMS') is not None: pICMS = float(c.find('pICMS').text)
                
                data.append({
                    'Fluxo': fluxo, 'Arquivo': f.name, 'Chave': chave,
                    'NCM': ncm, 'CFOP': cfop, 'Valor': vProd,
                    'CST_NF': cst_icms, 'Aliq_NF': pICMS
                })
        except: continue
    return pd.DataFrame(data)

def auditoria_fiscal(df, df_regras_icms):
    if df.empty or df_regras_icms is None: return df
    
    # Padroniza Base ICMS (9 Colunas)
    df_regras_icms.columns = ['NCM','DESC_INT','CST_INT','ALIQ_INT','RED_INT','DESC_EXT','CST_EXT','ALIQ_EXT','OBS']
    df_regras_icms['NCM'] = df_regras_icms['NCM'].str.replace(r'\D', '', regex=True).str.zfill(8)
    
    # Merge
    df['NCM_Limpo'] = df['NCM'].str.replace(r'\D', '', regex=True).str.zfill(8)
    res = pd.merge(df, df_regras_icms, left_on='NCM_Limpo', right_on='NCM', how='left', suffixes=('', '_R'))
    
    def validar(row):
        if pd.isna(row['NCM_R']): return "NCM NÃO CADASTRADO"
        cfop = str(row['CFOP'])
        eh_interno = cfop.startswith('5')
        cst_nota = str(row['CST_NF']).zfill(2)
        
        # Define regra pelo CFOP (Interno ou Externo)
        cst_esperado = str(row['CST_INT']).zfill(2) if eh_interno else str(row['CST_EXT']).zfill(2)
        
        if cst_nota != cst_esperado:
            return f"ERRO CST (Nota: {cst_nota} | Esperado: {cst_esperado})"
        return "OK"

    res['STATUS_ICMS'] = res.apply(validar, axis=1)
    return res

# ==============================================================================
# --- 3. SIDEBAR: LOGO NASCEL, STATUS, GESTÃO DE BASES E GABARITOS ---
# ==============================================================================
with st.sidebar:
    caminho_logo = ".streamlit/nascel sem fundo.png"
    if os.path.exists(caminho_logo): st.image(caminho_logo, use_column_width=True)
    else: st.markdown("<h1 style='color:#FF6F00; text-align:center;'>Nascel</h1>", unsafe_allow_html=True)
    
    st.markdown("---")

    def get_file(name):
        paths = [f".streamlit/{name}", name, f"bases/{name}"]
        for p in paths:
            if os.path.exists(p): return p
        return None

    st.subheader("📊 Status das Bases")
    f_icms = get_file("base_icms.xlsx")
    f_tipi = get_file("tipi.xlsx")
    f_pc = get_file("CST_Pis_Cofins.xlsx")

    if f_icms: st.success("🟢 Base ICMS OK")
    else: st.error("🔴 Base ICMS Ausente")

    if f_tipi: st.success("🟢 Base TIPI OK")
    else: st.error("🔴 Base TIPI Ausente")

    if f_pc: st.success("🟢 Base PIS/COF OK")
    else: st.error("🔴 Base PIS/COF Ausente")

    st.markdown("---")

    with st.expander("💾 1. GERENCIAR BASES ATUAIS"):
        st.caption("Regras de ICMS")
        if f_icms:
            with open(f_icms, "rb") as f: st.download_button("📥 Baixar ICMS", f, "base_icms.xlsx", key="side_dl_icms")
        up_icms = st.file_uploader("Nova Base ICMS", type=['xlsx'], key='side_up_icms')
        if up_icms:
            with open("base_icms.xlsx", "wb") as f: f.write(up_icms.getbuffer())
            st.success("ICMS Atualizado!")

        st.markdown("---")
        st.caption("Tabela TIPI")
        if f_tipi:
            with open(f_tipi, "rb") as f: st.download_button("📥 Baixar TIPI", f, "tipi.xlsx", key="side_dl_tipi")
        up_tipi = st.file_uploader("Nova TIPI", type=['xlsx'], key='side_up_tipi')
        if up_tipi:
            with open("tipi.xlsx", "wb") as f: f.write(up_tipi.getbuffer())
            st.success("TIPI Atualizada!")

        st.markdown("---")
        st.caption("Regras PIS/COFINS")
        if f_pc:
            with open(f_pc, "rb") as f: st.download_button("📥 Baixar PIS/COF", f, "CST_Pis_Cofins.xlsx", key="side_dl_pc")
        up_pc = st.file_uploader("Nova PIS/COF", type=['xlsx'], key='side_up_pc')
        if up_pc:
            with open("CST_Pis_Cofins.xlsx", "wb") as f: f.write(up_pc.getbuffer())
            st.success("PIS/COF Atualizado!")

    with st.expander("📂 2. MODELOS DE GABARITO"):
        st.caption("Modelos para novos cadastros")
        df_m_icms = pd.DataFrame(columns=['NCM','DESC_INT','CST_INT','ALIQ_INT','RED_INT','DESC_EXT','CST_EXT','ALIQ_EXT','OBS'])
        b_icms = io.BytesIO()
        with pd.ExcelWriter(b_icms, engine='xlsxwriter') as w: df_m_icms.to_excel(w, index=False)
        st.download_button("📥 Gabarito ICMS", b_icms.getvalue(), "modelo_icms.xlsx")
        
        st.markdown("---")
        df_m_pc = pd.DataFrame({'NCM': ['00000000'], 'CST_ENT': ['50'], 'CST_SAI': ['01']})
        b_pc = io.BytesIO()
        with pd.ExcelWriter(b_pc, engine='xlsxwriter') as w: df_m_pc.to_excel(w, index=False)
        st.download_button("📥 Gabarito PIS/COF", b_pc.getvalue(), "modelo_pc.xlsx")

# ==============================================================================
# --- 3. ÁREA CENTRAL: LOGO SENTINELA E OPERAÇÃO ---
# ==============================================================================

caminho_titulo = ".streamlit/Sentinela.png"
if os.path.exists(caminho_titulo):
    col_l, col_tit, col_r = st.columns([3, 4, 3])
    with col_tit: st.image(caminho_titulo, use_column_width=True)
else:
    st.markdown("<h1 style='text-align: center; color: #FF6F00;'>SENTINELA</h1>", unsafe_allow_html=True)

st.markdown("---")

col_ent, col_sai = st.columns(2, gap="large")
with col_ent:
    st.markdown("### 📥 1. Entradas")
    up_ent_xml = st.file_uploader("📂 XMLs", type='xml', accept_multiple_files=True, key="ent_xml")
    up_ent_aut = st.file_uploader("🔍 Autenticidade Entradas", type=['xlsx', 'csv'], key="ent_aut")

with col_sai:
    st.markdown("### 📤 2. Saídas")
    up_sai_xml = st.file_uploader("📂 XMLs", type='xml', accept_multiple_files=True, key="sai_xml")
    up_sai_aut = st.file_uploader("🔍 Autenticidade Saídas", type=['xlsx', 'csv'], key="sai_aut")

st.markdown("---")
if st.button("🚀 EXECUTAR AUDITORIA COMPLETA"):
    if not up_ent_xml and not up_sai_xml:
        st.warning("Carregue arquivos XML para processar.")
    else:
        with st.spinner("Processando Auditoria..."):
            # Carrega Regras
            base_path = get_file("base_icms.xlsx")
            df_regras = pd.read_excel(base_path, dtype=str) if base_path else None
            
            # Extração
            df_e = extrair_dados_xml(up_ent_xml, "Entrada")
            df_s = extrair_dados_xml(up_sai_xml, "Saída")
            df_total = pd.concat([df_e, df_s], ignore_index=True)
            
            # Auditoria
            resultado = auditoria_fiscal(df_total, df_regras)
            
            st.success("Análise concluída!")
            st.dataframe(resultado, use_container_width=True)
            
            # Download Final
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as wr:
                resultado.to_excel(wr, index=False)
            st.download_button("💾 Baixar Relatório Final", buf.getvalue(), "Auditoria_Sentinela.xlsx")
