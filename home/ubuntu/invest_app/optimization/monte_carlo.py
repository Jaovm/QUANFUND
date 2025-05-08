# -*- coding: utf-8 -*-
"""
Módulo para otimização de carteira usando Simulação de Monte Carlo.

A Simulação de Monte Carlo para otimização de portfólio envolve gerar um grande
número de carteiras com pesos aleatórios para os ativos e, em seguida, calcular
o retorno esperado e a volatilidade para cada uma dessas carteiras. Isso permite
visualizar a fronteira eficiente e identificar carteiras com características desejadas
(ex: maior Sharpe Ratio, menor volatilidade para um dado retorno, etc.).
"""

import pandas as pd
import numpy as np
from pypfopt import expected_returns, risk_models

__version__ = "0.0.1"
__author__ = "Manus AI Agent"
__email__ = ""

class MonteCarloOptimizer:
    """Classe para otimizar uma carteira usando Simulação de Monte Carlo."""

    def __init__(self, historical_prices: pd.DataFrame, num_portfolios: int = 10000):
        """
        Inicializa o otimizador com os preços históricos dos ativos.

        Args:
            historical_prices (pd.DataFrame): DataFrame com preços históricos dos ativos.
                                              As colunas devem ser os tickers e o índice deve ser DatetimeIndex.
            num_portfolios (int): Número de carteiras aleatórias a serem geradas na simulação.
        """
        if not isinstance(historical_prices.index, pd.DatetimeIndex):
            try:
                historical_prices.index = pd.to_datetime(historical_prices.index)
            except Exception as e:
                raise ValueError(f"Não foi possível converter o índice de historical_prices para DatetimeIndex: {e}")
        
        self.historical_prices = historical_prices
        self.tickers = historical_prices.columns.tolist()
        self.num_portfolios = num_portfolios
        self.mu = None
        self.S = None
        self._calculate_mu_S()
        self.results_df = None

    def _calculate_mu_S(self):
        """Calcula o retorno esperado (mu) e a matriz de covariância (S)."""
        if self.historical_prices.empty or len(self.historical_prices) < 2:
            self.mu = pd.Series(dtype=float)
            self.S = pd.DataFrame()
            print("Dados históricos insuficientes para calcular mu e S.")
            return

        self.mu = expected_returns.mean_historical_return(self.historical_prices)
        self.S = risk_models.CovarianceShrinkage(self.historical_prices).ledoit_wolf()

    def run_simulation(self, risk_free_rate: float = 0.02) -> pd.DataFrame | None:
        """
        Executa a Simulação de Monte Carlo para gerar e avaliar carteiras aleatórias.

        Args:
            risk_free_rate (float): Taxa livre de risco anualizada para cálculo do Sharpe Ratio.

        Returns:
            pd.DataFrame | None: DataFrame com os resultados de cada carteira simulada
                                 (retorno, volatilidade, Sharpe Ratio, e pesos dos ativos).
                                 Retorna None se mu ou S não puderam ser calculados.
        """
        if self.mu is None or self.S is None or self.mu.empty or self.S.empty:
            print("Erro: Retornos esperados (mu) ou matriz de covariância (S) não calculados. Simulação não pode prosseguir.")
            return None
        if not self.tickers:
            print("Erro: Nenhum ticker disponível para simulação.")
            return None

        num_assets = len(self.tickers)
        results_array = np.zeros((3 + num_assets, self.num_portfolios)) # 3 para Ret, Vol, Sharpe

        for i in range(self.num_portfolios):
            # Gerar pesos aleatórios
            weights = np.random.random(num_assets)
            weights /= np.sum(weights) # Normalizar para que a soma seja 1
            
            # Calcular retorno, volatilidade e Sharpe da carteira
            portfolio_return = np.sum(self.mu * weights)
            portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(self.S, weights)))
            sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_volatility
            
            # Armazenar resultados
            results_array[0, i] = portfolio_return
            results_array[1, i] = portfolio_volatility
            results_array[2, i] = sharpe_ratio
            for j in range(num_assets):
                results_array[3+j, i] = weights[j]
        
        columns = ["Retorno", "Volatilidade", "SharpeRatio"] + self.tickers
        self.results_df = pd.DataFrame(results_array.T, columns=columns)
        return self.results_df

    def get_optimal_portfolio(self, metric: str = "SharpeRatio") -> tuple[dict | None, pd.Series | None]:
        """
        Retorna a carteira ótima da simulação com base em uma métrica.

        Args:
            metric (str): Métrica para otimização ("SharpeRatio" ou "Volatilidade").
                          Se "Volatilidade", busca a menor volatilidade.

        Returns:
            tuple[dict | None, pd.Series | None]: Pesos da carteira ótima e sua performance.
                                                  Retorna (None, None) se a simulação não foi executada.
        """
        if self.results_df is None or self.results_df.empty:
            print("Simulação de Monte Carlo não foi executada ou não gerou resultados. Execute run_simulation() primeiro.")
            return None, None

        if metric == "SharpeRatio":
            optimal_portfolio_row = self.results_df.iloc[self.results_df["SharpeRatio"].idxmax()]
        elif metric == "Volatilidade":
            optimal_portfolio_row = self.results_df.iloc[self.results_df["Volatilidade"].idxmin()]
        else:
            print("Métrica {metric} não suportada. Use 'SharpeRatio' ou 'Volatilidade'.")
            return None, None

        weights = optimal_portfolio_row[self.tickers].to_dict()
        performance = pd.Series({
            "Retorno Esperado Anualizado": optimal_portfolio_row["Retorno"],
            "Volatilidade Anualizada": optimal_portfolio_row["Volatilidade"],
            "Índice de Sharpe": optimal_portfolio_row["SharpeRatio"]
        }, name=f"Performance (Monte Carlo - Otimizado para {metric})")
        
        return weights, performance

if __name__ == "__main__":
    print("Executando exemplos locais para MonteCarloOptimizer...")
    # Gerar dados de preços históricos fictícios
    tickers_mc = ["TSLA", "MSFT", "GOOG", "AMZN"]
    date_rng_mc = pd.date_range(start="2020-01-01", end="2023-12-31", freq="B")
    np.random.seed(4242)
    prices_data_mc = {}
    for ticker in tickers_mc:
        prices_data_mc[ticker] = 200 + np.random.randn(len(date_rng_mc)).cumsum() * 0.5 + np.random.rand() * 50
    
    prices_df_mc = pd.DataFrame(prices_data_mc, index=date_rng_mc)
    prices_df_mc = prices_df_mc.clip(lower=10) # Evitar preços muito baixos

    print("\nPreços Históricos para Monte Carlo (head):")
    print(prices_df_mc.head())

    mc_optimizer = MonteCarloOptimizer(historical_prices=prices_df_mc, num_portfolios=5000) # Reduzido para teste rápido
    
    print("\n--- Executando Simulação de Monte Carlo ---")
    simulation_results = mc_optimizer.run_simulation(risk_free_rate=0.015)
    if simulation_results is not None:
        print(f"Simulação concluída. {len(simulation_results)} carteiras geradas.")
        print("Resultados da Simulação (primeiras 5 carteiras):")
        print(simulation_results.head())

        print("\n--- Carteira Ótima (Máximo Sharpe Ratio) da Simulação ---")
        weights_sharpe_mc, perf_sharpe_mc = mc_optimizer.get_optimal_portfolio(metric="SharpeRatio")
        if weights_sharpe_mc:
            print("Pesos Otimizados:")
            for ticker, weight in weights_sharpe_mc.items():
                print(f"  {ticker}: {weight:.4f}")
            print("\nPerformance Esperada:")
            print(perf_sharpe_mc)

        print("\n--- Carteira Ótima (Mínima Volatilidade) da Simulação ---")
        weights_vol_mc, perf_vol_mc = mc_optimizer.get_optimal_portfolio(metric="Volatilidade")
        if weights_vol_mc:
            print("Pesos Otimizados:")
            for ticker, weight in weights_vol_mc.items():
                print(f"  {ticker}: {weight:.4f}")
            print("\nPerformance Esperada:")
            print(perf_vol_mc)
    else:
        print("Falha na execução da Simulação de Monte Carlo.")

    # Teste com dados insuficientes
    print("\n--- Teste Monte Carlo com dados muito curtos ---")
    short_prices_df_mc = prices_df_mc.tail(5) # Apenas 5 dias de dados
    short_mc_optimizer = MonteCarloOptimizer(historical_prices=short_prices_df_mc)
    short_sim_results = short_mc_optimizer.run_simulation()
    if short_sim_results is None:
        print("Simulação com dados curtos falhou como esperado (mu/S não calculados).")
    
    # Opcional: Plotar a fronteira eficiente (requer matplotlib)
    # import matplotlib.pyplot as plt
    # if simulation_results is not None:
    #     plt.figure(figsize=(10, 6))
    #     plt.scatter(simulation_results["Volatilidade"], simulation_results["Retorno"], c=simulation_results["SharpeRatio"], cmap="viridis", marker='o', s=10, alpha=0.7)
    #     plt.colorbar(label="Sharpe Ratio")
    #     plt.title("Fronteira Eficiente - Simulação de Monte Carlo")
    #     plt.xlabel("Volatilidade (Risco)")
    #     plt.ylabel("Retorno Esperado")
        # Marcar a carteira de máximo Sharpe
    #     if perf_sharpe_mc is not None:
    #         plt.scatter(perf_sharpe_mc["Volatilidade Anualizada"], perf_sharpe_mc["Retorno Esperado Anualizado"], marker="*", color="red", s=200, label="Máximo Sharpe Ratio")
        # Marcar a carteira de mínima volatilidade
    #     if perf_vol_mc is not None:
    #         plt.scatter(perf_vol_mc["Volatilidade Anualizada"], perf_vol_mc["Retorno Esperado Anualizado"], marker="X", color="blue", s=200, label="Mínima Volatilidade")
    #     plt.legend()
    #     plt.grid(True)
    #     # plt.show() # Descomente para mostrar o gráfico se estiver rodando localmente com GUI
    #     plt.savefig("/home/ubuntu/monte_carlo_frontier.png")
    #     print("\nGráfico da fronteira eficiente salvo em /home/ubuntu/monte_carlo_frontier.png")

