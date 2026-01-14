import streamlit as st
import zipfile
import io
import os
import xml.etree.ElementTree as ET
import re
import pandas as pd
import gc

# --- MOTOR DE IDENTIFICAÇÃO RESTAURADO ---
def get_xml_key(content_str):
    match = re.search(r'\d{44}', content_str)
    return match.group(0) if match else None

def identify_xml_info(content_bytes, client_cnpj):
    # Limpeza rigorosa do CNPJ do sidebar
    client_cnpj_clean = "".join(filter(str.isdigit, str(client_cnpj))) if client_cnpj else ""
    
    pasta = "NAO_IDENTIFICADOS"
    chave = None
    is_p = False
    serie = "0"
    num = None
    d_type = "Outros"

    try:
        # Tenta ler o arquivo de forma resiliente (UTF-8 ou Latin-1)
        try:
            content_str = content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            content_str = content_bytes.decode('latin-1', errors='ignore')

        chave = get_xml_key(content_str)
        
        # Identificação do Tipo de Documento
        tag_lower = content_str.lower()
        if '<mod>65</mod>' in tag_lower: d_type = "NFC-e"
        elif '<infcte' in tag_lower: d_type = "CT-e"
        elif '<infmdfe' in tag_lower: d_type = "MDF-e"
        elif '<infnfe' in tag_lower: d_type = "NF-e"
        elif '<evento' in tag_lower: d_type = "Eventos"

        # Parser XML completo para garantir a captura do Emitente
        clean_content = re.sub(r'\sxmlns="[^"]+"', '', content_str, count=1)
        root = ET.fromstring(clean_content)
        
        # BUSCA DO EMITENTE (Onde a mágica acontece)
        emit_cnpj = ""
        # Tentamos encontrar o CNPJ do emitente em qualquer lugar da tag <emit>
        emit_tag = root.find(".//emit/CNPJ")
        if emit_tag is not None and emit_tag.text:
            emit_cnpj = "".join(filter(str.isdigit, emit_tag.text))
        
        # Série e Número
        s_tag = root.find(".//ide/serie")
        if s_tag is not None: serie = s_tag.text
        
        n_tag = root.find(".//ide/nNF") or root.find(".//ide/nCT") or root.find(".//ide/nMDF")
        if n_tag is not None: num = int(n_tag.text)

        # COMPARAÇÃO DE CNPJ (Voltou a ser a prioridade)
        if client_cnpj_clean and emit_cnpj == client_cnpj_clean:
            is_p = True
            pasta = f"EMITIDOS_CLIENTE/{d_type}/Serie_{serie}"
        else:
            # Backup: Verifica se o CNPJ está na chave de acesso
            if chave and client_cnpj_clean and client_cnpj_clean in chave[6:20]:
                is_p = True
                pasta = f"EMITIDOS_CLIENTE/{d_type}/Serie_{serie}"
            else:
                is_p = False
                pasta = f"RECEBIDOS_TERCEIROS/{d_type}"
            
        return pasta, chave, is_p, serie, num, d_type
    except:
        return "ERRO_PROCESSAMENTO", None, False, "0", None, "ERRO"

# --- INTERFACE ---
st.set_page_config(page_title="Garimpeiro v4.8", layout="wide", page_icon="⛏️")
st.title("⛏️ Garimpeiro v4.8 - A Volta das Emitidas")

with st.sidebar:
    st.header("⚙️ Configurações")
    cnpj_input = st.text_input("CNPJ do Cliente (Obrigatório para EMITIDAS)", placeholder="Ex: 12.345.678/0001-99")
    if st.button("🗑️ Resetar Sistema"):
        st.cache_data.clear()
        st.rerun()

uploaded_files = st.file_uploader("Suba seus XMLs", accept_multiple_files=True)

if uploaded_files:
    if st.button("🚀 INICIAR GARIMPO COMPLETO", use_container_width=True):
        processed_keys = set()
        sequencias = {} 
        resumo = {}
        
        zip_buffer = io.BytesIO()
        total = len(uploaded_files)
        bar = st.progress(0)
        status = st.empty()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, file in enumerate(uploaded_files):
                content = file.read()
                pasta, chave, is_p, serie, num, d_type = identify_xml_info(content, cnpj_input)
                
                if pasta != "ERRO_PROCESSAMENTO" and chave and chave not in processed_keys:
                    processed_keys.add(chave)
                    # Grava no ZIP
                    zf.writestr(f"{pasta}/{chave}.xml", content)
                    
                    # Alimenta Inventário
                    cat = pasta.replace('/', ' - ')
                    resumo[cat] = resumo.get(cat, 0) + 1
                    
                    # Alimenta Sequencial de Faltantes (SÓ SE FOR EMISSÃO PRÓPRIA)
                    if is_p and num:
                        chave_seq = (d_type, serie)
                        if chave_seq not in sequencias: sequencias[chave_seq] = set()
                        sequencias[chave_seq].add(num)
                
                if i % 25 == 0 or i + 1 == total:
                    bar.progress((i + 1) / total)
                    status.caption(f"Processando: {i+1} de {total}")
                    gc.collect()

        if processed_keys:
            st.success(f"✅ Garimpo pronto! {len(processed_keys)} notas organizadas.")
            
            # --- RELATÓRIO DE FALTANTES ---
            faltantes_data = []
            for (d_type, serie), nums in sequencias.items():
                if nums:
                    ideal = set(range(min(nums), max(nums) + 1))
                    buracos = sorted(list(ideal - nums))
                    for b in buracos:
                        faltantes_data.append({"Tipo": d_type, "Série": serie, "Nº Faltante": b})

            col_a, col_b = st.columns(2)
            with col_a:
                st.write("### 📊 Inventário Final")
                st.table(pd.DataFrame(list(resumo.items()), columns=['Caminho', 'Qtd']))
            
            with col_b:
                st.write("### ⚠️ Notas Faltantes")
                if faltantes_data:
                    st.dataframe(pd.DataFrame(faltantes_data), use_container_width=True)
                else:
                    st.info("Nenhuma falha de sequência nas notas emitidas.")

            st.divider()
            st.download_button("📥 BAIXAR TUDO (.ZIP)", zip_buffer.getvalue(), "garimpo_v4_8.zip", use_container_width=True)
        
        zip_buffer.close()
        gc.collect()
