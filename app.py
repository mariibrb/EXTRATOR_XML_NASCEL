import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import io
import re
import os

# --- 1. CONFIGURAÇÃO VISUAL NASCEL (Cinza & Laranja & Fofo) ---
st.set_page_config(
    page_title="Nascel | Auditoria",
    page_icon="🧡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS PERSONALIZADO (A Mágica do Design)
st.markdown("""
    <style>
    /* Importando fonte arredondada fofa */
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Quicksand', sans-serif;
    }

    /* Fundo Geral - Cinza Suave */
    .stApp {
        background-color: #F7F7F7;
    }

    /* Barra Lateral - Cinza um pouco mais escuro */
    section[data-testid="stSidebar"] {
        background-color: #EEEEEE;
        border-right: 1px solid #E0E0E0;
    }

    /* Títulos em Laranja Nascel */
    h1, h2, h3 {
        color: #FF6F00 !important; /* Laranja forte */
    }
    
    /* Textos normais em Cinza Escuro */
    p, label, span {
        color: #555555;
    }

    /* Cards (Métricas) - Fofos e Arredondados */
    div[data-testid="metric-container"] {
        background-color: #FFFFFF;
        border-left: 5px solid #FF6F00; /* Detalhe Laranja */
        border-radius: 15px; /* Bem arredondado */
        padding: 15px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }

    /* Botões - Laranjas e Redondinhos */
    .stButton>button {
        background-color: #FF6F00;
        color: white;
        border-radius: 25px;
        border: none;
        font-weight: bold;
        padding: 10px 20px;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #E65100; /* Laranja mais escuro no hover */
        box-shadow: 0px 4px 8px rgba(0,0,0,0.2);
    }

    /* Expander (Abas laterais) */
    .streamlit-expanderHeader {
        background-color: #FFFFFF;
        border-radius: 10px;
        color: #FF6F00;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. BARRA LATERAL (LOGO E OS 6 BOTÕES) ---
with st.sidebar:
    # LOGO DA NASCEL
    if os.path.exists("logo_nascel.png"):
        st.image("logo_nascel.png", use_column_width=True)
    else:
        # Logo provisório "Fofo" feito em código caso não tenha a imagem
        st.markdown("""
            <div style='text-align: center; background: white; padding: 20px; border-radius: 20px; margin-bottom: 20px;'>
                <h1 style='margin:0; color:#FF6F00; font-size: 40px;'>nascel</h1>
                <span style='color: #888; font-size: 14px;'>inteligência fiscal</span>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("### 🧡 Painel de Upload")

    # --- GRUPO 1: ENTRADAS ---
    with st.expander("📥 1. ENTRADAS", expanded=True):
        up_ent_xml = st.file_uploader("XMLs (Notas)", type='xml', accept_multiple_files=True, key="ent_xml")
        up_ent_aut = st.file_uploader("Autenticidade (Excel)", type=['xlsx', 'csv'], key="ent_aut")
        up_ent_ger = st.file_uploader("Gerencial (Regras)", type=['xlsx'], key="ent_ger")

    # --- GRUPO 2: SAÍDAS ---
    with st.expander("📤 2. SAÍDAS", expanded=True):
        up_sai_xml = st.file_uploader("XMLs (Notas)", type='xml', accept_multiple_files=True, key="sai_xml")
        up_sai_aut = st.file_uploader("Autenticidade (Excel)", type=['xlsx', 'csv'], key="sai_aut")
        up_sai_ger = st.file_uploader("Gerencial (Regras)", type=['xlsx'], key="sai_ger")

# --- 3. CARREGAR BASES DO SISTEMA (TIPI/PISCOFINS) ---
@st.cache_data
def carregar_bases_sistema():
    bases = {"TIPI": {}, "PIS_COFINS": {}}
    if os.path.exists("TIPI.xlsx"):
        try:
            df = pd.read_excel("TIPI.xlsx", dtype=str)
            df['NCM'] = df.iloc[:, 0].str.replace(r'\D', '', regex=True)
            df['ALIQ'] = df.iloc[:, 1].str.replace(',', '.')
            bases["TIPI"] = dict(zip(df['NCM'], df['ALIQ']))
        except: pass
    if os.path.exists("Pis_Cofins.xlsx"):
        try:
            df = pd.read_excel("Pis_Cofins.xlsx", dtype=str)
            df['NCM'] = df.iloc[:, 0].str.replace(r'\D', '', regex=True)
            bases["PIS_COFINS"] = dict(zip(df['NCM'], df.iloc[:, 2]))
        except: pass
    return bases

bases_sistema = carregar_bases_sistema()

# --- 4. ENGINE DE PROCESSAMENTO ---
def extrair_xml(arquivos, origem):
    dados = []
    for arq in arquivos:
        try:
            raw = arq.read()
            try: xml = raw.decode('utf-8')
            except: xml = raw.decode('latin-1')
            
            xml = re.sub(r' xmlns="[^"]+"', '', xml)
            xml = re.sub(r' xmlns:xsi="[^"]+"', '', xml)
            root = ET.fromstring(xml)
            
            if "resNFe" in root.tag or "procEvento" in root.tag: continue
            inf = root.find('.//infNFe')
            if inf is None: continue
            
            chave = inf.attrib.get('Id', '')[3:]
            nat = root.find('.//ide/natOp').text if root.find('.//ide/natOp') is not None else ""
            
            dets = root.findall('.//det')
            for det in dets:
                prod = det.find('prod')
                imposto = det.find('imposto')
                
                def val(node, tag, is_float=False):
                    if node is None: return 0.0 if is_float else ""
                    x = node.find(tag)
                    if x is not None and x.text:
                        return float(x.text) if is_float else x.text
                    return 0.0 if is_float else ""

                item = {
                    "Origem": origem,
                    "Arquivo": arq.name,
                    "Chave": chave,
                    "Natureza": nat,
                    "Item": det.attrib.get('nItem'),
                    "NCM": val(prod, 'NCM'),
                    "CFOP": val(prod, 'CFOP'),
                    "Valor Prod": val(prod, 'vProd', True),
                    "CST ICMS": "", "Aliq ICMS": 0.0,
                    "Aliq IPI": 0.0, "CST PIS": "", "CST COFINS": ""
                }
                
                if imposto:
                    icms = imposto.find('ICMS')
                    if icms:
                        for c in icms:
                            if c.find('CST') is not None: item['CST ICMS'] = c.find('CST').text
                            elif c.find('CSOSN') is not None: item['CST ICMS'] = c.find('CSOSN').text
                            if c.find('pICMS') is not None: item['Aliq ICMS'] = float(c.find('pICMS').text)
                    ipi = imposto.find('IPI')
                    if ipi:
                        for c in ipi:
                            if c.find('pIPI') is not None: item['Aliq IPI'] = float(c.find('pIPI').text)
                    pis = imposto.find('PIS')
                    if pis:
                        for c in pis:
                            if c.find('CST') is not None: item['CST PIS'] = c.find('CST').text
                    cof = imposto.find('COFINS')
                    if cof:
                        for c in cof:
                            if c.find('CST') is not None: item['CST COFINS'] = c.find('CST').text
                
                dados.append(item)
        except: pass
    return pd.DataFrame(dados)

# --- 5. LÓGICA DE ANÁLISE ---
def aplicar_analises(df, status_file):
    if df.empty: return df
    
    # Autenticidade
    if status_file:
        try:
            if status_file.name.endswith('xlsx'): df_st = pd.read_excel(status_file, dtype=str)
            else: df_st = pd.read_csv(status_file, dtype=str)
            status_map = dict(zip(df_st.iloc[:, 0].str.replace(r'\D', '', regex=True), df_st.iloc[:, -1]))
            df['Status Sefaz'] = df['Chave'].map(status_map).fillna("Não Localizado")
        except: df['Status Sefaz'] = "Erro Status"
    else:
        df['Status Sefaz'] = "N/A"

    # IPI
    if bases_sistema["TIPI"]:
        def check_ipi(row):
            aliq_tipi = bases_sistema["TIPI"].get(str(row['NCM']))
            if aliq_tipi is None: return "NCM Off"
            if aliq_tipi == "NT": return "OK"
            try: return "OK" if abs(row['Aliq IPI'] - float(aliq_tipi)) < 0.1 else "Divergente"
            except: return "Erro"
        df['Audit IPI'] = df.apply(check_ipi, axis=1)

    # PIS COFINS
    if bases_sistema["PIS_COFINS"]:
        def check_pc(row):
            esp = bases_sistema["PIS_COFINS"].get(str(row['NCM']))
            if not esp: return "NCM Off"
            return "OK" if str(row['CST PIS']) == esp else f"Div (Esp: {esp})"
        df['Audit PIS/COF'] = df.apply(check_pc, axis=1)
        
    return df

# Execução
df_ent = extrair_xml(up_ent_xml, "Entrada") if up_ent_xml else pd.DataFrame()
df_ent_final = aplicar_analises(df_ent, up_ent_aut)

df_sai = extrair_xml(up_sai_xml, "Saída") if up_sai_xml else pd.DataFrame()
df_sai_final = aplicar_analises(df_sai, up_sai_aut)

# --- 6. DASHBOARD FOFO E LIMPO ---

st.title("🛡️ Auditoria Fiscal")

if df_ent_final.empty and df_sai_final.empty:
    st.info("👋 Olá! Vamos começar? Carregue seus arquivos no painel cinza ao lado.")
else:
    tab1, tab2, tab3 = st.tabs(["📊 Visão Geral", "📥 Entradas", "📤 Saídas"])
    
    with tab1:
        st.markdown("### Resumo")
        c1, c2, c3, c4 = st.columns(4)
        
        err_ent = len(df_ent_final[~df_ent_final['Status Sefaz'].str.contains("Autoriz|OK", na=False)]) if not df_ent_final.empty else 0
        err_sai = len(df_sai_final[~df_sai_final['Status Sefaz'].str.contains("Autoriz|OK", na=False)]) if not df_sai_final.empty else 0
        
        c1.metric("Total Notas", len(df_ent_final) + len(df_sai_final))
        c2.metric("Entradas", len(df_ent_final))
        c3.metric("Saídas", len(df_sai_final))
        c4.metric("Alertas Sefaz", err_ent + err_sai)
        
        st.markdown("---")
        g1, g2 = st.columns(2)
        if not df_ent_final.empty:
            with g1: st.caption("Status Entradas"); st.bar_chart(df_ent_final['Status Sefaz'].value_counts(), color="#FF6F00")
        if not df_sai_final.empty:
            with g2: st.caption("Status Saídas"); st.bar_chart(df_sai_final['Status Sefaz'].value_counts(), color="#FF6F00")

    with tab2:
        if not df_ent_final.empty: st.dataframe(df_ent_final, use_container_width=True)
        else: st.warning("Sem Entradas.")

    with tab3:
        if not df_sai_final.empty: st.dataframe(df_sai_final, use_container_width=True)
        else: st.warning("Sem Saídas.")

    st.markdown("---")
    if st.button("💾 Baixar Relatório (Excel)"):
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            if not df_ent_final.empty: df_ent_final.to_excel(writer, index=False, sheet_name='Entradas')
            if not df_sai_final.empty: df_sai_final.to_excel(writer, index=False, sheet_name='Saídas')
        st.download_button("📥 Clique para Baixar", buffer.getvalue(), "Relatorio_Nascel.xlsx", mime="application/vnd.ms-excel")
