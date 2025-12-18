import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import io
import re
import os

# --- 1. CONFIGURAÇÃO VISUAL ORIGINAL ---
st.set_page_config(
    page_title="Nascel | Auditoria",
    page_icon="🧡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Quicksand', sans-serif; }
    div.block-container { padding-top: 2rem !important; }
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
# --- 2. MOTORES DE EXTRAÇÃO E CÁLCULO ---
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
            dest = inf.find('dest')
            uf_dest = dest.find('UF').text if dest is not None and dest.find('UF') is not None else ""
            chave = inf.attrib.get('Id', '')[3:]
            
            for det in root.findall('.//det'):
                prod = det.find('prod')
                imp = det.find('imposto')
                row = {
                    'Fluxo': fluxo, 'Chave': chave, 'Arquivo': f.name,
                    'NCM': prod.find('NCM').text if prod.find('NCM') is not None else "",
                    'CFOP': prod.find('CFOP').text if prod.find('CFOP') is not None else "",
                    'Descricao': prod.find('xProd').text if prod.find('xProd') is not None else "",
                    'Valor_Prod': float(prod.find('vProd').text) if prod.find('vProd') is not None else 0.0,
                    'CST_ICMS_NF': "", 'Aliq_ICMS_NF': 0.0, 'Aliq_IPI_NF': 0.0,
                    'CST_PIS_NF': "", 'UF_Dest': uf_dest
                }
                # ICMS
                icms = imp.find('.//ICMS')
                if icms is not None:
                    for c in icms:
                        node = c.find('CST') or c.find('CSOSN')
                        if node is not None: row['CST_ICMS_NF'] = node.text
                        if c.find('pICMS') is not None: row['Aliq_ICMS_NF'] = float(c.find('pICMS').text)
                # IPI
                ipi = imp.find('.//IPI')
                if ipi is not None:
                    p_ipi = ipi.find('.//pIPI')
                    if p_ipi is not None: row['Aliq_IPI_NF'] = float(p_ipi.text)
                # PIS
                pis = imp.find('.//PIS')
                if pis is not None:
                    c_pis = pis.find('.//CST')
                    if c_pis is not None: row['CST_PIS_NF'] = c_pis.text
                data.append(row)
        except: continue
    return pd.DataFrame(data)

def realizar_auditoria(df, bi, bp, bt):
    if df.empty: return {}
    df['NCM_L'] = df['NCM'].str.replace(r'\D', '', regex=True).str.zfill(8)

    # DIFAL e ICMS (Coluna AO / Índice 40)
    if bi is not None:
        rules_i = bi.iloc[:, [0, 2, 6, 40]].copy()
        rules_i.columns = ['NCM_R', 'CST_INT_R', 'CST_EXT_R', 'ALIQ_INT_AO']
        rules_i['NCM_R'] = rules_i['NCM_R'].astype(str).str.zfill(8)
        df = pd.merge(df, rules_i, left_on='NCM_L', right_on='NCM_R', how='left')
        df['DIFAL_EST'] = df.apply(lambda r: (float(str(r['ALIQ_INT_AO']).replace(',','.')) - r['Aliq_ICMS_NF']) if str(r['CFOP']).startswith('6') else 0, axis=1)

    # PIS/COFINS
    if bp is not None:
        rules_p = bp.iloc[:, [0, 1, 2]].copy()
        rules_p.columns = ['NCM_P', 'CST_E_P', 'CST_S_P']
        rules_p['NCM_P'] = rules_p['NCM_P'].astype(str).str.zfill(8)
        df = pd.merge(df, rules_p, left_on='NCM_L', right_on='NCM_P', how='left')

    return {
        'ENTRADAS': df[df['Fluxo'] == 'Entrada'],
        'SAIDAS': df[df['Fluxo'] == 'Saída'],
        'ICMS': df[['Chave', 'NCM', 'CFOP', 'CST_ICMS_NF', 'CST_INT_R', 'CST_EXT_R']],
        'IPI': df[df['Aliq_IPI_NF'] > 0],
        'PIS_COFINS': df,
        'DIFAL': df[df['DIFAL_EST'] > 0]
    }

# ==============================================================================
# --- 3. SIDEBAR (STATUS COM CAMINHOS CORRETOS) ---
# ==============================================================================

with st.sidebar:
    st.image(".streamlit/nascel sem fundo.png", use_column_width=True)
    st.markdown("---")
    st.subheader("📊 Status das Bases")
    
    # Caminhos baseados no seu print
    p_i = ".streamlit/ICMS.xlsx"
    p_p = ".streamlit/CST_Pis_Cofins.xlsx"
    p_t = ".streamlit/tipi.xlsx"
    
    st.success("🟢 ICMS OK (Regra AO)") if os.path.exists(p_i) else st.error("🔴 ICMS OFF")
    st.success("🟢 PIS/COF OK") if os.path.exists(p_p) else st.error("🔴 PIS/COF OFF")
    st.success("🟢 TIPI OK") if os.path.exists(p_t) else st.warning("🟡 TIPI OFF")

    with st.expander("💾 Atualizar Bases"):
        up_i = st.file_uploader("Trocar ICMS", type=['xlsx'], key='side_i')
        if up_i:
            with open(".streamlit/ICMS.xlsx", "wb") as f: f.write(up_i.getbuffer())
            st.rerun()

# ==============================================================================
# --- 4. ÁREA CENTRAL (LAYOUT ORIGINAL) ---
# ==============================================================================

col_l, col_tit, col_r = st.columns([3, 4, 3])
with col_tit: st.image(".streamlit/Sentinela.png", use_column_width=True)

st.markdown("---")
col_ent, col_sai = st.columns(2, gap="large")

with col_ent:
    st.markdown("### 📥 1. Entradas")
    ue = st.file_uploader("📂 XMLs", type='xml', accept_multiple_files=True, key="m_ue")
    ae = st.file_uploader("🔍 Autenticidade Entradas", type=['xlsx'], key="m_ae")

with col_sai:
    st.markdown("### 📤 2. Saídas")
    us = st.file_uploader("📂 XMLs", type='xml', accept_multiple_files=True, key="m_us")
    as_ = st.file_uploader("🔍 Autenticidade Saídas", type=['xlsx'], key="m_as")

if st.button("🚀 EXECUTAR AUDITORIA COMPLETA", type="primary", use_container_width=True):
    with st.spinner("Gerando auditoria completa com as 6 abas..."):
        bi = pd.read_excel(p_i, dtype=str) if os.path.exists(p_i) else None
        bp = pd.read_excel(p_p, dtype=str) if os.path.exists(p_p) else None
        bt = pd.read_excel(p_t, dtype=str) if os.path.exists(p_t) else None
        
        df_total = pd.concat([extrair_xmls(ue, "Entrada"), extrair_xmls(us, "Saída")], ignore_index=True)
        abas = realizar_auditoria(df_total, bi, bp, bt)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for nome, dados in abas.items():
                dados.to_excel(writer, sheet_name=nome, index=False)
        
        st.success("Auditoria Concluída!")
        st.download_button("💾 BAIXAR RELATÓRIO (ENT/SAI/ICMS/IPI/PIS/DIFAL)", output.getvalue(), "Auditoria_Nascel_Sentinela.xlsx")
