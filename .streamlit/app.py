import streamlit as st
import zipfile
import io
import os
import re
import pandas as pd
import random

# --- MOTOR DE IDENTIFICAÇÃO (INTEGRAL) ---
def identify_xml_info(content_bytes, client_cnpj, file_name):
    client_cnpj_clean = "".join(filter(str.isdigit, str(client_cnpj))) if client_cnpj else ""
    nome_puro = os.path.basename(file_name)
    resumo = {
        "Arquivo": nome_puro, "Chave": "", "Tipo": "Outros", "Série": "0",
        "Número": 0, "Pasta": "RECEBIDOS_TERCEIROS/OUTROS"
    }
    try:
        # Analisamos apenas o cabeçalho para ser veloz
        content_str = content_bytes[:8192].decode('utf-8', errors='ignore')
        match_ch = re.search(r'\d{44}', content_str)
        resumo["Chave"] = match_ch.group(0) if match_ch else ""
        tag_l = content_str.lower()
        
        tipo = "NF-e"
        if '<mod>65</mod>' in tag_l: tipo = "NFC-e"
        elif '<infcte' in tag_l: tipo = "CT-e"
        elif '<infmdfe' in tag_l: tipo = "MDF-e"
        
        status = "NORMAIS"
        if '110111' in tag_l: status = "CANCELADOS"
        elif '110110' in tag_l: status = "CARTA_CORRECAO"
        elif '<inutnfe' in tag_l or '<procinut' in tag_l:
            status = "INUTILIZADOS"
            tipo = "Inutilizacoes"
            
        resumo["Tipo"] = tipo
        s_match = re.search(r'<(?:serie)>(\d+)</', tag_l)
        resumo["Série"] = s_match.group(1) if s_match else "0"
        n_match = re.search(r'<(?:nnf|nct|nmdf|nnfini)>(\d+)</', tag_l)
        resumo["Número"] = int(n_match.group(1)) if n_match else 0
        
        cnpj_emit = re.search(r'<cnpj>(\d+)</cnpj>', tag_l).group(1) if re.search(r'<cnpj>(\d+)</cnpj>', tag_l) else ""
        is_p = (cnpj_emit == client_cnpj_clean) or (resumo["Chave"] and client_cnpj_clean in resumo["Chave"][6:20])
        resumo["Pasta"] = f"EMITIDOS_CLIENTE/{tipo}/{status}/Serie_{resumo['Série']}" if is_p else f"RECEBIDOS_TERCEIROS/{tipo}"
        return resumo, is_p
    except:
        return resumo, False

# --- DESIGN LUXO ---
st.set_page_config(page_title="O Garimpeiro", layout="wide", page_icon="⛏️")
st.markdown("""
    <style>
    #MainMenu, footer, header, .stAppDeployButton {visibility: hidden !important; display: none !important;}
    .stApp { background-color: #f7f3f0; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #EADBC8 0%, #D2B48C 100%) !important; border-right: 3px solid #b8860b; }
    [data-testid="stSidebar"] * { color: #2b1e16 !important; font-weight: 900 !important; }
    h1, h2, h3, h4, p, label, .stMetric label { color: #2b1e16 !important; font-family: 'Playfair Display', serif; font-weight: 900 !important; }
    [data-testid="stMetric"] { background: linear-gradient(135deg, #ffffff 0%, #fff9e6 100%); border: 2px solid #d4af37; border-radius: 20px; padding: 20px; }
    div.stButton > button { background: linear-gradient(180deg, #fcf6ba 0%, #d4af37 40%, #aa771c 100%) !important; color: #2b1e16 !important; border: 2px solid #8a6d3b; padding: 20px !important; font-weight: 900 !important; border-radius: 50px !important; width: 100% !important; text-transform: uppercase !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>⛏️ O GARIMPEIRO</h1>", unsafe_allow_html=True)

# Inicialização segura
if 'garimpo_ok' not in st.session_state: st.session_state['garimpo_ok'] = False
if 'confirmado' not in st.session_state: st.session_state['confirmado'] = False

with st.sidebar:
    st.markdown("### ⛏️ Painel de Extração")
    cnpj_input = st.text_input("CNPJ DO CLIENTE")
    cnpj_limpo = "".join(filter(str.isdigit, cnpj_input))
    if len(cnpj_limpo) == 14:
        if st.button("✅ LIBERAR OPERAÇÃO"):
            st.session_state['confirmado'] = True
            st.rerun()
    st.divider()
    if st.button("🗑️ RESETAR SISTEMA"):
        st.session_state.clear()
        st.rerun()

if st.session_state['confirmado']:
    if not st.session_state['garimpo_ok']:
        uploaded_files = st.file_uploader("Suba seus arquivos:", accept_multiple_files=True)
        if uploaded_files and st.button("🚀 INICIAR GRANDE GARIMPO"):
            keys, rel, seq = set(), [], {}
            buf_org, buf_todos = io.BytesIO(), io.BytesIO()
            
            with st.status("⛏️ Minerando jazidas paralelas...", expanded=True) as status:
                with zipfile.ZipFile(buf_org, "w", zipfile.ZIP_STORED) as z_org, \
                     zipfile.ZipFile(buf_todos, "w", zipfile.ZIP_STORED) as z_todos:
                    
                    for f in uploaded_files:
                        f_bytes = f.read()
                        temp = []
                        if f.name.lower().endswith('.zip'):
                            with zipfile.ZipFile(io.BytesIO(f_bytes)) as z_in:
                                for name in z_in.namelist():
                                    if name.lower().endswith('.xml'):
                                        temp.append((os.path.basename(name), z_in.read(name)))
                        else:
                            temp.append((os.path.basename(f.name), f_bytes))

                        for name, xml_data in temp:
                            res, is_p = identify_xml_info(xml_data, cnpj_limpo, name)
                            k = res["Chave"] if res["Chave"] else name
                            if k not in keys:
                                keys.add(k)
                                # ZIP 1: Organizado
                                z_org.writestr(f"{res['Pasta']}/{name}", xml_data)
                                # ZIP 2: Todos soltos
                                z_todos.writestr(name, xml_data)
                                rel.append(res)
                                if is_p and res["Número"] > 0:
                                    sk = (res["Tipo"], res["Série"])
                                    if sk not in seq: seq[sk] = set()
                                    seq[sk].add(res["Número"])
                        del temp

            # Buracos
            faltantes = []
            for (t, s), nums in seq.items():
                if len(nums) > 1:
                    ideal = set(range(min(nums), max(nums) + 1))
                    for b in sorted(list(ideal - nums)):
                        faltantes.append({"Documento": t, "Série": s, "Nº Faltante": b})

            st.session_state.update({
                'zip_org': buf_org.getvalue(),
                'zip_todos': buf_todos.getvalue(),
                'relatorio': rel,
                'df_faltantes': pd.DataFrame(faltantes),
                'garimpo_ok': True
            })
            st.rerun()
    else:
        # EXIBIÇÃO SEGURA DOS RESULTADOS
        st.success(f"⛏️ Garimpo Concluído! {len(st.session_state.get('relatorio', []))} arquivos processados.")
        
        c1, c2, c3 = st.columns(3)
        if 'relatorio' in st.session_state:
            df_res = pd.DataFrame(st.session_state['relatorio'])
            c1.metric("📦 VOLUME", len(df_res))
            emitidas = len(df_res[df_res['Pasta'].str.contains("EMITIDOS")])
            c2.metric("✨ CLIENTE", emitidas)
            c3.metric("⚠️ BURACOS", len(st.session_state.get('df_faltantes', [])))

        st.divider()
        st.markdown("### 📥 ESCOLHA SUA EXTRAÇÃO")
        col1, col2 = st.columns(2)
        
        # Só mostra o botão se a chave existir no session_state para evitar o KeyError
        with col1:
            if 'zip_org' in st.session_state:
                st.download_button("📂 BAIXAR ORGANIZADO (POR PASTAS)", st.session_state['zip_org'], "garimpo_pastas.zip", use_container_width=True)
            else:
                st.error("Erro ao carregar ZIP organizado. Tente resetar.")

        with col2:
            if 'zip_todos' in st.session_state:
                st.download_button("📦 BAIXAR TODOS (SÓ XML SOLTO)", st.session_state['zip_todos'], "todos_xml.zip", use_container_width=True)
            else:
                st.error("Erro ao carregar ZIP de XMLs soltos.")

        st.divider()
        st.markdown("### ⚠️ AUDITORIA DE SEQUÊNCIA")
        st.dataframe(st.session_state.get('df_faltantes', pd.DataFrame()), use_container_width=True, hide_index=True)

        if st.button("⛏️ NOVO GARIMPO"):
            st.session_state.clear()
            st.rerun()
