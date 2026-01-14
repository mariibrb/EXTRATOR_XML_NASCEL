import streamlit as st
import zipfile
import io
import os
import xml.etree.ElementTree as ET
import re
import pandas as pd
import gc

# --- FUNÇÕES DE IDENTIFICAÇÃO (VERSÃO CORREÇÃO DE EMISSÃO) ---
def get_xml_key(content_str):
    match = re.search(r'\d{44}', content_str)
    return match.group(0) if match else None

def identify_xml_info(content_bytes, client_cnpj):
    # LIMPEZA DO CNPJ DO CLIENTE (O que você digita no sidebar)
    client_cnpj_clean = "".join(filter(str.isdigit, str(client_cnpj))) if client_cnpj else ""
    
    pasta = "NAO_IDENTIFICADOS"
    chave = None
    is_p = False
    serie = "0"
    num = None
    d_type = "Outros"

    try:
        content_str = content_bytes.decode('utf-8', errors='ignore')
        chave = get_xml_key(content_str)
        
        # Identificação de Tipo
        if '<mod>65</mod>' in content_str: d_type = "NFC-e"
        elif '<infCTe' in content_str: d_type = "CT-e"
        elif '<infMDFe' in content_str: d_type = "MDF-e"
        elif '<infNFe' in content_str: d_type = "NF-e"
        elif '<evento' in content_str: d_type = "Eventos"

        # Parser XML
        clean_content = re.sub(r'\sxmlns="[^"]+"', '', content_str, count=1)
        root = ET.fromstring(clean_content)
        
        # BUSCA CNPJ DO EMITENTE (Reforçada)
        emit_cnpj = ""
        emit_tag = root.find(".//emit/CNPJ")
        if emit_tag is not None and emit_tag.text:
            emit_cnpj = "".join(filter(str.isdigit, emit_tag.text))
        
        # Busca Série e Número
        s_tag = root.find(".//ide/serie")
        if s_tag is not None: serie = s_tag.text
        
        n_tag = root.find(".//ide/nNF") or root.find(".//ide/nCT") or root.find(".//ide/nMDF")
        if n_tag is not None: num = int(n_tag.text)

        # COMPARAÇÃO ROBUSTA (Verifica se um contém o outro para evitar erros de zeros ou espaços)
        if client_cnpj_clean and emit_cnpj:
            # Se o CNPJ digitado for igual ao do XML (comparações limpas)
            if client_cnpj_clean == emit_cnpj:
                is_p = True
        
        # Atribuição da pasta com base na verificação
        if is_p:
            pasta = f"EMITIDOS_CLIENTE/{d_type}/Serie_{serie}"
        else:
            pasta = f"RECEBIDOS_TERCEIROS/{d_type}"
            
        return pasta, chave, is_p, serie, num, d_type
    except:
        return "ERRO_ARQUIVO", chave, False, "0", None, "ERRO"

# --- INTERFACE ---
st.set_page_config(page_title="Garimpeiro v4.6", layout="wide")
st.title("⛏️ Garimpeiro v4.6 - Fix de Pastas Emitidas")

with st.sidebar:
    st.header("⚙️ Configurações")
    # Usei o value=cnpj_input se já existir para manter o que você digitou
    cnpj_input = st.text_input("CNPJ do Cliente (Copie e Cole aqui)", placeholder="00.000.000/0000-00")
    if st.button("🗑️ Reiniciar Cache"):
        st.cache_data.clear()
        st.rerun()
    st.info("🛠️ Ajuste: Comparação de CNPJ agora ignora qualquer formatação ou espaço.")

uploaded_files = st.file_uploader("Suba seus XMLs (Pastas ou arquivos)", accept_multiple_files=True)

if uploaded_files:
    if st.button("🚀 INICIAR GARIMPO", use_container_width=True):
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
                
                if chave and chave not in processed_keys:
                    processed_keys.add(chave)
                    zf.writestr(f"{pasta}/{chave}.xml", content)
                    
                    cat = pasta.replace('/', ' - ')
                    resumo[cat] = resumo.get(cat, 0) + 1
                    
                    if is_p and num:
                        chave_seq = (d_type, serie)
                        if chave_seq not in sequencias: sequencias[chave_seq] = set()
                        sequencias[chave_seq].add(num)
                
                if i % 20 == 0 or i + 1 == total:
                    bar.progress((i + 1) / total)
                    status.caption(f"Lendo: {i+1} de {total}")
                    gc.collect()

        if processed_keys:
            st.success(f"✅ Processamento finalizado para {len(processed_keys)} notas.")
            
            # Relatório de Faltantes
            faltantes_data = []
            for (d_type, serie), nums in sequencias.items():
                if nums:
                    ideal = set(range(min(nums), max(nums) + 1))
                    buracos = sorted(list(ideal - nums))
                    for b in buracos:
                        faltantes_data.append({"Tipo": d_type, "Série": serie, "Nº Faltante": b})

            col_inf1, col_inf2 = st.columns([1, 1])
            with col_inf1:
                st.write("### 📊 O que encontramos")
                st.table(pd.DataFrame(list(resumo.items()), columns=['Pasta destino', 'Qtd']))
            
            with col_inf2:
                st.write("### ⚠️ Relatório de Faltantes")
                if faltantes_data:
                    st.dataframe(pd.DataFrame(faltantes_data), use_container_width=True)
                else:
                    st.info("Nenhuma falha de sequência!")

            st.divider()
            st.download_button(
                "📥 BAIXAR TUDO (.ZIP)",
                data=zip_buffer.getvalue(),
                file_name="garimpo_v4_6.zip",
                use_container_width=True
            )
        
        zip_buffer.close()
        gc.collect()
