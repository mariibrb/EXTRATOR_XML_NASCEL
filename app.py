import streamlit as st
import os

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Sentinela - Nascel",
    page_icon="🛡️",
    layout="wide"
)

# --- 2. CSS PERSONALIZADO (Identidade Nascel) ---
st.markdown("""
<style>
    /* Importando fonte limpa */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Título Principal */
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: #555555; /* Cinza Escuro Nascel */
        margin-bottom: 0px;
    }
    .sub-title {
        font-size: 1rem;
        color: #FF8C00; /* Laranja Nascel */
        font-weight: 600;
        margin-bottom: 30px;
    }

    /* Estilo dos Cards (Caixas Brancas) */
    .feature-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #E0E0E0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        text-align: center;
        transition: all 0.3s ease;
        height: 100%;
    }
    .feature-card:hover {
        transform: translateY(-5px);
        border-color: #FF8C00;
        box-shadow: 0 10px 15px rgba(255, 140, 0, 0.15);
    }
    
    /* Ícones dentro dos cards */
    .card-icon {
        font-size: 2rem;
        margin-bottom: 10px;
        display: block;
    }

    /* Ajuste dos botões para ocuparem largura total */
    .stButton button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
    }
    
    /* Uploaders personalizados */
    [data-testid='stFileUploader'] section {
        background-color: #FFF8F0; /* Fundo levemente laranja */
        border: 1px dashed #FF8C00;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. CABEÇALHO COM LOGO ---
col_logo, col_text = st.columns([1, 5])

with col_logo:
    # Ajuste de caminho: Verifica se o logo está na raiz ou na pasta .streamlit (conforme sua imagem)
    logo_path = "nascel sem fundo.png"
    if not os.path.exists(logo_path):
        logo_path = ".streamlit/nascel sem fundo.png"
    
    if os.path.exists(logo_path):
        st.image(logo_path, width=150)
    else:
        st.warning("Logo não encontrado")

with col_text:
    st.markdown('<div class="main-title">Sentinela Fiscal</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Central de Auditoria e Compliance - Nascel Contabilidade</div>', unsafe_allow_html=True)

st.divider()

# --- 4. ÁREA 1: UPLOAD DE DADOS (XMLs) ---
st.markdown("### 📂 1. Importação de Arquivos")
c1, c2 = st.columns(2, gap="medium")

with c1:
    st.markdown('<div class="feature-card"><span class="card-icon">📥</span><b>Entradas XML</b><br><span style="font-size:0.8rem; color:#777">Notas de Fornecedores</span></div>', unsafe_allow_html=True)
    xml_entradas = st.file_uploader("Upload Entradas", type=["xml"], accept_multiple_files=True, label_visibility="collapsed", key="in")

with c2:
    st.markdown('<div class="feature-card"><span class="card-icon">📤</span><b>Saídas XML</b><br><span style="font-size:0.8rem; color:#777">Notas de Venda</span></div>', unsafe_allow_html=True)
    xml_saidas = st.file_uploader("Upload Saídas", type=["xml"], accept_multiple_files=True, label_visibility="collapsed", key="out")

# Espaço
st.markdown("<br>", unsafe_allow_html=True)

# --- 5. ÁREA 2: BOTÕES DE AUTENTICIDADE ---
st.markdown("### 🛡️ 2. Validação de Autenticidade")
c3, c4 = st.columns(2, gap="medium")

with c3:
    st.info("Valida assinatura digital e status na Sefaz das compras.")
    if st.button("🔍 Verificar Autenticidade Entradas", type="primary", use_container_width=True):
        if not xml_entradas:
            st.error("⚠️ Faça o upload dos XMLs de Entrada acima primeiro.")
        else:
            st.toast("Iniciando validação de Entradas...", icon="🛡️")
            # --- SUA LÓGICA AQUI ---

with c4:
    st.info("Valida sequência numérica e autorização das vendas.")
    if st.button("🔍 Verificar Autenticidade Saídas", type="primary", use_container_width=True):
        if not xml_saidas:
            st.error("⚠️ Faça o upload dos XMLs de Saída acima primeiro.")
        else:
            st.toast("Iniciando validação de Saídas...", icon="🛡️")
            # --- SUA LÓGICA AQUI ---

# Espaço
st.markdown("<br>", unsafe_allow_html=True)

# --- 6. ÁREA 3: RELATÓRIOS GERENCIAIS ---
st.markdown("### 📊 3. Relatórios Gerenciais")
c5, c6 = st.columns(2, gap="medium")

with c5:
    st.markdown("Resumo de CFOPs, alíquotas médias e créditos tomados.")
    if st.button("📈 Gerar Relatório Gerencial Entradas", use_container_width=True):
        st.toast("Gerando Dashboard de Compras...", icon="📊")
        # --- SUA LÓGICA AQUI ---

with c6:
    st.markdown("Curva ABC de produtos, clientes e impostos destacados.")
    if st.button("📈 Gerar Relatório Gerencial Saídas", use_container_width=True):
        st.toast("Gerando Dashboard de Vendas...", icon="📊")
        # --- SUA LÓGICA AQUI ---
