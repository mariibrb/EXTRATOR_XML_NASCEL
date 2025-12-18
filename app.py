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
                    'CST_NF': "", 'PIS_NF': "", 'COFINS_NF': ""
                }
                # Captura CST ICMS
                icms = imp.find('.//ICMS')
                if icms is not None:
                    for c in icms:
                        node = c.find('CST') or c.find('CSOSN')
                        if node is not None: row['CST_NF'] = node.text
                # Captura CST PIS/COF
                pis = imp.find('.//PIS')
                if pis is not None:
                    for p in pis:
                        node = p.find('CST')
                        if node is not None: row['PIS_NF'] = node.text
                data.append(row)
        except: continue
    return pd.DataFrame(data)

def auditoria_consolidada(df, df_icms, df_pc):
    if df.empty: return df
    
    # --- AUDITORIA ICMS ---
    if df_icms is not None and not df_icms.empty:
        # Pega colunas por posição para evitar erro de nome
        df_icms = df_icms.iloc[:, [0, 2, 6]] # NCM, CST_INT, CST_EXT
        df_icms.columns = ['NCM_R', 'CST_INT_R', 'CST_EXT_R']
        df_icms['NCM_R'] = df_icms['NCM_R'].astype(str).str.replace(r'\D', '', regex=True).str.zfill(8)
        
        df['NCM_L'] = df['NCM'].str.replace(r'\D', '', regex=True).str.zfill(8)
        df = pd.merge(df, df_icms, left_on='NCM_L', right_on='NCM_R', how='left')
        
        def check_icms(r):
            if pd.isna(r['NCM_R']): return "NCM NÃO CADASTRADO"
            esp = str(r['CST_INT_R']) if str(r['CFOP']).startswith('5') else str(r['CST_EXT_R'])
            esp = esp.split('.')[0].zfill(2)
            nf = str(r['CST_NF']).zfill(2)
            return "OK" if nf == esp else f"ERRO (Esp: {esp})"
        df['AUDIT_ICMS'] = df.apply(check_icms, axis=1)

    # --- AUDITORIA PIS/COFINS ---
    if df_pc is not None and not df_pc.empty:
        df_pc = df_pc.iloc[:, [0, 1, 2]] # NCM, ENT, SAI
        df_pc.columns = ['NCM_P', 'CST_E_P', 'CST_S_P']
        df_pc['NCM_P'] = df_pc['NCM_P'].astype(str).str.replace(r'\D', '', regex=True).str.zfill(8)
        
        df = pd.merge(df, df_pc, left_on='NCM_L', right_on='NCM_P', how='left')
        
        def check_pc(r):
            if pd.isna(r['NCM_P']): return "NCM NÃO CADASTRADO"
            esp = str(r['CST_E_P']) if str(r['CFOP'])[0] in '123' else str(r['CST_S_P'])
            esp = esp.split('.')[0].zfill(2)
            return "OK" if str(r['PIS_NF']).zfill(2) == esp else f"ERRO (Esp: {esp})"
        df['AUDIT_PIS_COFINS'] = df.apply(check_pc, axis=1)

    return df

# ==============================================================================
# --- 3. INTERFACE E SIDEBAR ---
# ==============================================================================
with st.sidebar:
    st.image("https://raw.githubusercontent.com/seu-repo/main/nascel_logo.png", error_handler=lambda: st.title("Nascel"))
    st.markdown("---")
    
    def get_b(name):
        for p in [f".streamlit/{name}", name]:
            if os.path.exists(p): return pd.read_excel(p, dtype=str)
        return None

    st.subheader("📊 Status das Bases")
    b_icms = get_b("base_icms.xlsx")
    b_pc = get_b("CST_Pis_Cofins.xlsx")
    
    st.success("🟢 ICMS OK") if b_icms is not None else st.error("🔴 ICMS Ausente")
    st.success("🟢 PIS/COF OK") if b_pc is not None else st.error("🔴 PIS/COF Ausente")

    with st.expander("📂 Gabaritos"):
        # Gabarito ICMS 9 colunas
        df_m = pd.DataFrame(columns=['NCM','D1','CST_I','A1','R1','D2','CST_E','A2','O1'])
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as w: df_m.to_excel(w, index=False)
        st.download_button("Modelo ICMS", buf.getvalue(), "modelo_icms.xlsx")

# --- ÁREA CENTRAL ---
st.image(".streamlit/Sentinela.png", width=400) if os.path.exists(".streamlit/Sentinela.png") else st.title("SENTINELA")

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
            
            # Auditoria
            df_res = auditoria_consolidada(df_total, b_icms, b_pc)
            
            st.success("Análise Concluída!")
            st.dataframe(df_res, use_container_width=True)
            
            # Geração do Excel com Múltiplas Abas
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Aba 1: Tudo
                df_res.to_excel(writer, sheet_name='RELATORIO_GERAL', index=False)
                # Aba 2: Só Erros
                cond = (df_res.get('AUDIT_ICMS', '') != 'OK') | (df_res.get('AUDIT_PIS_COFINS', '') != 'OK')
                df_res[cond].to_excel(writer, sheet_name='DIVERGENCIAS', index=False)
            
            st.download_button("💾 BAIXAR RELATÓRIO COM TODAS AS ABAS", output.getvalue(), "Auditoria_Consolidada.xlsx")
