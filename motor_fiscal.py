import pandas as pd
import xml.etree.ElementTree as ET
import re
import io

def extrair_dados_xml(files, fluxo):
    """
    Extrai dados dos XMLs seguindo rigorosamente a tipagem e ordem 
    definida no Power Query do usuário.
    """
    dados_lista = []
    
    if not files:
        return pd.DataFrame()

    for f in files:
        try:
            f.seek(0)
            xml_utf8 = f.read().decode('utf-8', errors='ignore')
            # Remove namespaces para facilitar a localização das tags
            xml_limpo = re.sub(r' xmlns="[^"]+"', '', xml_utf8)
            root = ET.fromstring(xml_limpo)
            
            # 1. Dados do Cabeçalho (Ide, Emit, Dest)
            ide = root.find('.//ide')
            emit = root.find('.//emit')
            dest = root.find('.//dest')
            
            num_nf = int(ide.find('nNF').text) if ide.find('nNF') is not None else 0
            data_emissao = ide.find('dhEmi').text if ide.find('dhEmi') is not None else None
            
            # Define qual CNPJ ler baseado no fluxo (Entrada lê Emitente, Saída lê Destinatário)
            if fluxo == "Entrada":
                cnpj = emit.find('CNPJ').text if emit.find('CNPJ') is not None else ""
                uf = emit.find('UF').text if emit.find('UF') is not None else ""
            else:
                cnpj = dest.find('CNPJ').text if dest is not None and dest.find('CNPJ') is not None else ""
                uf = dest.find('UF').text if dest is not None and dest.find('UF') is not None else ""

            vlr_nf = float(root.find('.//vNF').text) if root.find('.//vNF') is not None else 0.0

            # 2. Varredura dos Itens (det)
            for det in root.findall('.//det'):
                n_item = det.attrib.get('nItem')
                prod = det.find('prod')
                imp = det.find('imposto')
                
                # Estrutura de Dicionário espelhando o Power Query
                item = {
                    "NUM_NF": num_nf,
                    "DATA_EMISSAO": pd.to_datetime(data_emissao).replace(tzinfo=None) if data_emissao else None,
                    "CNPJ": cnpj,
                    "UF": uf,
                    "VLR_NF": vlr_nf,
                    "AC": n_item, # Ordem do item
                    "CFOP": int(prod.find('CFOP').text) if prod.find('CFOP') is not None else 0,
                    "COD_PROD": prod.find('cProd').text if prod.find('cProd') is not None else "",
                    "DESCR": prod.find('xProd').text if prod.find('xProd') is not None else "",
                    "NCM": prod.find('NCM').text if prod.find('NCM') is not None else "",
                    "UNID": prod.find('uCom').text if prod.find('uCom') is not None else "",
                    "VUNIT": float(prod.find('vUnCom').text) if prod.find('vUnCom') is not None else 0.0,
                    "QTDE": float(prod.find('qCom').text) if prod.find('qCom') is not None else 0.0,
                    "VPROD": float(prod.find('vProd').text) if prod.find('vProd') is not None else 0.0,
                    "DESC": float(prod.find('vDesc').text) if prod.find('vDesc') is not None else 0.0,
                    "FRETE": float(prod.find('vFrete').text) if prod.find('vFrete') is not None else 0.0,
                    "SEG": float(prod.find('vSeg').text) if prod.find('vSeg') is not None else 0.0,
                    "DESP": float(prod.find('vOutro').text) if prod.find('vOutro') is not None else 0.0,
                    "VC": 0.0, # Valor Contábil (ajustado no processamento se necessário)
                    
                    # ICMS
                    "CST-ICMS": "",
                    "BC-ICMS": 0.0,
                    "VLR-ICMS": 0.0,
                    "BC-ICMS-ST": 0.0,
                    "ICMS-ST": 0.0,
                    
                    # IPI
                    "VLR_IPI": 0.0,
                    
                    # PIS
                    "CST_PIS": "",
                    "BC_PIS": 0.0,
                    "VLR_PIS": 0.0,
                    
                    # COFINS
                    "CST_COF": "",
                    "BC_COF": 0.0,
                    "VLR_COF": 0.0,
                    
                    # Colunas de Análise (Vazias para preenchimento posterior na AO)
                    "NF com possível permissão de crédito ICMS": "",
                    "Análise de Devoluções ": "",
                    "Difal de Entrada": "",
                    "Análise Pis e Cofins": ""
                }

                # --- Extração Técnica de Impostos (det/imposto) ---
                # ICMS
                icms_node = imp.find('.//ICMS')
                if icms_node is not None:
                    for tag in icms_node: # CST ou CSOSN
                        cst = tag.find('CST') if tag.find('CST') is not None else tag.find('CSOSN')
                        item["CST-ICMS"] = cst.text if cst is not None else ""
                        item["BC-ICMS"] = float(tag.find('vBC').text) if tag.find('vBC') is not None else 0.0
                        item["VLR-ICMS"] = float(tag.find('vICMS').text) if tag.find('vICMS') is not None else 0.0
                        item["BC-ICMS-ST"] = float(tag.find('vBCST').text) if tag.find('vBCST') is not None else 0.0
                        item["ICMS-ST"] = float(tag.find('vICMSST').text) if tag.find('vICMSST') is not None else 0.0

                # IPI
                ipi_vlr = imp.find('.//IPI/IPITrib/vIPI')
                if ipi_vlr is not None:
                    item["VLR_IPI"] = float(ipi_vlr.text)

                # PIS
                pis_node = imp.find('.//PIS')
                if pis_node is not None:
                    cst_p = pis_node.find('.//CST')
                    vbc_p = pis_node.find('.//vBC')
                    vpis_p = pis_node.find('.//vPIS')
                    item["CST_PIS"] = cst_p.text if cst_p is not None else ""
                    item["BC_PIS"] = float(vbc_p.text) if vbc_p is not None else 0.0
                    item["VLR_PIS"] = float(vpis_p.text) if vpis_p is not None else 0.0

                # COFINS
                cof_node = imp.find('.//COFINS')
                if cof_node is not None:
                    cst_c = cof_node.find('.//CST')
                    vbc_c = cof_node.find('.//vBC')
                    vcof_c = cof_node.find('.//vCOFINS')
                    item["CST_COF"] = cst_c.text if cst_c is not None else ""
                    item["BC_COF"] = float(vbc_c.text) if vbc_c is not None else 0.0
                    item["VLR_COF"] = float(vcof_c.text) if vcof_c is not None else 0.0

                item["VC"] = item["VPROD"] + item["ICMS-ST"] + item["VLR_IPI"] + item["DESP"] - item["DESC"]
                dados_lista.append(item)

        except Exception as e:
            continue

    return pd.DataFrame(dados_lista)
