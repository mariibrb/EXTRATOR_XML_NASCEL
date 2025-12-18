import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import io
import os

st.set_page_config(page_title="Sentinela Fiscal v2.0", layout="wide")
st.title("🛡️ Sentinela Fiscal: Auditoria Inteligente")

# 1. CARREGAR REGRAS DO GITHUB (Sentinela_MIRÃO_Outubro2025.xlsx)
@st.cache_data
def carregar_regras_fixas():
    # Ajuste o nome do arquivo se necessário
    arquivo = "Sentinela_MIRÃO_Outubro2025.xlsx"
    if os.path.exists(arquivo):
        xls = pd.ExcelFile(arquivo)
        return {
            'tribut': pd.read_excel(xls, sheet_name='Bases Tribut'),
            'tes': pd.read_excel(xls, sheet_name='TES')
        }
    return None

regras = carregar_regras_fixas()

# 2. UPLOADS
col1, col2 = st.columns(2)
with col1:
    xmls = st.file_uploader("1. Arraste seus XMLs", accept_multiple_files=True, type='xml')
with col2:
    rel_autent = st.file_uploader("2. Suba o Relatório de Autenticidade (Extraído do Sistema)", type=['xlsx', 'csv'])

def auditoria_completa(row, df_autent, regras):
    # AO - STATUS
    match_status = df_autent[df_autent['Chave de Acesso'] == row['Chave_Acesso']]
    status = match_status.iloc[0]['Situação'] if not match_status.empty else "Não Conferido"
    
    # AP - Análise CST ICMS
    regra_ncm = regras['tribut'][regras['tribut']['NCM'] == row['NCM']]
    esperado_cst = str(regra_ncm.iloc[0]['CST']) if not regra_ncm.empty else "N/A"
    analise_cst = "Correto" if str(row['CST_ICMS']) == esperado_cst else f"Divergente (Esperado: {esperado_cst})"
    
    # AQ - CST x BC
    if row['CST_ICMS'] == "20" and row['pRedBC'] == 0:
        cst_bc = "Erro: CST 020 sem redução"
    elif row['CST_ICMS'] == "00" and abs(row['vBC'] - row['vProd']) > 0.05:
        cst_bc = "Erro: Base != Produto"
    else:
        cst_bc = "Correto"

    # AR - Alíquota ICMS (Motivo detalhado sem precisar de AS)
    alq_esperada = regra_ncm.iloc[0]['ALÍQUOTA ICMS'] if not regra_ncm.empty else 0
    analise_alq = "Correto"
    if row['UF_Emit'] != row['UF_Dest']:
        # Lógica simplificada de alíquota interestadual
        analise_alq = f"Validar Operação {row['UF_Emit']}->{row['UF_Dest']}"
    elif row['Alq_ICMS'] != alq_esperada:
        analise_alq = f"Divergente: {row['Alq_ICMS']}% | Esperado: {alq_esperada}%"

    # AV - Análise ST
    analise_st = "OK"
    if row['vBCST'] > 0 and row['vICMSST'] == 0:
        analise_st = "Divergente: Base ST sem valor de imposto"
    elif row['vBCST'] == 0 and row['CST_ICMS'] in ['10', '30', '60', '70']:
        analise_st = "Divergente: CST de ST sem Base de Cálculo"

    return {
        'AO_STATUS': status,
        'AP_Analise_CST': analise_cst,
        'AQ_CST_x_BC': cst_bc,
        'AR_Analise_Alq': analise_alq,
        'AV_Analise_ST_FCP': analise_st
    }

if xmls and rel_autent and regras:
    # Carregar autenticidade do usuário
    df_autent_user = pd.read_csv(rel_autent) if rel_autent.name.endswith('.csv') else pd.read_excel(rel_autent)
    
    lista_itens = []
    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    
    for arq in xmls:
        try:
            tree = ET.parse(arq)
            root = tree.getroot()
            
            # Extração Cabeçalho
            inf = root.find('.//nfe:infNFe', ns)
            chave = inf.attrib['Id'][3:]
            ide = root.find('.//nfe:ide', ns)
            emit = root.find('.//nfe:emit', ns)
            dest = root.find('.//nfe:dest', ns)
            
            for det in root.findall('.//nfe:det', ns):
                prod = det.find('nfe:prod', ns)
                imposto = det.find('nfe:imposto', ns)
                icms = imposto.find('.//nfe:ICMS', ns)[0]
                
                # Campos Base_XML (A-AN)
                item = {
                    'NF': ide.find('nfe:nNF', ns).text,
                    'Chave_Acesso': chave,
                    'UF_Emit': emit.find('.//nfe:UF', ns).text,
                    'UF_Dest': dest.find('.//nfe:UF', ns).text,
                    'NCM': prod.find('nfe:NCM', ns).text,
                    'CFOP': prod.find('nfe:CFOP', ns).text,
                    'vProd': float(prod.find('nfe:vProd', ns).text),
                    'CST_ICMS': icms.find('nfe:CST', ns).text if icms.find('nfe:CST', ns) is not None else "00",
                    'Alq_ICMS': float(icms.find('nfe:pICMS', ns).text) if icms.find('nfe:pICMS', ns) is not None else 0,
                    'vBC': float(icms.find('nfe:vBC', ns).text) if icms.find('nfe:vBC', ns) is not None else 0,
                    'pRedBC': float(icms.find('nfe:pRedBC', ns).text) if icms.find('nfe:pRedBC', ns) is not None else 0,
                    'vBCST': float(icms.find('nfe:vBCST', ns).text) if icms.find('nfe:vBCST', ns) is not None else 0,
                    'vICMSST': float(icms.find('nfe:vICMSST', ns).text) if icms.find('nfe:vICMSST', ns) is not None else 0,
                }
                
                # Aplicar Auditoria
                item.update(auditoria_completa(item, df_autent_user, regras))
                lista_itens.append(item)
        except:
            continue

    df_final = pd.DataFrame(lista_itens)
    st.success(f"✅ Auditoria Concluída: {len(df_final)} itens processados.")
    
    # Gerar Excel
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, sheet_name='Análise Sentinela', index=False)
        # Aba Autent zerada para o mês seguinte
        pd.DataFrame(columns=['Chave de Acesso', 'Situação']).to_excel(writer, sheet_name='Autent', index=False)

    st.download_button("📥 Baixar Planilha Sentinela Pronta", buffer, "Sentinela_Auditada.xlsx")
