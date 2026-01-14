import streamlit as st
import zipfile
import io
import os

def identify_xml_type(content_bytes):
    """Analisa o conteúdo do XML para identificar o tipo de documento fiscal."""
    try:
        content = content_bytes.decode('utf-8', errors='ignore').lower()
        if '<infnfe' in content:
            return "NFC-e" if '<mod>65</mod>' in content else "NF-e"
        elif '<infcte' in content: 
            return "CT-e"
        elif '<infmdfe' in content: 
            return "MDF-e"
        elif '<infresevento' in content or '<evento' in content: 
            return "Eventos"
        elif '<procnfe' in content: 
            return "NF-e"
        elif '<proccte' in content: 
            return "CT-e"
        else: 
            return "Outros_XMLs"
    except:
        return "Nao_Identificados"

def add_to_dict(filepath, content, xml_files_dict):
    """Organiza o arquivo na pasta correta e evita nomes duplicados."""
    simple_name = os.path.basename(filepath)
    if not simple_name or not simple_name.lower().endswith('.xml'):
        return

    doc_type = identify_xml_type(content)
    full_path_in_zip = f"{doc_type}/{simple_name}"
    
    name_to_save = full_path_in_zip
    counter = 1
    while name_to_save in xml_files_dict:
        name_part, ext_part = os.path.splitext(simple_name)
        name_to_save = f"{doc_type}/{name_part}_{counter}{ext_part}"
        counter += 1
    
    xml_files_dict[name_to_save] = content

def process_recursively(file_name, file_bytes, xml_files_dict):
    """Mergulha em ZIPs e processa arquivos XML soltos de pastas abertas."""
    if file_name.lower().endswith('.zip'):
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                for internal_info in z.infolist():
                    if internal_info.is_dir(): 
                        continue
                    internal_content = z.read(internal_info.filename)
                    process_recursively(internal_info.filename, internal_content, xml_files_dict)
        except:
            pass
    elif file_name.lower().endswith('.xml'):
        add_to_dict(file_name, file_bytes, xml_files_dict)

# --- INTERFACE ---

st.set_page_config(page_title="Extrator Total de XML", page_icon="📂", layout="wide")

st.title("📂 Extrator Fiscal: Pastas Abertas e ZIPs")

st.markdown("""
### 🚀 Como usar:
1. Abra a pasta no seu computador.
2. Selecione tudo (**Ctrl + A**).
3. **Arraste e solte** no campo abaixo. 
O sistema vai ignorar o que não é XML, abrir os ZIPs internos e organizar tudo por tipo.
""")

uploaded_files = st.file_uploader(
    "Arraste aqui seus arquivos (ZIPs ou XMLs soltos de pastas)", 
    accept_multiple_files=True
)

if uploaded_files:
    if st.button("📥 PROCESSAR E ORGANIZAR TUDO"):
        all_xml_data = {}
        progress_bar = st.progress(0)
        status = st.empty()
        
        total = len(uploaded_files)
        for i, file in enumerate(uploaded_files):
            status.text(f"Processando: {file.name}")
            content = file.read()
            process_recursively(file.name, content, all_xml_data)
            progress_bar.progress((i + 1) / total)

        status.empty()

        if all_xml_data:
            st.success(f"✅ Concluído! Encontramos {len(all_xml_data)} XMLs.")
            
            # Criar o ZIP final organizado
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z_final:
                for path, data in all_xml_data.items():
                    z_final.writestr(path, data)
            
            # Resumo por categorias
            resumo = {}
            for path in all_xml_data.keys():
                cat = path.split('/')[0]
                resumo[cat] = resumo.get(cat, 0) + 1
            
            st.write("### 📊 Resultado da Organização:")
            cols = st.columns(len(resumo))
            for i, (cat, qtd) in enumerate(resumo.items()):
                cols[i].metric(cat, f"{qtd} un")

            st.download_button(
                label="📦 BAIXAR ZIP ORGANIZADO",
                data=zip_buffer.getvalue(),
                file_name="xmls_organizados.zip",
                mime="application/zip",
                use_container_width=True
            )
        else:
            st.error("Nenhum arquivo XML válido foi encontrado.")

st.divider()
st.caption("Desenvolvido para extração fiscal recursiva.")
