# -*- coding: utf-8 -*-
"""
Módulo para análise da carteira do usuário e sugestão de aportes.

Funcionalidades:
- Processar a carteira atual do usuário (upload).
- Analisar a alocação setorial da carteira.
- Comparar com setores atrativos identificados pela análise macroeconômica.
- Identificar oportunidades de valuation dentro dos setores priorizados.
- Sugerir aportes para rebalanceamento e aproveitamento de oportunidades.
"""

import pandas as pd
import numpy as np

# Para type hinting e evitar import circular em tempo de execução real, usamos strings
# from ..analysis.macro_analysis import MacroEconomicAnalysis
# from ..analysis.valuation import ValuationModels
# from ..data_collection.yahoo_finance_api import YahooFinanceAPI

__version__ = "0.0.1"
__author__ = "Manus AI Agent"
__email__ = ""

class PortfolioSuggestor:
    """Classe para analisar a carteira do usuário e sugerir aportes."""

    def __init__(self, user_portfolio_df: pd.DataFrame, 
                 macro_analyzer, # Instância de MacroEconomicAnalysis
                 valuation_model_class, # Classe ValuationModels (não instanciada)
                 stock_data_fetcher, # Instância de YahooFinanceAPI ou similar
                 current_stock_prices: pd.Series = None):
        """
        Inicializa o PortfolioSuggestor.

        Args:
            user_portfolio_df (pd.DataFrame): DataFrame da carteira do usuário.
                                              Colunas esperadas: ["Ticker", "Quantidade", "PrecoMedio"].
                                              Opcionalmente: ["Setor"].
            macro_analyzer: Instância da classe MacroEconomicAnalysis já configurada.
            valuation_model_class: A classe ValuationModels em si, para ser instanciada conforme necessário.
            stock_data_fetcher: Acesso à API para buscar dados de ações (info, preços).
            current_stock_prices (pd.Series, optional): Série com preços atuais dos tickers, indexada por ticker.
                                                      Se não fornecida, tentará buscar.
        """
        self.user_portfolio_df = user_portfolio_df.copy()
        self.macro_analyzer = macro_analyzer
        self.valuation_model_class = valuation_model_class
        self.stock_data_fetcher = stock_data_fetcher
        self.current_stock_prices = current_stock_prices
        self.potential_new_investments = [] # Lista de dicts com info de novos ativos

        self._prepare_portfolio_data()

    def _get_sector_for_ticker(self, ticker: str) -> str:
        """Busca o setor de um ticker. Usa stock_data_fetcher se disponível."""
        if self.stock_data_fetcher:
            # Adicionar .SA se não tiver para a busca de info
            parsed_ticker = ticker if ticker.upper().endswith(".SA") else ticker.upper() + ".SA"
            info = self.stock_data_fetcher.get_stock_info(parsed_ticker)
            sector = info.get("sector", "Outros")
            # Heurística para traduzir/simplificar setores do Yahoo Finance
            if sector == "Financial Services": sector = "Financeiro"
            if sector == "Technology": sector = "Tecnologia"
            if sector == "Consumer Cyclical": sector = "Consumo Cíclico"
            if sector == "Consumer Defensive": sector = "Consumo Não Cíclico"
            if sector == "Basic Materials": sector = "Materiais Básicos"
            if sector == "Industrials": sector = "Bens Industriais"
            if sector == "Energy": sector = "Petróleo e Gás"
            if sector == "Utilities": sector = "Utilidades Públicas"
            if sector == "Real Estate": sector = "Imobiliário"
            if sector == "Healthcare": sector = "Saúde"
            return sector if sector else "Outros"
        
        # Fallback para mock se fetcher não funcionar ou não encontrar
        mock_sectors = {
            "PETR4.SA": "Petróleo e Gás", "VALE3.SA": "Materiais Básicos", "ITUB4.SA": "Financeiro",
            "BBDC4.SA": "Financeiro", "ABEV3.SA": "Consumo Não Cíclico", "MGLU3.SA": "Consumo Cíclico",
            "WEGE3.SA": "Bens Industriais", "LREN3.SA": "Consumo Cíclico", "RENT3.SA": "Consumo Cíclico",
            "RADL3.SA": "Saúde", "PRIO3.SA": "Petróleo e Gás", "EQTL3.SA": "Utilidades Públicas"
        }
        parsed_ticker = ticker if ticker.upper().endswith(".SA") else ticker.upper() + ".SA"
        return mock_sectors.get(parsed_ticker, "Outros")

    def _prepare_portfolio_data(self):
        """Prepara o DataFrame da carteira, calculando valores atuais e pesos."""
        if self.user_portfolio_df.empty:
            self.user_portfolio_df["ValorAtual"] = 0.0
            self.user_portfolio_df["Peso"] = 0.0
            self.user_portfolio_df["Setor"] = "N/A"
            return

        if "Ticker" in self.user_portfolio_df.columns:
            self.user_portfolio_df["Ticker"] = self.user_portfolio_df["Ticker"].apply(
                lambda x: str(x).upper() + (".SA" if not str(x).upper().endswith(".SA") else "")
            )
            if self.user_portfolio_df.index.name != "Ticker": # Evita setar índice se já for
                try:
                    self.user_portfolio_df.set_index("Ticker", inplace=True)
                except KeyError:
                    print("Aviso: Coluna 'Ticker' não encontrada para definir como índice após processamento.")
                    # Se Ticker não é o índice, não podemos prosseguir com algumas lógicas baseadas nele.
                    # Vamos tentar continuar, mas pode haver erros.
                    pass 

        if self.current_stock_prices is None and self.stock_data_fetcher:
            self.current_stock_prices = pd.Series(dtype=float)
            for ticker_idx in self.user_portfolio_df.index:
                info = self.stock_data_fetcher.get_stock_info(ticker_idx)
                self.current_stock_prices[ticker_idx] = info.get("regularMarketPrice", self.user_portfolio_df.loc[ticker_idx, "PrecoMedio"] if "PrecoMedio" in self.user_portfolio_df.columns else 0)
        elif self.current_stock_prices is None: # Fallback se não há fetcher
             self.current_stock_prices = self.user_portfolio_df["PrecoMedio"].copy() if "PrecoMedio" in self.user_portfolio_df.columns else pd.Series(0.0, index=self.user_portfolio_df.index)

        self.user_portfolio_df["PrecoAtual"] = self.user_portfolio_df.index.map(self.current_stock_prices).fillna(self.user_portfolio_df["PrecoMedio"]) # Usa PrecoMedio se PrecoAtual for NaN
        self.user_portfolio_df["ValorAtual"] = self.user_portfolio_df["Quantidade"] * self.user_portfolio_df["PrecoAtual"]
        
        total_portfolio_value = self.user_portfolio_df["ValorAtual"].sum()
        if total_portfolio_value > 0:
            self.user_portfolio_df["Peso"] = self.user_portfolio_df["ValorAtual"] / total_portfolio_value
        else:
            self.user_portfolio_df["Peso"] = 0

        if "Setor" not in self.user_portfolio_df.columns or self.user_portfolio_df["Setor"].isnull().any():
            self.user_portfolio_df["Setor"] = self.user_portfolio_df.index.map(self._get_sector_for_ticker)
        
        self.user_portfolio_df.reset_index(inplace=True) # Volta Ticker para coluna

    def get_portfolio_summary(self) -> pd.DataFrame:
        """Retorna um resumo da carteira com alocação por setor."""
        if self.user_portfolio_df.empty or "Setor" not in self.user_portfolio_df.columns:
            return pd.DataFrame(columns=["Setor", "ValorTotal", "PesoNoPortfolio"])
            
        sector_allocation = self.user_portfolio_df.groupby("Setor")["ValorAtual"].sum().reset_index()
        sector_allocation.rename(columns={"ValorAtual": "ValorTotal"}, inplace=True)
        total_value = sector_allocation["ValorTotal"].sum()
        if total_value > 0:
            sector_allocation["PesoNoPortfolio"] = sector_allocation["ValorTotal"] / total_value
        else:
            sector_allocation["PesoNoPortfolio"] = 0
        return sector_allocation.sort_values(by="PesoNoPortfolio", ascending=False)

    def analyze_sector_exposure(self) -> pd.DataFrame:
        """Analisa a exposição setorial da carteira em relação aos setores favorecidos pelo cenário macro."""
        portfolio_summary = self.get_portfolio_summary()
        if portfolio_summary.empty:
            return pd.DataFrame(columns=["Setor", "PesoCarteira", "SensibilidadeCenario", "Comentario"])

        _, scenario_sensitivities = self.macro_analyzer.identify_current_scenario()
        analysis_data = []
        all_sectors_in_analysis = set(portfolio_summary["Setor"]).union(set(scenario_sensitivities.keys()))

        for sector in all_sectors_in_analysis:
            peso_carteira = portfolio_summary[portfolio_summary["Setor"] == sector]["PesoNoPortfolio"].sum()
            sensibilidade = scenario_sensitivities.get(sector, "N/A")
            comentario = ""
            if isinstance(sensibilidade, (int, float)):
                if sensibilidade > 0 and peso_carteira < 0.10: comentario = f"Subexposto a setor favorecido (Sens: {sensibilidade}). Aumentar exposição."
                elif sensibilidade > 0 and peso_carteira >= 0.10: comentario = f"Exposição adequada a setor favorecido (Sens: {sensibilidade}). Manter ou aumentar moderadamente."
                elif sensibilidade < 0 and peso_carteira > 0.05: comentario = f"Sobreexposto a setor desfavorecido (Sens: {sensibilidade}). Considerar reduzir."
                elif sensibilidade == 0: comentario = "Sensibilidade neutra ao cenário."
                else: comentario = f"Sensibilidade: {sensibilidade}."
            else: comentario = "Setor não mapeado na análise macro ou sensibilidade N/A."
            analysis_data.append({"Setor": sector, "PesoCarteira": peso_carteira, "SensibilidadeCenario": sensibilidade, "Comentario": comentario})
        return pd.DataFrame(analysis_data).sort_values(by="SensibilidadeCenario", ascending=False)

    def suggest_contributions(self, new_contribution_value: float, max_suggestions: int = 5) -> pd.DataFrame:
        """
        Sugere aportes para rebalancear a carteira e aproveitar oportunidades.

        Args:
            new_contribution_value (float): O valor do novo aporte a ser distribuído.
            max_suggestions (int): Número máximo de sugestões de ativos.

        Returns:
            pd.DataFrame: DataFrame com as sugestões (Ticker, Setor, SugestaoAporte, Justificativa, PrecoAtual, ValuationScore).
        """
        if not self.stock_data_fetcher or not self.valuation_model_class:
            return pd.DataFrame(columns=["Ticker", "Setor", "SugestaoAporte", "Justificativa"], 
                                data=[["N/A", "N/A", 0, "Módulos de dados ou valuation não configurados."]])

        sector_analysis = self.analyze_sector_exposure()
        favored_sectors = sector_analysis[ (sector_analysis["SensibilidadeCenario"] > 0) & 
                                           (sector_analysis["PesoCarteira"] < 0.25) ] # Exemplo: setores favorecidos e com peso < 25%
        favored_sectors = favored_sectors.sort_values(by="SensibilidadeCenario", ascending=False)

        opportunities = []
        # Considerar ativos existentes na carteira e alguns novos potenciais (mock por enquanto)
        # Mock de novos ativos potenciais (idealmente viria de um screener)
        potential_new_tickers_info = [
            {"symbol": "WEGE3.SA", "sector": "Bens Industriais"}, 
            {"symbol": "RENT3.SA", "sector": "Consumo Cíclico"}, 
            {"symbol": "PRIO3.SA", "sector": "Petróleo e Gás"} # Exemplo, pode não ser favorecido
        ]
        
        candidate_tickers = list(self.user_portfolio_df["Ticker"].unique()) # Ativos existentes
        for p_info in potential_new_tickers_info:
            if p_info["symbol"] not in candidate_tickers:
                candidate_tickers.append(p_info["symbol"])
                # Guardar info para usar depois, se o ticker for selecionado
                self.potential_new_investments.append(self.stock_data_fetcher.get_stock_info(p_info["symbol"]))

        for sector_row in favored_sectors.itertuples():
            sector_name = sector_row.Setor
            # Buscar ativos neste setor (existentes e potenciais)
            for ticker in candidate_tickers:
                ticker_sector = self._get_sector_for_ticker(ticker)
                if ticker_sector == sector_name:
                    stock_info = self.stock_data_fetcher.get_stock_info(ticker)
                    if not stock_info or not stock_info.get("regularMarketPrice"):
                        # Se não conseguiu info, tenta pegar dos novos investimentos potenciais (se já buscado)
                        stock_info_cand = next((item for item in self.potential_new_investments if item.get("symbol") == ticker), None)
                        if not stock_info_cand or not stock_info_cand.get("regularMarketPrice"):
                            print(f"Não foi possível obter dados para {ticker}. Pulando valuation.")
                            continue
                        stock_info = stock_info_cand
                    
                    vm = self.valuation_model_class(stock_info_data=stock_info)
                    valuations = vm.get_all_valuations()
                    current_price = stock_info.get("regularMarketPrice")
                    
                    # Score de Valuation (simples)
                    score = 0
                    graham_val = valuations.get("Graham Number")
                    bazin_val = valuations.get("Bazin (Yield 6%)")
                    try: # Graham e Bazin podem ser strings formatadas
                        graham_val_f = float(str(graham_val).replace('%','')) if graham_val else None
                        bazin_val_f = float(str(bazin_val).replace('%','')) if bazin_val else None
                    except ValueError:
                        graham_val_f = None; bazin_val_f = None

                    if graham_val_f and current_price and current_price < graham_val_f: score += 2
                    if bazin_val_f and current_price and current_price < bazin_val_f: score += 1
                    if valuations.get("Múltiplos", {}).get("P/L") and float(valuations["Múltiplos"]["P/L"]) < 15 : score +=1 # Exemplo de P/L baixo
                    if valuations.get("Múltiplos", {}).get("P/VP") and float(valuations["Múltiplos"]["P/VP"]) < 2 : score +=1

                    if score > 1: # Considerar apenas se tiver algum indicativo de bom valuation
                        opportunities.append({
                            "Ticker": ticker,
                            "Setor": sector_name,
                            "PrecoAtual": current_price,
                            "ValuationScore": score,
                            "SensibilidadeSetor": sector_row.SensibilidadeCenario,
                            "PesoAtualCarteiraSetor": sector_row.PesoCarteira,
                            "Justificativa": f"Setor {sector_name} favorecido (Sens: {sector_row.SensibilidadeCenario}). Valuation atrativo (Score: {score})."
                        })
        
        if not opportunities:
            return pd.DataFrame(columns=["Ticker", "Setor", "SugestaoAporte", "Justificativa"], 
                                data=[["N/A", "N/A", 0, "Nenhuma oportunidade clara encontrada com os critérios atuais."]])

        # Ordenar oportunidades: maior sensibilidade do setor, depois maior valuation score, depois menor peso atual no setor
        opportunities_df = pd.DataFrame(opportunities)
        opportunities_df.sort_values(by=["SensibilidadeSetor", "ValuationScore", "PesoAtualCarteiraSetor"], 
                                     ascending=[False, False, True], inplace=True)
        
        top_opportunities = opportunities_df.head(max_suggestions)
        
        # Distribuição simples do aporte (pode ser mais sofisticada)
        # Por enquanto, divide igualmente entre as top N sugestões
        if not top_opportunities.empty:
            aporte_por_sugestao = new_contribution_value / len(top_opportunities)
            top_opportunities["SugestaoAporte"] = aporte_por_sugestao
        else: # Caso raro, se opportunities_df for populado mas top_opportunities ficar vazio
             return pd.DataFrame(columns=["Ticker", "Setor", "SugestaoAporte", "Justificativa"], 
                                data=[["N/A", "N/A", 0, "Nenhuma oportunidade clara encontrada com os critérios atuais."]])

        return top_opportunities[["Ticker", "Setor", "PrecoAtual", "ValuationScore", "SugestaoAporte", "Justificativa"]]

if __name__ == "__main__":
    # Mocks (simplificados para rodar)
    class MockMacroAnalyzer:
        def identify_current_scenario(self, manual_scenario_name=None, **kwargs):
            scenario_name = manual_scenario_name or "Crescimento com Juros Baixos (Simulado)"
            sensitivities = {"Consumo Cíclico": 2, "Tecnologia": 1, "Bens Industriais": 1, "Petróleo e Gás": -1, "Financeiro": 0}
            return scenario_name, sensitivities

    class MockValuationModels:
        def __init__(self, stock_info_data):
            self.stock_info = stock_info_data
        def get_all_valuations(self):
            price = self.stock_info.get("regularMarketPrice", 10)
            graham = price * 1.2 if self.stock_info.get("symbol") != "MGLU3.SA" else price * 0.8
            return {"Ticker": self.stock_info.get("symbol"), "Preço Atual": price, "Graham Number": graham, "Múltiplos": {"P/L": 10, "P/VP": 1.5}}
    
    class MockStockDataFetcher:
        def get_stock_info(self, ticker):
            # Adicionar .SA se não tiver para o mock funcionar
            parsed_ticker = ticker if ticker.upper().endswith(".SA") else ticker.upper() + ".SA"
            mock_data = {
                "PETR4.SA": {"symbol": "PETR4.SA", "regularMarketPrice": 30.0, "sector": "Petróleo e Gás", "trailingEps": 3, "bookValue": 28},
                "VALE3.SA": {"symbol": "VALE3.SA", "regularMarketPrice": 70.0, "sector": "Materiais Básicos", "trailingEps": 7, "bookValue": 40},
                "ITUB4.SA": {"symbol": "ITUB4.SA", "regularMarketPrice": 28.0, "sector": "Financeiro", "trailingEps": 2.5, "bookValue": 20},
                "MGLU3.SA": {"symbol": "MGLU3.SA", "regularMarketPrice": 2.5, "sector": "Consumo Cíclico", "trailingEps": -0.1, "bookValue": 1},
                "WEGE3.SA": {"symbol": "WEGE3.SA", "regularMarketPrice": 35.0, "sector": "Bens Industriais", "trailingEps": 1, "bookValue": 7},
                "RENT3.SA": {"symbol": "RENT3.SA", "regularMarketPrice": 50.0, "sector": "Consumo Cíclico", "trailingEps": 2, "bookValue": 20},
                "PRIO3.SA": {"symbol": "PRIO3.SA", "regularMarketPrice": 45.0, "sector": "Petróleo e Gás", "trailingEps": 5, "bookValue": 25}
            }
            return mock_data.get(parsed_ticker, {"symbol": parsed_ticker, "regularMarketPrice": 0, "sector": "Outros"})

    user_portfolio_data = {
        "Ticker": ["PETR4", "MGLU3"],
        "Quantidade": [100, 500],
        "PrecoMedio": [25.0, 3.0]
    }
    user_pf_df = pd.DataFrame(user_portfolio_data)

    macro_module = MockMacroAnalyzer()
    fetcher_module = MockStockDataFetcher()
    # Passando a classe ValuationModels, não uma instância
    from valuation import ValuationModels # Supondo que valuation.py está no mesmo diretório ou PYTHONPATH

    suggestor_inst = PortfolioSuggestor(
        user_portfolio_df=user_pf_df,
        macro_analyzer=macro_module,
        valuation_model_class=ValuationModels, # Classe ValuationModels real
        stock_data_fetcher=fetcher_module
    )

    print("\n--- Carteira Preparada (Teste Final) ---")
    print(suggestor_inst.user_portfolio_df)
    print("\n--- Análise de Exposição Setorial (Teste Final) ---")
    print(suggestor_inst.analyze_sector_exposure())
    print("\n--- Sugestão de Aportes (R$ 1000) (Teste Final) ---")
    contribution_suggestions = suggestor_inst.suggest_contributions(new_contribution_value=1000.0)
    print(contribution_suggestions)

