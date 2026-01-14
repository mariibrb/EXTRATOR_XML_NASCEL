import streamlit as st
import zipfile
import io
import os

def identify_xml_type(content_bytes):
    """
    Lê o interior do XML para saber se é NF-e, CT-e, etc.
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
    Organiza no dicionário com a pasta correta e evita duplicados.
    """
    simple_name = os.path.basename(filepath)
    if not simple_name or not simple_name.lower().endswith('.xml'):
        return

    doc_type = identify_xml_type(content)
    # Define o caminho: Pasta_Tipo/Nome_do_Arquivo.xml
    full_path_in_zip = f"{doc_type}/{simple_name}"
    
    # Se houver arquivo com mesmo nome, adiciona um contador
    name_to_save = full_path_in_zip
    counter = 1
    while name_to_save in xml_files_dict:
        name_part, ext_part = os.path.splitext(simple_name)
        name_to_save = f"{doc_type}/{name_part}_{counter}{ext_part}"
        counter += 1
    
    xml_files_dict[name_to_save] = content

def process_recursively(file_name, file_bytes, xml_files_dict):
    """
    FUNÇÃO CHAVE: Abre ZIPs dentro de ZIPs e processa arquivos soltos.
    """
    # Se for um ZIP, precisamos abrir e olhar tudo lá dentro
    if file_name.lower().endswith('.zip'):
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                for internal_info in z.infolist():
                    if internal_info.is_dir():
                        continue
                    
                    # Lê o conteúdo do arquivo interno
                    internal_content = z.read(internal_info.filename)
                    internal_name = internal_info.filename
                    
                    # RECURSIVIDADE: Se o arquivo dentro do ZIP for outro ZIP, chama a função de novo
                    if internal_name.lower().endswith('.zip') or internal_name.lower().endswith('.xml'):
                        process_recursively(internal_name, internal_content, xml_files_dict)
        except zipfile.BadZipFile:
            pass
            
    # Se for um XML solto
    elif file_name.lower().endswith('.xml'):
        add_to_dict(file_name, file_bytes, xml_files_dict)

# --- CONFIGURAÇÃO DO STREAMLIT ---

st.set_page_config(page_title="Extrator Total de XML", page_icon="📂", layout="wide")

st.title("📂 Extrator Total de XML")
st.subheader("Varredura em Pastas, ZIPs e Sub-ZIPs")

st.markdown("""
**Instruções de uso:**
1. No seu computador, entre na sua pasta, dê um **Ctrl + A** (para selecionar todos os arquivos e pastas) e arraste tudo para cá.
2. O sistema vai abrir cada ZIP individualmente, procurar XMLs e separá-los por categoria.
""")

uploaded_files = st.file_uploader(
    "Arraste seus arquivos e pastas aqui", 
    accept_multiple_files=True
)

if uploaded_files:
    if st.button("🚀 Iniciar Extração Profunda"):
        all_xml_data = {} # { "Pasta/Arquivo.xml": bytes }
        
        progress_text = "Processando arquivos... aguarde."
        my_bar = st.progress(0, text=progress_text)
        
        for index, uploaded_file in enumerate(uploaded_files):
            # Lemos o arquivo enviado pelo usuário
            f_bytes = uploaded_file.read()
            f_name = uploaded_file.name
            
            # Chama a função que mergulha em ZIPs e XMLs
            process_recursively(f_name, f_bytes, all_xml_data)
            
            # Atualiza barra de progresso
            progress = (index + 1) / len(uploaded_files)
            my_bar.progress(progress, text=progress_text)
            
        if all_xml_data:
            st.success(f"✅ Finalizado! {len(all_xml_data)} arquivos XML encontrados e organizados.")
            
            # Criar o ZIP Final
            final_zip_buffer = io.BytesIO()
            with zipfile.ZipFile(final_zip_buffer, "w", zipfile.ZIP_DEFLATED) as z_final:
                for path_in_zip, data in all_xml_data.items():
                    z_final.writestr(path_in_zip, data)
            
            # Exibir resumo por categoria
            resumo = {}
            for path in all_xml_data.keys():
                categoria = path.split('/')[0]
                resumo[categoria] = resumo.get(categoria, 0) + 1
            
            st.write("### Resumo da Organização:")
            cols = st.columns(len(resumo))
            for i, (cat, qtd) in enumerate(resumo.items()):
                cols[i].metric(cat, f"{qtd} un")
            
            st.download_button(
                label="📥 Baixar ZIP com XMLs Organizados",
                data=final_zip_buffer.getvalue(),
                file_name="xmls_extraidos_e_organizados.zip",
                mime="application/zip",
                use_container_width=True
            )
        else:
            st.error("Nenhum XML foi encontrado nos arquivos enviados.")
