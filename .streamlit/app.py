import streamlit as st
import zipfile
import io
import os

def extract_xml_recursive(data, xml_files_dict):
    """
    Lê bytes de um arquivo. Se for um ZIP, abre e olha dentro.
    Se encontrar outro ZIP dentro, mergulha recursivamente.
    Se encontrar XML, salva no dicionário.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for file_info in z.infolist():
                # Ignora pastas vazias dentro do ZIP
                if file_info.is_dir():
                    continue
                
                filename = file_info.filename
                # Se for um ZIP dentro do ZIP
                if filename.lower().endswith('.zip'):
                    nested_zip_bytes = z.read(filename)
                    extract_xml_recursive(nested_zip_bytes, xml_files_dict)
                
                # Se for um XML dentro do ZIP
                elif filename.lower().endswith('.xml'):
                    content = z.read(filename)
                    simple_name = os.path.basename(filename)
                    if simple_name:
                        # Se o nome já existir, anexa um contador para não sobrescrever
                        base_name = simple_name
                        counter = 1
                        while simple_name in xml_files_dict:
                            name_part, ext_part = os.path.splitext(base_name)
                            simple_name = f"{name_part}_{counter}{ext_part}"
                            counter += 1
                        xml_files_dict[simple_name] = content
    except zipfile.BadZipFile:
        # Se não for um ZIP válido, apenas ignora
        pass

# Configuração da Página
st.set_page_config(page_title="Extrator Total XML", page_icon="⚡")

st.title("⚡ Extrator Total de XML")
st.markdown("""
Arraste para cá:
1. **Arquivos ZIP** (mesmo que tenham pastas ou outros ZIPs dentro).
2. **Pastas inteiras** do seu computador.
3. **Arquivos XML** avulsos.
""")

# Componente de Upload
uploaded_files = st.file_uploader(
    "Solte seus arquivos ou pastas aqui", 
    accept_multiple_files=True
)

if uploaded_files:
    if st.button("🚀 Extrair tudo para um único ZIP"):
        all_xmls = {} # {nome_do_arquivo: conteudo_em_bytes}
        
        with st.spinner("Processando..."):
            for uploaded_file in uploaded_files:
                file_bytes = uploaded_file.read()
                fname = uploaded_file.name.lower()
                
                # Caso 1: O arquivo enviado é um ZIP
                if fname.endswith('.zip'):
                    extract_xml_recursive(file_bytes, all_xmls)
                
                # Caso 2: O arquivo enviado é um XML solto (ou veio de uma pasta arrastada)
                elif fname.endswith('.xml'):
                    simple_name = os.path.basename(uploaded_file.name)
                    # Lógica para evitar nomes duplicados
                    name_to_save = simple_name
                    c = 1
                    while name_to_save in all_xmls:
                        n, e = os.path.splitext(simple_name)
                        name_to_save = f"{n}_{c}{e}"
                        c += 1
                    all_xmls[name_to_save] = file_bytes

        if all_xmls:
            st.success(f"Encontrados {len(all_xmls)} arquivos XML!")
            
            # Criar ZIP final
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as new_zip:
                for name, content in all_xmls.items():
                    new_zip.writestr(name, content)
            
            st.download_button(
                label="📥 Baixar ZIP com todos os XMLs",
                data=zip_buffer.getvalue(),
                file_name="xmls_extraidos.zip",
                mime="application/zip"
            )
        else:
            st.error("Nenhum XML encontrado nos arquivos fornecidos.")

st.divider()
st.info("Dica: Ao arrastar uma pasta, o navegador enviará todos os arquivos contidos nela individualmente para o Streamlit.")
