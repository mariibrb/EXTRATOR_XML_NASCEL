# ... (mantenha a função extrair_tags_estilo_query igual)

if xml_files and report_file:
    # 1. Lendo o Relatório de Status
    if report_file.name.endswith('.csv'):
        df_status = pd.read_csv(report_file, dtype=str) # Lê tudo como texto
    else:
        df_status = pd.read_excel(report_file, dtype=str) # Lê tudo como texto
    
    # 2. LIMPANDO O RELATÓRIO: Remove espaços e garante que a chave seja texto puro
    df_status.columns = [str(c).strip() for c in df_status.columns]
    
    # Identifica as colunas (Ajuste os nomes se necessário)
    col_chave_rel = 'Chave de Acesso' if 'Chave de Acesso' in df_status.columns else df_status.columns[0]
    col_status_rel = 'Situação' if 'Situação' in df_status.columns else df_status.columns[-1]

    # Limpeza profunda na coluna de chave do relatório
    df_status[col_chave_rel] = df_status[col_chave_rel].astype(str).str.replace(r'\D', '', regex=True).str.strip()
    
    # 3. EXTRAÇÃO DOS XMLS
    lista_consolidada = []
    for f in xml_files:
        dados_xml = extrair_tags_estilo_query(f.read())
        lista_consolidada.extend(dados_xml)
    
    if lista_consolidada:
        df_base = pd.DataFrame(lista_consolidada)
        
        # 4. LIMPANDO A BASE XML: Garante que a chave do XML também esteja limpa
        df_base['Chave de Acesso'] = df_base['Chave de Acesso'].astype(str).str.replace(r'\D', '', regex=True).str.strip()

        # Criando o dicionário de DE-PARA
        status_dict = pd.Series(
            df_status[col_status_rel].values, 
            index=df_status[col_chave_rel]
        ).to_dict()
        
        # --- APLICANDO O "PROCV" NA COLUNA AP ---
        df_base['AP'] = df_base['Chave de Acesso'].map(status_dict).fillna("Chave não encontrada no relatório")
        
        st.write(f"### Processamento Concluído")
        st.dataframe(df_base[['Chave de Acesso', 'Número NF', 'AP']].head(15))
        
        # Gerar o arquivo para download
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_base.to_excel(writer, index=False, sheet_name='Base_XML')
            
        st.download_button(
            label="📥 Baixar Base_XML Corrigida",
            data=buffer.getvalue(),
            file_name="Base_XML_Sentinela.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
