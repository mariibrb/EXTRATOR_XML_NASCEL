import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import io
import re
import os

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Nascel | Auditoria", page_icon="🧡", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Quicksand', sans-serif; }
    div.block-container { padding-top: 2rem !important; }
    .stApp { background-color: #F7F7F7; }
    h1, h2, h3 { color: #FF6F00 !important; font-weight: 700; }
    .stButton>button { background-color: #FF6F00; color: white; border-radius: 25px; font-weight: bold; width: 100%; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# --- 2. MOTORES DE EXTRAÇÃO E AUDITORIA ---
# ==============================================================================

def extrair_xmls(files, fluxo):
    data = []
    if not files: return pd.DataFrame()
    for f in files:
        try:
            f.seek(0)
            txt = f.read().decode('utf-8', errors='ignore')
            txt = re.sub(r' xmlns="[^"]+"', '', txt)
            root = ET.fromstring(txt)
            inf = root.find('.//infNFe')
            if inf is None: continue
            chave = inf.attrib.get('Id', '')[3:]
            for det in root.findall('.//det'):
                prod = det.find('prod')
                imp = det.find('imposto')
                row = {
                    'Fluxo': fluxo, 'Chave': chave, 'Arquivo': f.name,
                    'NCM': prod.find('NCM').text if prod.find('NCM') is not None else "",
                    'CFOP': prod.find('CFOP').text if prod.find('CFOP') is not None else "",
                    'Valor': float(prod.find('vProd').text) if prod.find('vProd') is not None else 0.0,
                    'CST_ICMS_NF': "", 'CST_PIS_NF': "", 'CST_COFINS_NF': ""
                }
                # ICMS
                icms = imp.find('.//ICMS')
                if icms is not None:
                    for c in icms:
                        node = c.find('CST') or c.find('CSOSN')
                        if node is not None: row['CST_ICMS_NF'] = node.text
                # PIS/COF
                pis = imp.find('.//PIS')
                if pis is not None:
                    for p in pis:
                        node = p.find('CST')
                        if node is not None: row['CST_PIS_NF'] = node.text
                data.append(row)
        except: continue
    return pd.DataFrame(data)

def auditoria_consolidada(df, df_icms, df_pc):
    if df.empty: return df
    
    # --- AUDITORIA ICMS (Lógica 9 colunas) ---
    if df_icms is not None and not df_icms.empty:
        # Seleciona NCM (0), CST Interno (2) e CST Externo (6)
        df_icms_red = df_icms.iloc[:, [0, 2, 6]].copy()
        df_icms_red.columns = ['NCM_R', 'CST_INT_R', 'CST_EXT_R']
        df_icms_red['NCM_R'] = df_icms_red['NCM_R'].astype(str).str.replace(r'\D', '', regex=True).str.zfill(8)
        
        df['NCM_L'] = df['NCM'].str.replace(r'\D', '', regex=True).str.zfill(8)
        df = pd.merge(df, df_icms_red, left_on='NCM_L', right_on='NCM_R', how='left')
        
        def check_icms(r):
            if pd.isna(r['NCM_R']): return "NCM NÃO CADASTRADO"
            # CFOP 5 = Interno, 6 = Externo
            esp = str(r['CST_INT_R']) if str(r['CFOP']).startswith('5') else str(r['CST_EXT_R'])
            esp = str(esp).split('.')[0].zfill(2)
            return "OK" if str(r['CST_ICMS_NF']).zfill(2) == esp else f"ERRO (Esp: {esp})"
        df['AUDIT_ICMS'] = df.apply(check_icms, axis=1)

    # --- AUDITORIA PIS/COFINS ---
    if df_pc is not None and not df_pc.empty:
        df_pc_red = df_pc.iloc[:, [0, 1, 2]].copy() # NCM, ENT, SAI
        df_pc_red.columns = ['NCM_P', 'CST_E_P', 'CST_S_P']
        df_pc_red['NCM_P'] = df_pc_red['NCM_P'].astype(str).str.replace(r'\D', '', regex=True).str.zfill(8)
        
        if 'NCM_L' not in df.columns: df['NCM_L'] = df['NCM'].str.replace(r'\D', '', regex=True).str.zfill(8)
        df = pd.merge(df, df_pc_red, left_on='NCM_L', right_on='NCM_P', how='left')
        
        def check_pc(r):
            if pd.isna(r['NCM_P']): return "NCM NÃO CADASTRADO"
            # Entrada (1,2,3) vs Saída (5,6,7)
            esp = str(r['CST_E_P']) if str(r['CFOP'])[0] in '123' else str(r['CST_S_P'])
            esp = str(esp).split('.')[0].zfill(2)
            return "OK" if str(r['CST_PIS_NF']).zfill(2) == esp else f"ERRO (Esp: {esp})"
        df['AUDIT_PIS_COFINS'] = df.apply(check_pc, axis=1)

    return df

# ==============================================================================
# --- 3. INTERFACE E SIDEBAR ---
# ==============================================================================
with st.sidebar:
    # Correção do erro da logo: Removido parâmetro inexistente error_handler
    logo_url = "https://raw.githubusercontent.com/seu-repo/main/nascel_logo.png"
    try:
        st.image(logo_url)
    except:
        st.title("Nascel")
    
    st.markdown("---")
    
    def get_b(name):
        for p in [f".streamlit/{name}", name]:
            if os.path.exists(p): return pd.read_excel(p, dtype=str)
        return None

    st.subheader("📊 Status das Bases")
    b_icms = get_b("base_icms.xlsx")
    b_pc = get_b("CST_Pis_Cofins.xlsx")
    
    if b_icms is not None: st.success("🟢 ICMS OK")
    else: st.error("🔴 ICMS Ausente")
    
    if b_pc is not None: st.success("🟢 PIS/COF OK")
    else: st.error("🔴 PIS/COF Ausente")

    with st.expander("📂 Gabaritos"):
        # Gabarito ICMS (A-I)
        df_m = pd.DataFrame(columns=['NCM','DESC_INT','CST_INT','ALIQ_INT','RED_INT','DESC_EXT','CST_EXT','ALIQ_EXT','OBS'])
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as w: df_m.to_excel(w, index=False)
        st.download_button("Modelo ICMS", buf.getvalue(), "modelo_icms.xlsx")

# --- ÁREA CENTRAL ---
st.markdown("<h1 style='text-align: center;'>SENTINELA</h1>", unsafe_allow_html=True)

col_e, col_s = st.columns(2)
with col_e:
    st.markdown("### 📥 Entradas")
    up_e = st.file_uploader("XMLs Entrada", type='xml', accept_multiple_files=True, key="ue")
    up_ae = st.file_uploader("Autenticidade Entradas", type=['xlsx','csv'], key="ae")
with col_s:
    st.markdown("### 📤 Saídas")
    up_s = st.file_uploader("XMLs Saída", type='xml', accept_multiple_files=True, key="us")
    up_as = st.file_uploader("Autenticidade Saídas", type=['xlsx','csv'], key="as")

if st.button("🚀 EXECUTAR AUDITORIA COMPLETA"):
    if not up_e and not up_s:
        st.warning("Suba os arquivos XML.")
    else:
        with st.spinner("Analisando todos os tributos..."):
            df_ent = extrair_xmls(up_e, "Entrada")
            df_sai = extrair_xmls(up_s, "Saída")
            df_total = pd.concat([df_ent, df_sai], ignore_index=True)
            
            # Auditoria Consolidada
            df_res = auditoria_consolidada(df_total, b_icms, b_pc)
            
            st.success("Análise Concluída!")
            st.dataframe(df_res, use_container_width=True)
            
            # Geração do Excel com todas as abas de análise
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Aba 1: Relatório Completo
                df_res.to_excel(writer, sheet_name='RELATORIO_GERAL', index=False)
                # Aba 2: Divergências encontradas
                cond = (df_res.get('AUDIT_ICMS', '') != 'OK') | (df_res.get('AUDIT_PIS_COFINS', '') != 'OK')
                df_res[cond].to_excel(writer, sheet_name='DIVERGENCIAS', index=False)
            
            st.download_button("💾 BAIXAR PLANILHA COM TODAS AS ABAS", output.getvalue(), "Auditoria_Consolidada.xlsx")
