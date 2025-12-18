# ... (parte anterior do código onde você gera o df_final)

if not df_final.empty:
    st.success(f"✅ Auditoria Concluída: {len(df_final)} itens processados.")
    
    # Gerar Excel com motor mais leve
    buffer = io.BytesIO()
    try:
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_final.to_excel(writer, sheet_name='Análise Sentinela', index=False)
            
            # Criar a aba Autent zerada (apenas cabeçalhos) para você colar depois
            df_autent_vazia = pd.DataFrame(columns=['Chave de Acesso', 'Situação', 'Data/Hora'])
            df_autent_vazia.to_excel(writer, sheet_name='Autent', index=False)
            
            # Ajustar largura das colunas automaticamente (opcional, mas ajuda)
            worksheet = writer.sheets['Análise Sentinela']
            worksheet.set_column('A:AZ', 20) 
            
        st.download_button(
            label="📥 Baixar Planilha Sentinela Pronta",
            data=buffer.getvalue(),
            file_name="Sentinela_Auditada_Completa.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        st.error(f"Erro ao gerar o arquivo Excel: {e}")
