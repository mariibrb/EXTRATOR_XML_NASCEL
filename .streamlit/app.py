import streamlit as st
import zipfile
import io
import os
import streamlit.components.v1 as components

# --- FUNÇÕES DE IDENTIFICAÇÃO (FISCAL) ---

def identify_xml_type(content_bytes):
    try:
        content = content_bytes.decode('utf-8', errors='ignore').lower()
        if '<infnfe' in content:
            return "NFC-e" if '<mod>65</mod>' in content else "NF-e"
        elif '<infcte' in content: return "CT-e"
        elif '<infmdfe' in content: return "MDF-e"
        elif '<infresevento' in content or '<evento' in content: return "Eventos"
        elif '<procnfe' in content: return "NF-e"
        elif '<proccte' in content: return "CT-e"
        else: return "Outros_XMLs"
    except:
        return "Nao_Identificados"

def add_to_dict(filepath, content, xml_files_dict):
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
    """Varre ZIPs dentro de ZIPs e captura XMLs"""
    if file_name.lower().endswith('.zip'):
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                for internal_info in z.infolist():
                    if internal_info.is_dir(): continue
                    internal_content = z.read(internal_info.filename)
                    process_recursively(internal_info.filename, internal_content, xml_files_dict)
        except:
            pass
    elif file_name.lower().endswith('.xml'):
        add_to_dict(file_name, file_bytes, xml_files_dict)

# --- INTERFACE ---

st.set_page_config(page_title="Extrator de Pastas XML", page_icon="🚀", layout="wide")

st.title("🚀 Extrator Inteligente: Pastas, ZIPs e XMLs")
st.markdown("Selecione a **pasta raiz** e eu farei o trabalho sujo de abrir tudo e separar por tipo.")

# Hack para aceitar pastas: o Streamlit por padrão não tem webkitdirectory.
# Usamos o st.file_uploader com accept_multiple_files=True.
# DICA DE OURO: Para subir a pasta, arraste ela para o campo abaixo ou 
# entre na pasta, selecione tudo (Ctrl+A) e arraste.

uploaded_files = st.file_uploader(
    "Arraste a sua PASTA principal para cá", 
    accept_multiple_files=True
)

if uploaded_files:
    if st.button("📥 PROCESSAR TUDO E SEPARAR FISCAL"):
        all_xml_data = {}
        progress_bar = st.progress(0)
        status = st.empty()
        
        total = len(uploaded_files)
        for i, file in enumerate(uploaded_files):
            status.text(f"Garimpando: {file.name}")
            content = file.read()
            process_recursively(file.name, content, all_xml_data)
            progress_bar.progress((i + 1) / total)

        if all_xml_data:
            st.success(f"✅ Pronto! Encontramos {len(all_xml_data)} XMLs organizados.")
            
            # Criar ZIP final
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z_final:
                for path, data in all_xml_data.items():
                    z_final.writestr(path, data)
            
            # Métricas
            resumo = {}
            for path in all_xml_data.keys():
                cat = path.split('/')[0]
                resumo[cat] = resumo.get(cat, 0) + 1
            
            cols = st.columns(len(resumo))
            for i, (cat, qtd) in enumerate(resumo.items()):
                cols[i].metric(cat, f"{qtd} un")

            st.download_button(
                label="📦 BAIXAR TUDO PRONTO (.ZIP)",
                data=zip_buffer.getvalue(),
                file_name="xmls_separados.zip",
                mime="application/zip",
                use_container_width=True
            )
        else:
            st.error("Nenhum XML foi encontrado dentro dos arquivos ou pastas.")

st.divider()
st.info("💡 **Dica Infalível:** Se o botão 'Browse' não deixar escolher a pasta, abra a pasta no seu computador, aperte **Ctrl+A** (selecionar tudo) e arraste para o retângulo acima. O sistema vai abrir todos os ZIPs internos automaticamente!")
