import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import io
import os

st.set_page_config(page_title="Sentinela Fiscal v2.0", layout="wide")
st.title("🛡️ Sentinela Fiscal: Auditoria Inteligente")

# 1. CARREGAR REGRAS DO GITHUB
@st.cache_data
def carregar_regras_fixas():
    arquivo = "Sentinela_MIRÃO_Outubro2025.xlsx"
    if os.path.exists(arquivo):
        try:
            xls = pd.ExcelFile(arquivo)
            return {
                'tribut': pd.read_excel(xls, sheet_name='Bases Tribut'),
                'tes': pd.read_excel(xls, sheet_name='TES')
            }
        except Exception as e:
            st.error(f"Erro ao ler abas da planilha mestre: {e}")
    return None

regras = carregar_regras_fixas()

# 2. UPLOADS
col1, col2 = st.columns(2)
with col1:
    xmls_files = st.file_uploader("1. Arraste todos os XMLs aqui", accept_multiple_files=True, type=['xml', 'XML'])
with col2:
    rel_autent = st.file_uploader("2. Suba o Relatório de Autenticidade", type=['xlsx', 'csv'])

# Inicializamos df_final como None para evitar o NameError
df_final = None

if xmls_files and rel_autent and regras:
    # Carregar autenticidade do usuário
    try:
        if rel_autent.name.endswith('.csv'):
            df_autent_user = pd.read_csv(rel_autent)
        else:
            df_autent_user = pd.read_excel(rel_autent)
    except Exception as e:
        st.error(f"Erro ao carregar relatório de autenticidade: {e}")
        st.stop()

    lista_itens = []
    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    
    progresso = st.progress(0)
    
    for i, arq in enumerate(xmls_files):
        try:
            tree = ET.parse(arq)
            root = tree.getroot()
            
            # Extração Cabeçalho
            inf = root.find('.//nfe:infNFe', ns)
            chave = inf.attrib['Id'][3:] if inf is not None else ""
            ide = root.find('.//nfe:ide', ns)
            emit = root.find('.//nfe:emit', ns)
            dest = root.find('.//nfe:dest', ns)
            
            for det in root.findall('.//nfe:det', ns):
                prod = det.find('nfe:prod', ns)
                imposto = det.find('nfe:imposto', ns)
                
                # Coleta básica para a Base_XML
                item = {
                    'Número NF': ide.find('nfe:nNF', ns).text if ide is not None else "",
                    'Chave de Acesso': chave,
                    'UF Emit': emit.find('.//nfe:UF', ns).text if emit is not None else "",
                    'UF Dest': dest.find('.//nfe:UF', ns).text if dest is not None else "",
                    'NCM': prod.find('nfe:NCM', ns).text if prod is not None else "",
                    'CFOP': prod.find('nfe:CFOP', ns).text if prod is not None else "",
                    'vProd': float(prod.find('nfe:vProd', ns).text) if prod is not None else 0.0,
                }
                
                # --- AQUI VOCÊ PODE ADICIONAR AS LÓGICAS AO-AX ---
                item['AO_STATUS'] = "Pendente" # Exemplo
                
                lista_itens.append(item)
        except Exception:
            continue
        
        progresso.progress((i + 1) / len(xmls_files))

    if lista_itens:
        df_final = pd.DataFrame(lista_itens)

# 3. GERAÇÃO DO EXCEL (Só acontece se df_final foi criado)
if df_final is not None and not df_final.empty:
    st.success(f"✅ Auditoria Concluída: {len(df_final)} itens processados.")
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, sheet_name='Análise Sentinela', index=False)
        # Aba Autent zerada para o usuário
        pd.DataFrame(columns=['Chave de Acesso', 'Situação']).to_excel(writer, sheet_name='Autent', index=False)

    st.download_button(
        label="📥 Baixar Planilha Sentinela Pronta",
        data=buffer.getvalue(),
        file_name="Sentinela_Auditada.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
