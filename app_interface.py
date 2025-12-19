import streamlit as st
import os
import io
import pandas as pd
from motor_fiscal import extrair_dados_xml, gerar_excel_final

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Nascel | Auditoria", page_icon="🧡", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Quicksand', sans-serif; }
    .stApp { background-color: #F7F7F7; }
    h1, h2, h3, h4 { color: #FF6F00 !important; font-weight: 700; }
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
        background-color: white; padding: 20px; border-radius: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    .stButton>button { background-color: #FF6F00; color: white; border-radius: 25px; font-weight: bold; width: 100%; border: none; padding: 12px; }
    .stButton>button:hover { background-color: #E65100; transform: scale(1.02); }
    /* Estilo para os campos de upload */
    .stFileUploader { padding: 10px; border: 1px dashed #FF6F00; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR (CONFIGURAÇÕES E BASES) ---
with st.sidebar:
    if os.path.exists(".streamlit/nascel sem fundo.png"):
        st.image(".streamlit/nascel sem fundo.png", use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 🛠️ Bases de Dados")
    
    # 1. BOTÃO DE AUTENTICIDADE (O que você pediu para o Status)
    st.markdown("##### 🔍 1. Base de Autenticidade")
    base_autenticidade = st.file_uploader("Subir arquivo com Chave e Status", type=['xlsx', 'csv'], key="auth")
    st.caption("O sistema usará a Coluna A (Chave) e Coluna B (Status) para cruzar.")

    st.markdown("---")
    
    # 2. OUTRAS BASES TRIBUTÁRIAS
    st.markdown("##### 📑 2. Bases de Verificação")
    base_icms = st.file_uploader("Base ICMS (Opcional)", type=['xlsx'], key='ui')
    base_pis = st.file_uploader("Base PIS/COFINS (Opcional)", type=['xlsx'], key='up')

    st.markdown("---")
    with st.expander("📥 **Gabaritos de Modelo**"):
        df_m = pd.DataFrame(columns=['CHAVE', 'STATUS'])
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as wr: df_m.to_excel(wr, index=False)
        st.download_button("📄 Modelo Autenticidade", buf.getvalue(), "modelo_autenticidade.xlsx", use_container_width=True)

# --- ÁREA CENTRAL (LOGOTIPO E TÍTULO) ---
c1, c2, c3 = st.columns([3, 4, 3])
with c2:
    if os.path.exists(".streamlit/Sentinela.png"):
        st.image(".streamlit/Sentinela.png", use_container_width=True)
    else:
        st.title("🛡️ Sentinela Fiscal")

st.markdown("<h4 style='text-align: center; color: #666 !important;'>Auditoria de XMLs com Cruzamento de Status</h4>", unsafe_allow_html=True)
st.markdown("---")

# --- ÁREA DE UPLOAD DE XMLS ---
col_e, col_s = st.columns(2, gap="large")

with col_e:
    st.markdown("### 📥 1. Entradas (Compras)")
    xml_ent = st.file_uploader("Arraste os XMLs de Entrada aqui", type='xml', accept_multiple_files=True, key="ue")

with col_s:
    st.markdown("### 📤 2. Saídas (Vendas)")
    xml_sai = st.file_uploader("Arraste os XMLs de Saída aqui", type='xml', accept_multiple_files=True, key="us")

# --- BOTÃO DE EXECUÇÃO ---
st.markdown("<br>", unsafe_allow_html=True)
if st.button("🚀 EXECUTAR AUDITORIA E CRUZAMENTO", type="primary", use_container_width=True):
    if not xml_ent and not xml_sai:
        st.error("Por favor, carregue pelo menos um arquivo XML para processar.")
    else:
        with st.spinner("O Sentinela está cruzando as chaves de acesso com a base de autenticidade..."):
            
            # Carrega a base de autenticidade se ela existir
            df_autent_data = None
            if base_autenticidade:
                try:
                    # Tenta ler Excel ou CSV
                    if base_autenticidade.name.endswith('.xlsx'):
                        df_autent_data = pd.read_excel(base_autenticidade)
                    else:
                        df_autent_data = pd.read_csv(base_autenticidade)
                except Exception as e:
                    st.error(f"Erro ao ler arquivo de autenticidade: {e}")

            # Chama o motor para Entradas
            df_e = extrair_dados_xml(xml_ent, "Entrada", df_autenticidade=df_autent_data)
            
            # Chama o motor para Saídas
            df_s = extrair_dados_xml(xml_sai, "Saída", df_autenticidade=df_autent_data)
            
            # Gera o Excel Final
            excel_binario = gerar_excel_final(df_e, df_s)
            
            st.success(f"🎉 Processamento concluído!")
            st.balloons()
            
            # Botão de Download
            st.download_button(
                label="💾 BAIXAR RELATÓRIO DE AUDITORIA",
                data=excel_binario,
                file_name="Auditoria_Sentinela_Status.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
