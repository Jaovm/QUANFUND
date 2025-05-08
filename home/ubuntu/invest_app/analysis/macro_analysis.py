# -*- coding: utf-8 -*-
"""
Módulo para análise macroeconômica e de sensibilidade setorial.

Funcionalidades:
- Coletar e processar dados macroeconômicos (taxa de juros, inflação, PIB, etc.).
- Manter um dicionário de sensibilidade setorial a diferentes cenários macro.
- Identificar o cenário macroeconômico atual (pode ser manual ou automático no futuro).
- Sugerir setores favorecidos com base no cenário.
"""

import pandas as pd

__version__ = "0.0.1"
__author__ = "Manus AI Agent"
__email__ = ""

# Dicionário de sensibilidade setorial expandido e mais detalhado
# Valores: 2 (Muito Positivo), 1 (Positivo), 0 (Neutro), -1 (Negativo), -2 (Muito Negativo)
# Setores baseados em classificações comuns da B3 ou mercado.
SECTOR_SENSITIVITY = {
    "Crescimento Econômico Forte (PIB Alto)": {
        "Consumo Cíclico (Varejo, Automóveis, Construção Civil)": 2,
        "Bens Industriais (Máquinas, Equipamentos)": 2,
        "Tecnologia (Software, Hardware)": 1,
        "Financeiro (Bancos, Seguradoras)": 1,
        "Materiais Básicos (Mineração, Siderurgia, Papel e Celulose)": 1,
        "Consumo Não Cíclico (Alimentos, Bebidas, Saúde)": 0,
        "Utilidades Públicas (Energia, Saneamento)": 0,
        "Petróleo e Gás": 0,
        "Comunicações": 0,
    },
    "Recessão Econômica (PIB Baixo/Negativo)": {
        "Consumo Cíclico (Varejo, Automóveis, Construção Civil)": -2,
        "Bens Industriais (Máquinas, Equipamentos)": -2,
        "Tecnologia (Software, Hardware)": -1,
        "Financeiro (Bancos, Seguradoras)": -1,
        "Materiais Básicos (Mineração, Siderurgia, Papel e Celulose)": -1,
        "Consumo Não Cíclico (Alimentos, Bebidas, Saúde)": 1, # Defensivo
        "Utilidades Públicas (Energia, Saneamento)": 1, # Defensivo
        "Petróleo e Gás": 0,
        "Comunicações": 0,
    },
    "Juros Altos (Política Monetária Apertada)": {
        "Consumo Cíclico (Varejo, Automóveis, Construção Civil)": -2, # Crédito caro
        "Bens Industriais (Máquinas, Equipamentos)": -1,
        "Tecnologia (Valuation sensível a juros)": -2,
        "Imobiliário (Financiamento caro)": -2,
        "Financeiro (Bancos podem se beneficiar do spread, mas inadimplência sobe)": 0, # Efeito misto
        "Utilidades Públicas (Endividadas, mas repassam custos)": -1,
        "Consumo Não Cíclico (Alimentos, Bebidas, Saúde)": 0,
        "Materiais Básicos (Commodities podem ser afetadas por demanda global)": -1,
    },
    "Juros Baixos (Política Monetária Expansionista)": {
        "Consumo Cíclico (Varejo, Automóveis, Construção Civil)": 2, # Crédito barato
        "Bens Industriais (Máquinas, Equipamentos)": 1,
        "Tecnologia (Valuation beneficiado)": 2,
        "Imobiliário (Financiamento barato)": 2,
        "Financeiro (Compressão de spread, mas maior volume de crédito)": 0, # Efeito misto
        "Utilidades Públicas (Menor custo de dívida)": 1,
        "Consumo Não Cíclico (Alimentos, Bebidas, Saúde)": 0,
    },
    "Inflação Alta e Persistente": {
        "Consumo Não Cíclico (Repasse de preços, demanda inelástica)": 1,
        "Materiais Básicos (Commodities como hedge)": 1,
        "Financeiro (Títulos indexados à inflação, spread)": 1,
        "Imobiliário (Ativos reais como hedge)": 1,
        "Consumo Cíclico (Poder de compra corroído)": -2,
        "Utilidades Públicas (Dificuldade de repasse integral e imediato)": -1,
        "Tecnologia (Custos podem subir, poder de precificação varia)": -1,
    },
    "Inflação Controlada (Meta)": {
        "Geral (Estabilidade beneficia a maioria dos setores)": 1 # Positivo para o ambiente de negócios
    },
    "Desvalorização Cambial (Real Fraco)": {
        "Exportadoras (Materiais Básicos, Agronegócio, Papel e Celulose, Embraer)": 2,
        "Turismo Receptivo": 1,
        "Setores com Custos Dolarizados e Receita em Real": -2,
        "Importadoras": -2,
    },
    "Valorização Cambial (Real Forte)": {
        "Importadoras": 2,
        "Setores com Custos em Real e Receita Dolarizada (alguns serviços)": -1,
        "Exportadoras": -2,
        "Turismo Emissivo (empresas de viagem)": 1,
    }
    # Adicionar mais cenários: Crise Política, Reformas Estruturais, etc.
}

class MacroEconomicAnalysis:
    """Classe para realizar análises macroeconômicas e setoriais."""

    def __init__(self, macro_data: pd.DataFrame = None, api_client=None):
        """
        Inicializa com dados macroeconômicos e, opcionalmente, um cliente de API.

        Args:
            macro_data (pd.DataFrame, optional): DataFrame com séries históricas de indicadores macro.
                                              Ex: colunas como "SELIC", "IPCA_Mensal", "PIB_Anual_Var", "Cambio_BRLUSD".
                                              Índice deve ser DatetimeIndex.
            api_client: Cliente da API do Datasource (para buscar dados macro se necessário).
        """
        self.macro_data = macro_data
        if self.macro_data is not None and not isinstance(self.macro_data.index, pd.DatetimeIndex):
            try:
                self.macro_data.index = pd.to_datetime(self.macro_data.index)
            except Exception as e:
                print(f"Erro ao converter índice do macro_data para DatetimeIndex: {e}")
                self.macro_data = None
        
        self.api_client = api_client # Pode ser usado para buscar dados macro recentes
        self.current_scenario_name = "Não Definido"
        self.current_scenario_details = {}

    def identify_current_scenario(self, manual_scenario_name: str = None, latest_selic: float = None, latest_ipca_12m: float = None, latest_pib_growth_annual: float = None) -> tuple[str, dict]:
        """
        Identifica o cenário macroeconômico atual.
        Pode ser um input manual ou uma análise (simplificada por enquanto) dos dados.

        Args:
            manual_scenario_name (str, optional): Cenário definido manualmente pelo usuário (deve ser uma chave em SECTOR_SENSITIVITY).
            latest_selic (float, optional): Última taxa SELIC anualizada (ex: 0.10 para 10%).
            latest_ipca_12m (float, optional): Último IPCA acumulado em 12 meses (ex: 0.05 para 5%).
            latest_pib_growth_annual (float, optional): Último crescimento anual do PIB (ex: 0.02 para 2%).

        Returns:
            tuple[str, dict]: (Nome do cenário identificado, Detalhes do cenário com sensibilidades setoriais)
        """
        if manual_scenario_name and manual_scenario_name in SECTOR_SENSITIVITY:
            self.current_scenario_name = manual_scenario_name
            self.current_scenario_details = SECTOR_SENSITIVITY[manual_scenario_name]
            print(f"Cenário definido manualmente: {self.current_scenario_name}")
            return self.current_scenario_name, self.current_scenario_details

        # Lógica para identificar automaticamente o cenário (simplificada)
        # Esta lógica pode ser muito mais complexa, usando o self.macro_data ou dados de API.
        # Por enquanto, usaremos os parâmetros diretos se fornecidos.
        
        # Exemplo de lógica automática (MUITO SIMPLIFICADA):
        if latest_selic is not None and latest_ipca_12m is not None:
            if latest_selic > 0.10: # Acima de 10%
                if latest_ipca_12m > 0.06: # Acima de 6%
                    self.current_scenario_name = "Juros Altos (Política Monetária Apertada)" # Prioriza juros se ambos altos
                else:
                    self.current_scenario_name = "Juros Altos (Política Monetária Apertada)"
            elif latest_ipca_12m > 0.06:
                self.current_scenario_name = "Inflação Alta e Persistente"
            elif latest_pib_growth_annual is not None and latest_pib_growth_annual < 0.01:
                 self.current_scenario_name = "Recessão Econômica (PIB Baixo/Negativo)"
            elif latest_pib_growth_annual is not None and latest_pib_growth_annual > 0.025:
                 self.current_scenario_name = "Crescimento Econômico Forte (PIB Alto)"
            else:
                self.current_scenario_name = "Inflação Controlada (Meta)" # Cenário base
        else:
            # Se não houver dados suficientes para análise automática, usa um default ou o último definido.
            if self.current_scenario_name == "Não Definido": # Evita sobrescrever um cenário já definido se este método for chamado de novo sem params
                 self.current_scenario_name = "Inflação Controlada (Meta)" # Default geral
            print("Dados insuficientes para análise automática de cenário. Usando default ou último definido.")

        self.current_scenario_details = SECTOR_SENSITIVITY.get(self.current_scenario_name, {})
        print(f"Cenário identificado automaticamente: {self.current_scenario_name}")
        return self.current_scenario_name, self.current_scenario_details

    def get_favored_sectors(self, scenario_name: str = None) -> dict:
        """
        Retorna os setores e suas sensibilidades para um dado cenário.

        Args:
            scenario_name (str, optional): O nome do cenário macroeconômico. 
                                         Se None, usa o cenário atual identificado pela classe.

        Returns:
            dict: Dicionário com setores e sua sensibilidade (score de -2 a 2).
                  Ex: {"Consumo Cíclico": -2, ...}
        """
        target_scenario_name = scenario_name if scenario_name else self.current_scenario_name
        
        if not target_scenario_name or target_scenario_name == "Não Definido":
            print("Alerta: Cenário macroeconômico não definido para obter setores favorecidos.")
            return {"Erro": "Cenário macroeconômico não definido."}
        
        favored = SECTOR_SENSITIVITY.get(target_scenario_name)
        if favored is None:
            print(f"Alerta: Cenário '{target_scenario_name}' não encontrado no dicionário de sensibilidade.")
            return {"Erro": f"Cenário '{target_scenario_name}' não mapeado."}
            
        return favored

if __name__ == "__main__":
    print("Executando exemplos locais para MacroEconomicAnalysis...")
    macro_analyzer = MacroEconomicAnalysis()
    
    print("\n--- Teste com Cenário Manual ---")
    manual_scn_name = "Juros Baixos (Política Monetária Expansionista)"
    name, details = macro_analyzer.identify_current_scenario(manual_scenario_name=manual_scn_name)
    print(f"Cenário: {name}")
    # print(f"Detalhes: {details}")
    favored_sectors_manual = macro_analyzer.get_favored_sectors()
    print(f"Sensibilidade Setorial: {favored_sectors_manual}")

    print("\n--- Teste com Identificação Automática (Simulada) --- ")
    # Exemplo 1: Juros e Inflação Altos
    name_auto1, details_auto1 = macro_analyzer.identify_current_scenario(latest_selic=0.13, latest_ipca_12m=0.07, latest_pib_growth_annual=0.01)
    print(f"Cenário Auto 1: {name_auto1}")
    favored_auto1 = macro_analyzer.get_favored_sectors()
    print(f"Sensibilidade Setorial Auto 1: {favored_auto1}")

    # Exemplo 2: Inflação Alta, Juros Baixos (menos comum, mas para testar lógica)
    name_auto2, details_auto2 = macro_analyzer.identify_current_scenario(latest_selic=0.05, latest_ipca_12m=0.08, latest_pib_growth_annual=0.015)
    print(f"Cenário Auto 2: {name_auto2}") # Deve cair em "Inflação Alta e Persistente"
    favored_auto2 = macro_analyzer.get_favored_sectors()
    print(f"Sensibilidade Setorial Auto 2: {favored_auto2}")

    # Exemplo 3: Crescimento Forte
    name_auto3, details_auto3 = macro_analyzer.identify_current_scenario(latest_selic=0.08, latest_ipca_12m=0.04, latest_pib_growth_annual=0.03)
    print(f"Cenário Auto 3: {name_auto3}")
    favored_auto3 = macro_analyzer.get_favored_sectors()
    print(f"Sensibilidade Setorial Auto 3: {favored_auto3}")
    
    # Exemplo 4: Recessão
    name_auto4, details_auto4 = macro_analyzer.identify_current_scenario(latest_selic=0.09, latest_ipca_12m=0.03, latest_pib_growth_annual=-0.01)
    print(f"Cenário Auto 4: {name_auto4}")
    favored_auto4 = macro_analyzer.get_favored_sectors()
    print(f"Sensibilidade Setorial Auto 4: {favored_auto4}")

    # Teste buscando setores para um cenário específico não setado como atual
    print("\n--- Teste get_favored_sectors para cenário específico ---")
    specific_favored = macro_analyzer.get_favored_sectors(scenario_name="Desvalorização Cambial (Real Fraco)")
    print(f"Sensibilidade para 'Desvalorização Cambial': {specific_favored}")

