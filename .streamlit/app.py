import streamlit as st
import zipfile
import io
import os
import xml.etree.ElementTree as ET
import re
import pandas as pd
import gc

# --- MOTOR DE IDENTIFICAÇÃO (FISCAL) ---
def get_xml_key(root, content_str):
    try:
        ch_tag = root.find(".//chNFe") or root.find(".//chCTe") or root.find(".//chMDFe")
        if ch_tag is not None and ch_tag.text: return ch_tag.text
        inf_tags = [".//infNFe", ".//infCTe", ".//infMDFe", ".//infProc"]
        for tag in inf_tags:
            el = root.find(tag)
            if el is not None and 'Id' in el.attrib:
                k = re.sub(r'\D', '', el.attrib['Id'])
                if len(k) == 44: return k
        f = re.findall(r'\d{44}', content_str)
        if f: return f[0]
    except: pass
    return None

def identify_xml_info(content_bytes, client_cnpj):
    client_cnpj = "".join(filter(str.isdigit, client_cnpj))
    try:
        content_str = content_bytes.decode('utf-8', errors='ignore')
        # Limpeza para economizar RAM
        root = ET.fromstring(re.sub(r'\sxmlns="[^"]+"', '', content_str, count=1))
        
        doc_type = "Outros"
        tag_lower = content_str.lower()
        if '<infnfe' in tag_lower: doc_type = "NFC-e" if '<mod>65</mod>' in tag_lower else "NF-e"
        elif '<infcte' in tag_lower: doc_type = "CT-e"
        elif '<infmdfe' in tag_lower: doc_type = "MDF-e"
        elif '<evento' in tag_lower: doc_type = "Eventos"
        
        emit_cnpj = ""; serie = "0"; numero = None
        emit = root.find(".//emit/CNPJ")
        if emit is not None: emit_cnpj = "".join(filter(str.isdigit, emit.text))
        
        serie_tag = root.find(".//ide/serie")
        if serie_tag is not None: serie = serie_tag.text
        
        n_tag = root.find(".//ide/nNF") or root.find(".//ide/nCT") or root.find(".//ide/nMDF")
        if n_tag is not None: numero = int(n_tag.text)

        chave = get_xml_key(root, content_str)
        is_propria = (client_cnpj and emit_cnpj == client_cnpj)
        
        pasta = f"EMITIDOS_CLIENTE/{doc_type}/Serie_{serie}" if is_propria else f"RECEBIDOS_TERCEIROS/{doc_type}"
        return pasta, chave, is_propria, serie, numero
    except:
        return "NAO_IDENTIFICADOS", None, False, "0", None

def process_files(uploaded_files, client_cnpj):
    all_xml_data = {}
    processed_keys = set()
    sequencias = {}
    
    total
