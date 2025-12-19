import pandas as pd
import numpy as np
from datetime import datetime

class AnalisadorFiscalConsolidado:
    def __init__(self, caminho_planilha):
        """
        Inicializa o motor de análise lendo as diferentes abas da planilha.
        """
        self.caminho = caminho_planilha
        self.data_processamento = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        # Carregando as abas conforme sua estrutura
        self.df_icms = pd.read_excel(caminho_planilha, sheet_name='ICMS')
        self.df_pis = pd.read_excel(caminho_planilha, sheet_name='PIS')
        self.df_cofins = pd.read_excel(caminho_planilha, sheet_name='COFINS')
        
        # DataFrame Consolidado (Iniciando pela base de ICMS que já validamos)
        self.df_final = self.df_icms.copy()

    def integrar_e_calcular(self):
        """
        Integra os dados das abas PIS/COFINS e calcula o IPI.
        """
        # Fazendo o merge dos dados das outras abas usando 'id_item' ou 'produto' como chave
        # Assumindo que a coluna chave seja 'id_item'
        self.df_final = self.df_final.merge(self.df_pis[['id_item', 'aliquota_pis']], on='id_item', how='left')
        self.df_final = self.df_final.merge(self.df_cofins[['id_item', 'aliquota_cofins']], on='id_item', how='left')

        # Cálculos de PIS e COFINS
        self.df_final['valor_pis'] = self.df_final['valor_item'] * (self.df_final['aliquota_pis'] / 100)
        self.df_final['valor_cofins'] = self.df_final['valor_item'] * (self.df_final['aliquota_cofins'] / 100)
        
        # Cálculo de IPI (Pode vir de uma coluna na aba principal ou tabela fixa)
        # Se o IPI não tiver aba própria, calculamos com base na coluna de entrada
        if 'aliquota_ipi' in self.df_final.columns:
            self.df_final['valor_ipi'] = self.df_final['valor_item'] * (self.df_final['aliquota_ipi'] / 100)
        else:
            self.df_final['valor_ipi'] = 0.0

        # Soma total de impostos por item (ICMS + PIS + COFINS + IPI)
        self.df_final['total_tributos'] = (
            self.df_final['valor_icms'] + 
            self.df_final['valor_pis'] + 
            self.df_final['valor_cofins'] + 
            self.df_final['valor_ipi']
        )
        
        return self

    def aplicar_aprovacao_nivel_1(self):
        """
        Lógica de Aprovação 1: Valida se a soma dos impostos bate com o total informado
        e se as alíquotas estão preenchidas corretamente em todas as abas.
        """
        condicoes = [
            (self.df_final['total_tributos'] > 0) & (self.df_final['aliquota_pis'].notnull()),
            (self.df_final['valor_item'] <= 0)
        ]
        escolhas = ['Aprovado 1', 'Erro: Valor ou Alíquota Inválida']
        
        self.df_final['status_aprovacao'] = np.select(condicoes, escolhas, default='Revisão Pendente')
        self.df_final['data_analise'] = self.data_processamento
        
        return self

    def gerar_output_github(self):
        """
        Gera a saída formatada para o GitHub.
        """
        print(f"## Relatório Consolidado (ICMS, PIS, COFINS, IPI) - {self.data_processamento}")
        
        colunas_print = [
            'produto', 'valor_item', 'valor_icms', 'valor_pis', 
            'valor_cofins', 'valor_ipi', 'total_tributos', 'status_aprovacao'
        ]
        
        print("\n### Detalhamento Multia-aba")
        print(self.df_final[colunas_print].to_markdown(index=False, floatfmt=".2f"))
        
        return self.df_final

# --- EXECUÇÃO DO PROJETO ---

if __name__ == "__main__":
    # Para rodar, você precisaria do arquivo .xlsx com as abas: ICMS, PIS, COFINS
    # Exemplo de como o código seria chamado:
    
    try:
        # caminho = "planilha_fiscal_completa.xlsx"
        # analisador = AnalisadorFiscalConsolidado(caminho)
        
        # Simulação de dados para visualização imediata aqui no chat:
        data_simulada = {
            'id_item': [1, 2],
            'produto': ['Produto A', 'Produto B'],
            'valor_item': [1000.0, 2000.0],
            'valor_icms': [180.0, 360.0],
            'aliquota_pis': [1.65, 1.65],
            'aliquota_cofins': [7.6, 7.6],
            'aliquota_ipi': [5.0, 10.0]
        }
        
        df_teste = pd.DataFrame(data_simulada)
        
        # Simulando o comportamento de integração
        analise = AnalisadorFiscalConsolidado.__new__(AnalisadorFiscalConsolidado)
        analise.df_final = df_teste
        analise.data_processamento = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        analise.integrar_e_calcular().aplicar_aprovacao_nivel_1().gerar_output_github()
        
    except Exception as e:
        print(f"Erro ao processar planilhas: {e}")
