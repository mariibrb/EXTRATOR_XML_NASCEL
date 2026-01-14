import streamlit as st
import zipfile
import io
import os
import xml.etree.ElementTree as ET
import re
import pandas as pd
import gc

# --- MOTOR DE IDENTIFICAÇÃO (FISCAL & ESTABILIDADE) ---
def get_xml_key(root, content_str):
    """Busca a chave de 44 dígitos da forma mais rápida possível."""
    try:
        match = re.search(r'\d{44}', content_str)
        if match: return match.group(0)
        ch_tag = root.find(".//chNFe") or root.find(".//chCTe") or root.find(".//chMDFe")
        if ch_tag is not None and ch_tag.text: return ch_tag.text
    except: pass
    return None

def identify_xml_info(content_bytes, client_cnpj):
    """Extrai Tipo, Série, Número e define a Pasta."""
    client_cnpj = "".join(filter(str.isdigit, client_cnpj)) if client_cnpj else ""
    try:
        content_str = content_bytes.decode('utf-8', errors='ignore')
        # Limpeza para o parser não travar a RAM
        clean_content = re.sub(r'\sxmlns="[^"]+"', '', content_str, count=1)
        root = ET.fromstring(clean_content)
        
        doc_type = "NF-e"
        tag_lower = content_str.lower()
        if '<mod>65</mod>' in tag_lower: doc_type = "NFC-e"
        elif '<infcte' in tag_lower: doc_type = "CT-e"
        elif '<infmdfe' in tag_lower: doc_type = "MDF-e"
        elif '<evento' in tag_lower: doc_type = "Eventos"
        
        emit_cnpj = ""
        emit = root.find(".//emit/CNPJ")
        if emit is not None: emit_cnpj = "".join(filter(str.isdigit, emit.text))
        
        serie = "0"
        s_tag = root.find(".//ide/serie")
        if s_tag is not None: serie = s_tag.text
        
        num = None
        n_tag = root.find(".//ide/nNF") or root.find(".//ide/nCT") or root.find(".//ide/nMDF")
        if n_tag is not None: num = int(n_tag.text)

        chave = get_xml_key(root, content_str)
        is_propria = (client_cnpj != "" and emit_cnpj == client_cnpj)
        
        # Estrutura de pastas solicitada: Emitidos por Série e Recebidos por Tipo
        if is_propria:
            pasta = f"EMITIDOS_CLIENTE/{doc_type}/Serie_{serie}"
        else:
            pasta = f"RECEBIDOS_TERCEIROS/{doc_type}"
        
        return pasta, chave, is_propria, serie, num
    except:
        return "NAO_IDENTIFICADOS", None, False, "0", None

def process_recursively(file_name, file_bytes, xml_files_dict, client_cnpj, processed_keys, sequencias):
    """Lê arquivos e descompacta ZIPs internos se houver."""
    if file_name.lower().endswith('.zip'):
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                for info in z.infolist():
                    if info.is_dir(): continue
                    process_recursively(info.filename, z.read(info.filename), xml_files_dict, client_cnpj, processed_keys, sequencias)
        except: pass
    elif file_name.lower().endswith('.xml'):
        pasta, chave, is_p, serie, num = identify_xml_info(file_bytes, client_cnpj)
        if chave and chave not in processed_keys:
            processed_keys.add(chave)
            xml_files_dict[f"{pasta}/{chave}.xml"] = file_bytes
            if is_p and num:
                if serie not in sequencias: sequencias[serie] = set()
                sequencias[serie].add(num)

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Garimpeiro v4.1", layout="wide", page_icon="⛏️")

# CSS para melhorar o visual das métricas
st.markdown("""<style> .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; } </style>""", unsafe_allow_html=True)

st.title("⛏️ Garimpeiro de XML - Edição Completa")

with st.sidebar:
    st.header("⚙️ Configurações")
    cnpj_input = st.text_input("CNPJ do Cliente (Só números)", placeholder="Para relatórios e pastas de emissão própria")
    st.divider()
    if st.button("🗑️ Resetar App (Limpar Memória)"):
        st.cache_data.clear()
        st.rerun()
    st.info("💡 Dica: Se tiver muitos arquivos, suba um arquivo .ZIP para ser mais rápido.")

st.markdown("### 📥 1. Carregar Arquivos")
uploaded_files = st.file_uploader("Arraste sua pasta ou arquivos aqui", accept_multiple_files=True)

if uploaded_files:
    total = len(uploaded_files)
    if st.button("🚀 INICIAR GARIMPO TOTAL", use_container_width=True):
        all_xml_data = {}
        processed_keys = set()
        sequencias_proprias = {}

        # Painel de Progresso Fixo
        with st.container(border=True):
            st.write("### 📈 Progresso da Mineração")
            barra_geral = st.progress(0)
            c1, c2, c3 = st.columns(3)
            m_perc = c1.empty()
            m_qtd = c2.empty()
            m_unicos = c3.empty()
            txt_atual = st.empty()

        for i, file in enumerate(uploaded_files):
            process_recursively(file.name, file.read(), all_xml_data, cnpj_input, processed_keys, sequencias_proprias)
            
            # Atualização da Barra Geral
            prog = (i + 1) / total
            barra_geral.progress(prog)
            m_perc.metric("Concluído", f"{int(prog * 100)}%")
            m_qtd.metric("Arquivos Lidos", f"{i+1} de {total}")
            m_unicos.metric("Notas Únicas", len(all_xml_data))
            txt_atual.caption(f"⛏️ Minerando: {file.name}")
            
            if i % 50 == 0: gc.collect()

        if all_xml_data:
            txt_atual.empty()
            st.balloons()
            st.success(f"✨ Garimpo Finalizado! {len(all_xml_data)} XMLs organizados.")

            # --- PARTE 1: INVENTÁRIO (O QUE FOI ACHADO) ---
            st.divider()
            st.write("### 📊 Inventário Detalhado (Por Série e Tipo)")
            resumo = {}
            for path in all_xml_data.keys():
                cat = " - ".join(path.split('/')[:-1]).replace('_', ' ')
                resumo[cat] = resumo.get(cat, 0) + 1
            
            df_resumo = pd.DataFrame(list(resumo.items()), columns=['Pasta / Série', 'Quantidade'])
            st.table(df_resumo)

            # --- PARTE 2: RELATÓRIO DE FALTANTES ---
            st.divider()
            st.write("### ⚠️ Relatório de Notas Faltantes (Emissão Própria)")
            faltantes_list = []
            if sequencias_proprias:
                for serie, numeros in sequencias_proprias.items():
                    if numeros:
                        seq_ideal = set(range(min(numeros), max(numeros) + 1))
                        buracos = sorted(list(seq_ideal - numeros))
                        for b in buracos:
                            faltantes_list.append({"Série": serie, "Número Faltante": b})
            
            if faltantes_list:
                df_f = pd.DataFrame(faltantes_list)
                st.dataframe(df_f, use_container_width=True)
                st.download_button("📥 Baixar Lista de Faltantes (CSV)", df_f.to_csv(index=False).encode('utf-8'), "faltantes.csv")
            else:
                st.info("✅ Nenhuma quebra de sequência detectada nas séries encontradas.")

            # --- PARTE 3: GERAÇÃO DO ZIP FINAL ---
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for p, d in all_xml_data.items():
                    zf.writestr(p, d)
                if faltantes_list:
                    zf.writestr("RELATORIOS/notas_faltantes.csv", pd.DataFrame(faltantes_list).to_csv(index=False))
            
            st.write("")
            st.download_button(
                label="📥 BAIXAR TUDO ORGANIZADO (.ZIP)",
                data=zip_buf.getvalue(),
                file_name="garimpo_finalizado.zip",
                mime="application/zip",
                use_container_width=True
            )
            
            # Limpeza final de memória
            all_xml_data.clear()
            gc.collect()
        else:
            st.error("❌ Nenhum XML válido foi encontrado nos arquivos enviados.")

st.divider()
st.caption("FoxHelper v4.1 - O Garimpeiro Definitivo | Filtro de Série | Relatório de Sequência | Anti-Erro RAM")
