import streamlit as st
import pandas as pd
import io

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Auditoria Fiscal Mirão",
    page_icon="🔎",
    layout="wide"
)

# ==============================================================================
# FUNÇÕES DE LÓGICA (BACKEND)
# ==============================================================================

@st.cache_data
def carregar_bases(arquivo):
    """
    Lê a planilha 'Bases Tribut' (Regras da Empresa).
    Mapeia as colunas A até I conforme a estrutura fixa definida.
    """
    try:
        # Lê colunas A até I (0 a 8) e força NCM como texto
        df = pd.read_excel(arquivo, usecols="A:I", dtype=str)
        
        # Renomeia as colunas pelo índice para garantir consistência
        # A=NCM, C=CST_Int, D=Aliq_Int, E=Reduc_Int, G=CST_Ext
        novas_colunas = [
            'NCM', 'Desc_Int', 'CST_Int', 'Aliq_Int', 'Reducao_Int',
            'Desc_Ext', 'CST_Ext', 'Aliq_Ext_Ref', 'Info_Extra'
        ]
        
        # Ajusta caso o arquivo tenha cabeçalhos ou não
        if len(df.columns) == 9:
            df.columns = novas_colunas
        else:
            st.error(f"O arquivo de bases deve ter exatamente colunas de A a I. Encontradas: {len(df.columns)}")
            return None
            
        # Tratamento de dados numéricos
        # Converte percentuais (ex: 41,67%) para float
        def limpar_percentual(val):
            if pd.isna(val): return 0.0
            val = str(val).replace('%', '').replace(',', '.')
            try:
                # Se for maior que 1 (ex: 41.67), divide por 100. Se for 0.4167, mantém.
                num = float(val)
                return num / 100 if num > 1 else num
            except:
                return 0.0

        df['Reducao_Int'] = df['Reducao_Int'].apply(limpar_percentual)
        df['Aliq_Int'] = df['Aliq_Int'].apply(limpar_percentual)
        
        # Limpeza de NCM e CST (remove pontos e espaços)
        df['NCM'] = df['NCM'].str.replace('.', '', regex=False).str.strip()
        df['CST_Int'] = df['CST_Int'].str.replace('.0', '', regex=False).str.strip()
        df['CST_Ext'] = df['CST_Ext'].str.replace('.0', '', regex=False).str.strip()
        
        return df
    except Exception as e:
        st.error(f"Erro ao processar arquivo de bases: {e}")
        return None

def auditar_icms(df_notas, df_regras):
    """
    Motor de Cálculo: Cruza notas com regras e audita CST e Valores.
    """
    # 1. Preparação das Notas
    df_notas.columns = df_notas.columns.str.strip().str.upper() # Padroniza caixa alta
    
    # Tenta identificar colunas chave automaticamente
    col_ncm = next((c for c in df_notas.columns if 'NCM' in c), 'NCM')
    col_cfop = next((c for c in df_notas.columns if 'CFOP' in c), 'CFOP')
    col_cst = next((c for c in df_notas.columns if 'CST' in c), 'CST')
    col_val_prod = next((c for c in df_notas.columns if 'VALOR' in c and 'PROD' in c), None) # Ex: Valor Produto
    col_val_icms = next((c for c in df_notas.columns if 'VALOR' in c and 'ICMS' in c), None) # Ex: Valor ICMS
    
    if not col_val_prod or not col_val_icms:
        return pd.DataFrame(), "Erro: Não encontrei colunas de 'Valor Produto' ou 'Valor ICMS' no arquivo."

    # Garante NCM como texto limpo
    df_notas[col_ncm] = df_notas[col_ncm].astype(str).str.replace('.', '', regex=False).str.strip()
    
    # 2. Cruzamento (Merge)
    df_final = pd.merge(df_notas, df_regras, left_on=col_ncm, right_on='NCM', how='left')
    
    resultados = []

    # 3. Iteração Linha a Linha (Auditoria)
    for index, row in df_final.iterrows():
        status = "OK"
        detalhe_erro = ""
        icms_calculado = 0.0
        
        # Variáveis da linha
        ncm_nota = row[col_ncm]
        cfop_nota = str(row[col_cfop])
        cst_nota = str(row[col_cst]).replace('.0', '').strip()
        val_prod = float(str(row[col_val_prod]).replace(',', '.')) if pd.notna(row[col_val_prod]) else 0.0
        val_icms_nota = float(str(row[col_val_icms]).replace(',', '.')) if pd.notna(row[col_val_icms]) else 0.0
        
        # Regras vindas da base
        cst_regra_int = str(row['CST_Int']) if pd.notna(row['CST_Int']) else None
        cst_regra_ext = str(row['CST_Ext']) if pd.notna(row['CST_Ext']) else None
        
        # --- LÓGICA DE DECISÃO (O CÉREBRO) ---
        
        if pd.isna(cst_regra_int):
            status = "⚠️ NCM SEM REGRA"
            detalhe_erro = "Cadastrar na aba Bases"
        
        else:
            # Define se é Interna (CFOP 5...) ou Interestadual (CFOP 6...)
            eh_interna = cfop_nota.startswith('5')
            
            if eh_interna:
                # === CENÁRIO INTERNO ===
                cst_esperado = cst_regra_int
                reducao = float(row['Reducao_Int']) if pd.notna(row['Reducao_Int']) else 1.0
                
                # Se a alíquota vier da base, usa ela. Senão, usa 18% padrão.
                aliquota = float(row['Aliq_Int']) if pd.notna(row['Aliq_Int']) and row['Aliq_Int'] > 0 else 0.18
                
                # 1. Valida CST
                if cst_nota != cst_esperado:
                    status = "❌ ERRO CST"
                    detalhe_erro = f"Nota: {cst_nota} | Regra: {cst_esperado} (Int)"
                
                # 2. Calcula ICMS (Apenas para tributados)
                if cst_esperado in ['00', '20', '90']:
                    icms_calculado = val_prod * reducao * aliquota
                    
            else:
                # === CENÁRIO INTERESTADUAL ===
                cst_esperado = cst_regra_ext
                # Geralmente não tem redução interestadual, base 100%
                reducao = 1.0 
                aliquota = 0.12 # Padrão Interestadual (ajustar se necessário 4% ou 7%)
                
                # 1. Valida CST
                if cst_nota != cst_esperado:
                    status = "❌ ERRO CST"
                    detalhe_erro = f"Nota: {cst_nota} | Regra: {cst_esperado} (Ext)"
                
                # 2. Calcula ICMS
                if cst_esperado in ['00', '20', '90']:
                    icms_calculado = val_prod * reducao * aliquota

            # --- VALIDAÇÃO FINAL DE VALORES ---
            # Se o CST estiver OK, verificamos o valor financeiro
            if "ERRO CST" not in status and "NCM SEM REGRA" not in status:
                # Verifica isentos
                if cst_esperado in ['40', '41', '50', '51', '60']:
                    if val_icms_nota > 0:
                        status = "❌ ERRO VALOR"
                        detalhe_erro = "Produto Isento/Diferido com imposto cobrado"
                else:
                    # Verifica valores (tolerância de 5 centavos)
                    diferenca = abs(val_icms_nota - icms_calculado)
                    if diferenca > 0.05:
                        status = "❌ ERRO VALOR"
                        detalhe_erro = f"Dif: R$ {diferenca:.2f} (Calc: {icms_calculado:.2f})"

        resultados.append({
            'NCM': ncm_nota,
            'CFOP': cfop_nota,
            'CST_Nota': cst_nota,
            'CST_Esperado': cst_esperado if pd.notna(cst_regra_int) else '',
            'Vl_Produto': val_prod,
            'ICMS_Nota': val_icms_nota,
            'ICMS_Correto': round(icms_calculado, 2),
            'STATUS': status,
            'Detalhe': detalhe_erro
        })
        
    return pd.DataFrame(resultados), "Sucesso"

# ==============================================================================
# INTERFACE VISUAL (FRONTEND)
# ==============================================================================

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2910/2910768.png", width=50)
    st.title("Configurações")
    st.markdown("---")
    
    # 1. UPLOAD DA BASE DE REGRAS
    st.subheader("1. Base de Regras")
    st.caption("Upload do Excel com colunas A até I (NCM, CST, Reduções...)")
    
    file_bases = st.file_uploader("Carregar 'Bases Tribut.xlsx'", type=["xlsx"], key="base_regra")
    
    df_regras_carregada = None
    
    if file_bases:
        df_regras_carregada = carregar_bases(file_bases)
        if df_regras_carregada is not None:
            st.success("✅ Bases Carregadas com Sucesso!")
            # Mostra prévia pequena para confirmação
            with st.expander("Ver prévia das regras"):
                st.dataframe(df_regras_carregada.head(3), hide_index=True)
    else:
        st.error("⚠️ Pendente: Carregue a tabela de regras.")

    st.markdown("---")

    # 2. UPLOAD DA TIPI (Apenas armazenamento)
    st.subheader("2. Tabela TIPI")
    st.caption("Upload do arquivo oficial do Governo (Opcional para consulta).")
    file_tipi = st.file_uploader("Carregar TIPI.xlsx", type=["xlsx"], key="tipi")
    
    if file_tipi:
        st.info("✅ TIPI armazenada na memória.")

# --- ÁREA PRINCIPAL ---

st.title("Auditoria Fiscal Inteligente - ICMS")
st.markdown("""
Esta ferramenta cruza o **Relatório do Sistema** com a **Base de Regras** carregada ao lado.
Ela identifica automaticamente se a operação é **Interna** ou **Interestadual** pelo CFOP.
""")

st.divider()

# ÁREA DE UPLOAD DO RELATÓRIO DO DIA A DIA
col_upload, col_btn = st.columns([3, 1])

with col_upload:
    uploaded_file = st.file_uploader("📂 **Carregue o Relatório de Notas (Excel ou CSV)**", type=["csv", "xlsx"])

# BOTÃO DE AÇÃO
if uploaded_file and df_regras_carregada is not None:
    
    # Lê o arquivo do usuário
    try:
        if uploaded_file.name.endswith('.csv'):
            # Tenta ler CSV (padrão Brasil ; ou ,)
            try:
                df_notas_input = pd.read_csv(uploaded_file, sep=';', decimal=',')
            except:
                uploaded_file.seek(0)
                df_notas_input = pd.read_csv(uploaded_file, sep=',', decimal='.')
        else:
            df_notas_input = pd.read_excel(uploaded_file)
            
        st.write(f"Arquivo carregado: **{uploaded_file.name}** ({len(df_notas_input)} linhas)")
        
        st.markdown("###")
        if st.button("🚀 EXECUTAR AUDITORIA AGORA", type="primary", use_container_width=True):
            
            with st.spinner("Analisando NCM por NCM, validando CSTs e recalculando impostos..."):
                # CHAMA O MOTOR DE AUDITORIA
                df_resultado, msg = auditar_icms(df_notas_input, df_regras_carregada)
                
                if not df_resultado.empty:
                    # MÉTRICAS
                    total = len(df_resultado)
                    erros = df_resultado[df_resultado['STATUS'] != 'OK'].shape[0]
                    acuracia = ((total - erros) / total) * 100
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Total Analisado", total)
                    c2.metric("Inconsistências", erros, delta=-erros, delta_color="inverse")
                    c3.metric("Acurácia Fiscal", f"{acuracia:.1f}%")
                    
                    st.divider()
                    
                    # TABELA COLORIDA
                    st.subheader("📋 Detalhamento da Análise")
                    
                    def colorir_linha(val):
                        color = '#d4edda' if val == 'OK' else '#f8d7da' # Verde ou Vermelho claro
                        return f'background-color: {color}'
                    
                    st.dataframe(
                        df_resultado.style.applymap(colorir_linha, subset=['STATUS']),
                        use_container_width=True,
                        height=500
                    )
                    
                    # DOWNLOAD
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        df_resultado.to_excel(writer, index=False, sheet_name='Auditoria_ICMS')
                        
                    st.download_button(
                        label="📥 BAIXAR RELATÓRIO COMPLETO (.XLSX)",
                        data=buffer,
                        file_name="Resultado_Auditoria_ICMS.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="secondary"
                    )
                else:
                    st.error(msg)
                    
    except Exception as e:
        st.error(f"Erro ao ler o arquivo: {e}")

elif uploaded_file and df_regras_carregada is None:
    st.warning("👈 Por favor, carregue a **Base de Regras** na barra lateral esquerda para habilitar a auditoria.")

else:
    st.info("Aguardando uploads...")
