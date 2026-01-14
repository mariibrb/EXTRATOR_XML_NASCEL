import streamlit as st
import zipfile
import io
import os
import xml.etree.ElementTree as ET
import re

def get_xml_key(root, content_str):
    """Extrai a chave de acesso (44 dígitos) do XML."""
    ch_tag = root.find(".//chNFe") or root.find(".//chCTe") or root.find(".//chMDFe")
    if ch_tag is not None and ch_tag.text:
        return ch_tag.text

    inf_tags = [".//infNFe", ".//infCTe", ".//infMDFe", ".//infProc"]
    for tag in inf_tags:
        element = root.find(tag)
        if element is not None and 'Id' in element.attrib:
            key = re.sub(r'\D', '', element.attrib['Id'])
            if len(key) == 44:
                return key
    
    found = re.findall(r'\d{44}', content_str)
    if found:
        return found[0]
    return None

def identify_xml_info(content_bytes, client_cnpj):
    """Identifica tipo, fluxo (entrada/saída), série e chave."""
    client_cnpj = "".join(filter(str.isdigit, client_cnpj))
    try:
        content_str = content_bytes.decode('utf-8', errors='ignore')
        clean_content = content_str
        for ns in ["nfe", "cte", "mdfe"]:
            clean_content = clean_content.replace(f'xmlns="http://www.portalfiscal.inf.br/{ns}"', '')
        
        root = ET.fromstring(clean_content)
        
        doc_type = "Outros"
        tag_lower = content_str.lower()
        if '<infnfe' in tag_lower:
            doc_type = "NFC-e" if '<mod>65</mod>' in tag_lower else "NF-e"
        elif '<infcte' in tag_lower: doc_type = "CT-e"
        elif '<infmdfe' in tag_lower: doc_type = "MDF-e"
        elif '<evento' in tag_lower or '<infresevento' in tag_lower: doc_type = "Eventos"

        emit_cnpj = ""
        serie = "0"
        
        emit = root.find(".//emit/CNPJ")
        if emit is not None:
            emit_cnpj = "".join(filter(str.isdigit, emit.text))
            
        serie_tag = root.find(".//ide/serie")
        if serie_tag is not None:
            serie = serie_tag.text

        chave = get_xml_key(root, content_str)
        
        if client_cnpj and emit_cnpj == client_cnpj:
            pasta_final = f"EMITIDOS_CLIENTE/{doc_type}/Serie_{serie}"
        else:
            pasta_final = f"RECEBIDOS_TERCEIROS/{doc_type}"
            
        return pasta_final, chave
    except:
        return "NAO_IDENTIFICADOS", None

def add_to_dict(filepath, content, xml_files_dict, client_cnpj, processed_keys):
    """Valida duplicidade e organiza nas pastas por série."""
    simple_name = os.path.basename(filepath)
    if not simple_name or not simple_name.lower().endswith('.xml'):
        return

    subfolder, chave = identify_xml_info(content, client_cnpj)
    
    if chave:
        if chave in processed_keys:
            return
        processed_keys.add(chave)
        simple_name = f"{chave}.xml"

    full_path_in_zip = f"{subfolder}/{simple_name}"
    
    name_to_save = full_path_in_zip
    counter = 1
    while name_to_save in xml_files_dict:
        name_part, ext_part = os.path.splitext(simple_name)
        name_to_save = f"{subfolder}/{name_part}_{counter}{ext_part}"
        counter += 1
    
    xml_files_dict[name_to_save] = content

def process_recursively(file_name, file_bytes, xml_files_dict, client_cnpj, processed_keys):
    if file_name.lower().endswith('.zip'):
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                for info in z.infolist():
                    if info.is_dir(): continue
                    content = z.read(info.filename)
                    process_recursively(info.filename, content, xml_files_dict, client_cnpj, processed_keys)
        except:
            pass
    elif file_name.lower().endswith('.xml'):
        add_to_dict(file_name, file_bytes, xml_files_dict, client_cnpj, processed_keys)

# --- INTERFACE ---

st.set_page_config(page_title="Garimpeiro de XML v2.1", page_icon="⛏️", layout="wide")

st.title("⛏️ Garimpeiro de XML 💎")
st.subheader("Minerador inteligente com Barra de Progresso Real")

st.markdown("""
<div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; border: 1px solid #dcdde1;">
    <h4 style="margin-top:0;">🦊 Status do Garimpo</h4>
    Arraste sua pasta aberta ou ZIPs e acompanhe a barra de porcentagem abaixo!
</div>
""", unsafe_allow_html=True)

st.write("")

with st.sidebar:
    st.header("⚙️ Configurações")
    cnpj_input = st.text_input("CNPJ do Cliente (apenas números)", placeholder="Ex: 12345678000199")
    st.divider()
    st.info("🛡️ Anti-Duplicidade Ativa")
    st.info("📊 Separação por Série Ativa")

uploaded_files = st.file_uploader(
    "Selecione todos os arquivos da sua pasta (Ctrl+A) ou arraste a pasta aqui", 
    accept_multiple_files=True
)

if uploaded_files:
    if st.button("⛏️ INICIAR GARIMPO COM PORCENTAGEM", use_container_width=True):
        all_xml_data = {}
        processed_keys = set()
        
        total_files = len(uploaded_files)
        # Cria a barra de progresso com porcentagem
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, file in enumerate(uploaded_files):
            # Calcula a porcentagem
            percent_complete = int(((i + 1) / total_files) * 100)
            
            # Atualiza o texto de status e a barra
            status_text.markdown(f"⛏️ **Minerando:** {file.name} | **{i+1}/{total_files}** arquivos ({percent_complete}%)")
            progress_bar.progress((i + 1) / total_files)
            
            process_recursively(file.name, file.read(), all_xml_data, cnpj_input, processed_keys)

        status_text.empty() # Limpa o texto ao terminar

        if all_xml_data:
            st.balloons()
            st.success(f"✨ Garimpo Concluído! {len(all_xml_data)} XMLs únicos organizados.")
            
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for path, data in all_xml_data.items():
                    zf.writestr(path, data)
            
            resumo = {}
            for path in all_xml_data.keys():
                partes = path.split('/')
                cat = " - ".join([p.replace('_', ' ') for p in partes[:-1]])
                resumo[cat] = resumo.get(cat, 0) + 1
            
            st.write("### 📊 Inventário Final:")
            st.table(resumo)

            st.download_button(
                label="📥 BAIXAR MEU TESOURO (.ZIP)",
                data=zip_buffer.getvalue(),
                file_name="garimpo_xml_final.zip",
                mime="application/zip",
                use_container_width=True
            )
        else:
            st.error("💎 Ops! Não encontramos diamantes (XML) nessa mina.")

st.divider()
st.caption("🦊 Garimpeiro v2.1: Agora com barra de progresso em tempo real.")
