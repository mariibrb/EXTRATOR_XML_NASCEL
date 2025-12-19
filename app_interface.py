import streamlit as st

def main():
    # Configuração da página (Equivalente ao root.title e geometry)
    st.set_page_config(page_title="Sentinela - Interface", layout="centered")

    # Título principal
    st.title("Bem-vindo ao Sistema Sentinela")
    
    # Subtítulo ou texto informativo
    st.write("Interface web operacional.")

    # Container para organizar elementos (opcional, para estética)
    with st.container():
        st.markdown("---")
        # Botão de Ação
        if st.button("Executar Ação"):
            # Substitui o messagebox.showinfo
            st.success("Ação executada com sucesso!")
            st.info("O sistema está processando os dados...")

    # Rodapé simples
    st.sidebar.markdown("### Status do Sistema")
    st.sidebar.success("Online")

if __name__ == "__main__":
    main()
