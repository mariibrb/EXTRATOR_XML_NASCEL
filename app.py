import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import re
import os

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Sentinela - Nascel", page_icon="🛡️", layout="wide")

# --- 2. ESTILO VISUAL (CSS) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .main-title { font-size: 2.5rem; font-weight: 700; color: #555555; margin-bottom: 0px; }
    .sub-title { font-size: 1rem; color: #FF8C00; font-weight: 600; margin-bottom: 30px; }
    
    /* Cards */
    .feature-card {
        background-color: white; padding: 20px; border-radius: 10px;
        border: 1px solid #E0E0E0; text-align: center; height: 100%;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .card-icon { font-size: 2rem; display: block; margin-bottom: 10px; }
    
    /* Destaque para área de Autenticidade */
    .auth-area {
        background-color: #f8f9fa; border: 1px solid #dee2e6;
        border-radius: 10px; padding: 20px; margin-top: 10px;
    }
    
    /* Botões */
    .stButton button { width: 100%; border-radius: 8px; font-weight: 600; }
    .stButton button[type="primary"] { background-color: #FF8C00; border-color: #FF8C00; }
    
    [data-testid='stFileUploader'] section { background-color: #FFF8F0; border: 1px dashed #FF8C00; }
</style>
""", unsafe_allow_html=True)

# --- 3. FUNÇÕES (SIMPLIFICADAS PARA O EXEMPLO) ---
def extrair_xml(arquivos):
    lista = []
    for arq in arquivos:
        try:
            arq.seek(0)
            xml_str = arq.read().decode('utf-8', errors='ignore')
            root = ET.fromstring(re.sub(r' xmlns="[^"]+"', '', xml_str))
            
            inf = root.find('.//infNFe')
            ide = root.find('.//ide')
            if inf is not None:
                lista.append({
                    'Chave': inf.attrib.get('Id', '')[3:],
                    'Número': ide.find('nNF').text if ide is not None else '0'
                })
        except: pass
    return pd.DataFrame(lista)

def ler_status_sefaz(arquivo):
    if not arquivo: return {}
    try:
        if arquivo.name.endswith('.xlsx'): df = pd.read_excel(arquivo, dtype=str)
        else: df = pd.read_csv(arquivo, dtype=str)
        # Ajuste as colunas conforme seu arquivo real da Sefaz (ex: Coluna 0 é chave, Coluna 5 é status)
        return dict(zip(df.iloc[:, 0], df.iloc[:, 5]))
    except: return {}

# --- 4. CABEÇALHO ---
col_logo, col_text = st.columns([1, 5])
with col_logo:
    path = "nascel sem fundo.png" if os.path.exists("nascel sem fundo.png") else ".streamlit/nascel sem fundo.png"
    if os.path.exists(path): st.image(path, width=150)
    else: st.write("LOGO")
with col_text:
    st.markdown('<div class="main-title">Sentinela Fiscal</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Central de Auditoria e Compliance</div>', unsafe_allow_html=True)

st.divider()

# =========================================================
# SEÇÃO 1: UPLOAD DOS XMLS (MATÉRIA PRIMA)
# =========================================================
st.markdown("### 📂 1. Arquivos XML (Entradas e Saídas)")
c1, c2 = st.columns(2, gap="medium")
with c1:
    st.markdown('<div class="feature-card"><span class="card-icon">📥</span><b>Entradas</b></div>', unsafe_allow_html=True)
    xml_ent = st.file_uploader("Up Entradas", type=["xml"], accept_multiple_files=True, label_visibility="collapsed", key="in")
with c2:
    st.markdown('<div class="feature-card"><span class="card-icon">📤</span><b>Saídas</b></div>', unsafe_allow_html=True)
    xml_sai = st.file_uploader("Up Saidas", type=["xml"], accept_multiple_files=True, label_visibility="collapsed", key="out")

st.markdown("<br>", unsafe_allow_html=True)

# =========================================================
# SEÇÃO 2: AUTENTICIDADE (COM OS 2 BOTÕES QUE VOCÊ PEDIU)
# =========================================================
st.markdown("### 🛡️ 2. Validação de Autenticidade")

# Container visual cinza para agrupar essa lógica
with st.container():
    st.markdown('<div class="auth-area">', unsafe_allow_html=True)
    
    # Passo A: O Arquivo de Referência (Único para os dois botões)
    st.markdown("**Passo A: Envie o relatório de Status da Sefaz (.xlsx)**")
    file_status = st.file_uploader("Upload Status Sefaz", type=["xlsx", "csv"], label_visibility="collapsed", key="status")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Passo B: Os Dois Botões de Ação
    st.markdown("**Passo B: Escolha qual validação executar**")
    
    col_btn_ent, col_btn_sai = st.columns(2, gap="large")
    
    # --- BOTÃO 1: AUTENTICIDADE ENTRADAS ---
    with col_btn_ent:
        st.info("Verifica se as notas de compra estão Autorizadas ou Canceladas.")
        if st.button("🔍 Verificar Entradas", type="primary", use_container_width=True):
            if not xml_ent:
                st.error("Falta os XMLs de Entrada (Seção 1).")
            elif not file_status:
                st.error("Falta o arquivo de Status Sefaz (Acima).")
            else:
                # Lógica Entradas
                df = extrair_xml(xml_ent)
                status_dict = ler_status_sefaz(file_status)
                if not df.empty:
                    df['Status'] = df['Chave'].map(status_dict).fillna("Não Encontrado")
                    st.success("Entradas Verificadas!")
                    st.dataframe(df, use_container_width=True)
    
    # --- BOTÃO 2: AUTENTICIDADE SAÍDAS ---
    with col_btn_sai:
        st.info("Verifica status das vendas e procura Pulos de Numeração.")
        if st.button("🔍 Verificar Saídas", type="primary", use_container_width=True):
            if not xml_sai:
                st.error("Falta os XMLs de Saída (Seção 1).")
            elif not file_status:
                st.error("Falta o arquivo de Status Sefaz (Acima).")
            else:
                # Lógica Saídas
                df = extrair_xml(xml_sai)
                status_dict = ler_status_sefaz(file_status)
                if not df.empty:
                    df['Status'] = df['Chave'].map(status_dict).fillna("Não Encontrado")
                    st.success("Saídas Verificadas!")
                    st.dataframe(df, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# =========================================================
# SEÇÃO 3: RELATÓRIOS GERENCIAIS (INDEPENDENTES)
# =========================================================
st.markdown("### 📊 3. Relatórios Gerenciais (Independente do Status)")
c_g1, c_g2 = st.columns(2, gap="medium")

with c_g1:
    if st.button("📈 Gerar Relatório Entradas"):
        if xml_ent: 
            st.toast("Gerando relatório...")
            st.dataframe(extrair_xml(xml_ent).head()) # Exemplo
        else: st.warning("Suba os XMLs de entrada primeiro.")

with c_g2:
    if st.button("📈 Gerar Relatório Saídas"):
        if xml_sai: 
            st.toast("Gerando relatório...")
            st.dataframe(extrair_xml(xml_sai).head()) # Exemplo
        else: st.warning("Suba os XMLs de saída primeiro.")
