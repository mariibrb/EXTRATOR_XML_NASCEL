import streamlit as st
import zipfile
import io
import os

def identify_xml_type(content_bytes):
    """
    Analisa o conteúdo do XML para identificar o tipo de documento.
    """
    try:
        content = content_bytes.decode('utf-8', errors='ignore').lower()
        if '<infnfe' in content:
            if '<mod>65</mod>' in content:
                return "NFC-e"
            return "NF-e"
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
    """
    Adiciona ao dicionário com triagem de tipo e evita duplicatas.
    """
    simple_name = os.path.basename(filepath)
    if not simple_name or not simple_name.lower().endswith('.xml'):
        return

    doc_type = identify_xml_type(content)
    full_path_in_zip = f"{doc_type}/{simple_name}"
    
    # Se o nome já existir na mesma categoria, renomeia com sufixo
    name_to_save = full_path_in_zip
    counter = 1
    while name_to_save in xml_files_dict:
        name_part, ext_part = os.path.splitext(simple_name)
        name_to_save = f"{doc_type}/{name_part}_{counter}{ext_part}"
        counter += 1
    
    xml_files_dict[name_to_save] = content

def process_anything(file_name, file_bytes, xml_files_dict):
    """
    A função mestre: decide se abre como ZIP ou se guarda como XML.
    Funciona para arquivos soltos ou vindos de dentro de um ZIP.
    """
    # 1. Se for um ZIP (ou arquivo que parece ZIP), tentamos abrir
    if file_name.lower().endswith('.zip'):
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                for internal_file in z.infolist():
                    if internal_file.is_dir():
                        continue
                    # Extrai o conteúdo e processa de novo (recursividade para ZIP dentro de ZIP)
                    internal_content = z.read(internal_file.filename)
                    process_anything(internal_file.filename, internal_content, xml_files_dict)
        except zipfile.BadZipFile:
            pass # Ignora se o arquivo .zip estiver corrompido
            
    # 2. Se for um XML
    elif file_name.lower().endswith('.xml'):
        add_to_dict(file_name, file_bytes, xml_files_dict)

# --- INTERFACE ---

st.set_page_config(page_title="Extrator Pro XML", page_icon="📦", layout="wide")

st.title("📦 Extrator Pro: XML, ZIP e Pastas")
st.markdown("""
Jogue aqui qualquer mistura de arquivos. O sistema vai varrer **todas as camadas** de pastas e arquivos compactados para encontrar seus XMLs e separá-los por categoria.
""")

uploaded_files = st.file_uploader(
    "Arraste Pastas, ZIPs ou arquivos soltos", 
    accept_multiple_files=True
)

if uploaded_files:
    if st.button("🔍 Iniciar Varredura Profunda"):
        all_xmls = {}
        
        with st.spinner("Garimpando arquivos..."):
            for uploaded_file in uploaded_files:
                # O segredo: processar cada arquivo individualmente
                f_bytes = uploaded_file.read()
                f_name = uploaded_file.name
                process_anything(f_name, f_bytes, all_xmls)
        
        if all_xmls:
            st.success(f"✅ Sucesso! Encontramos {len(all_xmls)} XMLs.")
            
            # Criar o ZIP de saída
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as final_zip:
                for path, data in all_xmls.items():
                    final_zip.writestr(path, data)
            
            # Resumo visual
            cols = st.columns(4)
            resumo = {}
            for p in all_xmls.keys():
                cat = p.split('/')[0]
                resumo[cat] = resumo.get(cat, 0) + 1
            
            for i, (cat, count) in enumerate(resumo.items()):
                cols[i % 4].metric(cat, f"{count} un")

            st.download_button(
                label="📥 Baixar Tudo Organizado (.ZIP)",
                data=zip_buffer.getvalue(),
                file_name="xmls_organizados.zip",
                mime="application/zip",
                use_container_width=True
            )
        else:
            st.error("Nenhum XML foi encontrado. Verifique se os arquivos são válidos.")
