import streamlit as st
import zipfile
import io
import os
import xml.etree.ElementTree as ET
import re
import pandas as pd

# --- FUNÇÕES DE IDENTIFICAÇÃO ---
def get_xml_key(root, content_str):
    ch_tag = root.find(".//chNFe") or root.find(".//chCTe") or root.find(".//chMDFe")
    if ch_tag is not None and ch_tag.text: return ch_tag.text
    inf_tags = [".//infNFe", ".//infCTe", ".//infMDFe", ".//infProc"]
    for tag in inf_tags:
        element = root.find(tag)
        if element is not None and 'Id' in element.attrib:
            key = re.sub(r'\D', '', element.attrib['Id'])
            if len(key) == 44: return key
    found = re.findall(r'\d{44}', content_str)
    if found: return found[0]
    return None

def identify_xml_info(content_bytes, client_cnpj):
    client_cnpj = "".join(filter(str.isdigit, client_cnpj))
    try:
        content_str = content_bytes.decode('utf-8', errors='ignore')
        clean_content = content_str
        for ns in ["nfe", "cte", "mdfe"]:
            clean_content = clean_content.replace(f'xmlns="http://www.portalfiscal.inf.br/{ns}"', '')
        root = ET.fromstring(clean_content)
        
        doc_type = "Outros"
        tag_lower = content_str.lower()
        if '<infnfe' in tag_lower: doc_type = "NFC-e" if '<mod>65</mod>' in tag_lower else "NF-e"
        elif '<infcte' in tag_lower: doc_type = "CT-e"
        elif '<infmdfe' in tag_lower: doc_type = "MDF-e"
        elif '<evento' in tag_lower or '<infresevento' in tag_lower: doc_type = "Eventos"
        
        emit_cnpj = ""; serie = "0"; numero = None
        emit = root.find(".//emit/CNPJ")
        if emit is not None: emit_cnpj = "".join(filter(str.isdigit, emit.text))
        
        serie_tag = root.find(".//ide/serie")
        if serie_tag is not None: serie = serie_tag.text
        
        nNF_tag = root.find(".//ide/nNF") or root.find(".//ide/nCT") or root.find(".//ide/nMDF")
        if nNF_tag is not None: numero = int(nNF_tag.text)

        chave = get_xml_key(root, content_str)
        is_propria = (client_cnpj and emit_cnpj == client_cnpj)
        
        if is_propria:
            pasta_final = f"EMITIDOS_CLIENTE/{doc_type}/Serie_{serie}"
        else:
            pasta_final = f"RECEBIDOS_TERCEIROS/{doc_type}"
            
        return pasta_final, chave, is_propria, serie, numero
    except:
        return "NAO_IDENTIFICADOS", None, False, "0", None

def add_to_dict(filepath, content, xml_files_dict, client_cnpj, processed_keys, sequencias_proprias):
    simple_name = os.path.basename(filepath)
    if not simple_name or not simple_name.lower().endswith('.xml'): return
    
    subfolder, chave, is_propria, serie, numero = identify_xml_info(content, client_cnpj)
    
    if chave:
        if chave in processed_keys: return
        processed_keys.add(chave)
        simple_name = f"{chave}.xml"
        
        if is_propria and numero:
            if serie not in sequencias_proprias: sequencias_proprias[serie] = set()
            sequencias_proprias[serie].add(numero)

    full_path_in_zip = f"{subfolder}/{simple_name}"
    name_to_save = full_path_in_zip
    counter = 1
    while name_to_save in xml_files_dict:
        name_part, ext_part = os.path.splitext(simple_name)
        name_to_save = f"{subfolder}/{name_part}_{counter}{ext_part}"
        counter += 1
    xml_files_dict[name_to_save] = content

def process_recursively(file_name, file_bytes, xml_files_dict, client_cnpj, processed_keys, sequencias_proprias):
    if file_name.lower().endswith('.zip'):
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                for info in z.infolist():
                    if info.is_dir(): continue
                    content = z.read(info.filename)
                    process_recursively(info.filename, content, xml_files_dict, client_cnpj, processed_keys, sequencias_proprias)
        except: pass
    elif file_name.lower().endswith('.xml'):
        add_to_dict(file_name, file_bytes, xml_files_dict, client_cnpj, processed_keys, sequencias_proprias)

# --- INTERFACE ---
st.set_page_config(page_title="Garimpeiro de XML v3.1", page_icon="⛏️", layout="wide")

st.title("⛏️ Garimpeiro de XML 💎")

with st.sidebar:
    st.header("⚙️ Configurações")
    cnpj_input = st.text_input("CNPJ do Cliente (Apenas números)", placeholder="Ex: 12345678000199")
    st.divider()
    st.info("📊 Inventário Completo + Relatório de Faltantes")

st.markdown("### 📥 1. Carregar Arquivos")
status_upload = st.empty()

uploaded_files = st.file_uploader("Solte a pasta ou arquivos aqui", accept_multiple_files=True, label_visibility="collapsed")

if uploaded_files:
    total = len(uploaded_files)
    status_upload.warning(f"⏳ Aguardando leitura de {total} itens pelo navegador...")

    if st.button("🚀 INICIAR GARIMPO COMPLETO", use_container_width=True):
        status_upload.empty()
        all_xml_data = {}
        processed_keys = set()
        sequencias_proprias = {}

        # Interface de progresso total
        with st.container(border=True):
            st.write("### 📈 Progresso Total da Mineração")
            barra_geral = st.progress(0)
            c1, c2, c3 = st.columns(3)
            metrica_perc = c1.empty()
            metrica_qtd = c2.empty()
            metrica_rest = c3.empty()
            txt_file = st.empty()

        for i, file in enumerate(uploaded_files):
            process_recursively(file.name, file.read(), all_xml_data, cnpj_input, processed_keys, sequencias_proprias)
            prog = (i + 1) / total
            barra_geral.progress(prog)
            metrica_perc.metric("Status", f"{int(prog * 100)}%")
            metrica_qtd.metric("Processados", f"{i+1} de {total}")
            metrica_rest.metric("Faltam", total - (i+1))
            txt_file.caption(f"⛏️ Lendo: {file.name}")

        txt_file.empty()
        st.balloons()

        # --- EXIBIÇÃO DOS RESULTADOS ---
        st.success(f"✨ Garimpo Finalizado! {len(all_xml_data)} XMLs únicos organizados.")
        
        # 1. Tabela Detalhada (O que foi encontrado)
        st.write("### 📊 Inventário do Tesouro (Tudo o que foi encontrado)")
        resumo = {}
        for path in all_xml_data.keys():
            # Limpa o nome da pasta para exibição
            cat = " - ".join(path.split('/')[:-1]).replace('_', ' ')
            resumo[cat] = resumo.get(cat, 0) + 1
        
        # Transforma o dicionário em uma lista bonita para a tabela
        df_resumo = pd.DataFrame(list(resumo.items()), columns=['Categoria / Série', 'Quantidade'])
        st.table(df_resumo)

        # 2. Relatório de Faltantes
        st.divider()
        st.write("### ⚠️ Notas de Emissão Própria Faltantes (Buracos na Sequência)")
        faltantes_data = []
        if sequencias_proprias:
            for serie, numeros in sequencias_proprias.items():
                if numeros:
                    min_n = min(numeros)
                    max_n = max(numeros)
                    sequencia_completa = set(range(min_n, max_n + 1))
                    faltantes = sorted(list(sequencia_completa - numeros))
                    for f in faltantes:
                        faltantes_data.append({"Série": serie, "Número Faltante": f})
        
        if faltantes_data:
            df_faltantes = pd.DataFrame(faltantes_data)
            st.dataframe(df_faltantes, use_container_width=True)
            csv_faltantes = df_faltantes.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Baixar Lista de Faltantes (CSV)", csv_faltantes, "faltantes.csv", "text/csv")
        else:
            st.info("✅ Nenhuma quebra de sequência detectada nas notas do cliente.")

        # Gerar ZIP Final
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for path, data in all_xml_data.items():
                zf.writestr(path, data)
            if faltantes_data:
                zf.writestr("RELATORIOS/notas_faltantes.csv", pd.DataFrame(faltantes_data).to_csv(index=False))

        st.download_button(
            label="📥 BAIXAR TUDO ORGANIZADO (.ZIP)",
            data=zip_buffer.getvalue(),
            file_name="garimpo_completo.zip",
            mime="application/zip",
            use_container_width=True
        )

st.divider()
st.caption("FoxHelper v3.1: O Garimpeiro que não esquece nada.")
