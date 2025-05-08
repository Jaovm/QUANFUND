# -*- coding: utf-8 -*-
"""
Módulo para otimização de carteira usando o princípio de Máxima Diversificação.

Uma abordagem simples para máxima diversificação é a carteira de pesos iguais (Equal Weight Portfolio).
Outras abordagens mais complexas podem maximizar o "Diversification Ratio".
Por simplicidade e para oferecer uma alternativa clara aos modelos baseados em covariância,
este módulo implementará a carteira de pesos iguais.
"""

import pandas as pd
import numpy as np
from pypfopt import expected_returns, risk_models

__version__ = "0.0.1"
__author__ = "Manus AI Agent"
__email__ = ""

class MaxDiversificationOptimizer:
    """Classe para otimizar uma carteira visando Máxima Diversificação (via Equal Weight)."""

    def __init__(self, historical_prices: pd.DataFrame):
        """
        Inicializa o otimizador com os preços históricos dos ativos.

        Args:
            historical_prices (pd.DataFrame): DataFrame com preços históricos dos ativos.
                                              As colunas devem ser os tickers e o índice deve ser DatetimeIndex.
        """
        if not isinstance(historical_prices.index, pd.DatetimeIndex):
            try:
                historical_prices.index = pd.to_datetime(historical_prices.index)
            except Exception as e:
                raise ValueError(f"Não foi possível converter o índice de historical_prices para DatetimeIndex: {e}")
        
        self.historical_prices = historical_prices
        self.tickers = historical_prices.columns.tolist()

    def optimize_equal_weight(self) -> tuple[dict | None, pd.Series | None]:
        """
        Calcula os pesos para uma carteira de Máxima Diversificação (Equal Weight).

        Returns:
            tuple[dict | None, pd.Series | None]: Pesos otimizados (iguais) e performance esperada.
                                                  Retorna (None, None) em caso de erro.
        """
        if not self.tickers:
            print("Erro: Nenhum ticker fornecido para otimização de igual peso.")
            return None, None

        num_assets = len(self.tickers)
        if num_assets == 0:
            return {}, pd.Series(dtype=float, name="Performance Esperada (Equal Weight)")

        weight = 1 / num_assets
        weights = {ticker: weight for ticker in self.tickers}

        try:
            # Calcular performance esperada para a carteira de pesos iguais
            mu = expected_returns.mean_historical_return(self.historical_prices)
            S = risk_models.CovarianceShrinkage(self.historical_prices).ledoit_wolf()
            
            # Convert weights dict to a pandas Series with the same order as mu and S
            weights_series = pd.Series(weights, index=self.tickers)
            # Reindex to match mu and S columns, filling missing with 0 (should not happen if tickers is from historical_prices.columns)
            weights_series = weights_series.reindex(mu.index).fillna(0)

            expected_annual_return = np.sum(mu * weights_series)
            portfolio_volatility = np.sqrt(np.dot(weights_series.T, np.dot(S, weights_series)))
            sharpe_ratio = expected_annual_return / portfolio_volatility # Assuming risk_free_rate = 0 for simplicity here, or use a passed one
            # For a more accurate Sharpe, use (expected_annual_return - risk_free_rate) / portfolio_volatility
            # risk_free_rate = 0.02 # Example
            # sharpe_ratio = (expected_annual_return - risk_free_rate) / portfolio_volatility

            perf_series = pd.Series({
                "Retorno Esperado Anualizado": expected_annual_return,
                "Volatilidade Anualizada": portfolio_volatility,
                "Índice de Sharpe (Aproximado)": sharpe_ratio
            }, name="Performance Esperada (Equal Weight)")
            
            return weights, perf_series
        except Exception as e:
            print(f"Erro ao calcular performance para carteira Equal Weight: {e}")
            return weights, None # Retorna pesos, mas sem performance se o cálculo falhar

if __name__ == "__main__":
    print("Executando exemplos locais para MaxDiversificationOptimizer (Equal Weight)...")
    # Gerar dados de preços históricos fictícios
    tickers_md = ["Stock1", "Stock2", "Stock3", "Stock4", "Stock5"]
    date_rng_md = pd.date_range(start="2020-01-01", end="2023-12-31", freq="B")
    np.random.seed(777)
    prices_data_md = {}
    for ticker in tickers_md:
        prices_data_md[ticker] = 100 + np.random.randn(len(date_rng_md)).cumsum() * 0.15 + np.random.rand() * 15
    
    prices_df_md = pd.DataFrame(prices_data_md, index=date_rng_md)
    prices_df_md = prices_df_md.clip(lower=1) # Evitar preços negativos ou zero

    print("\nPreços Históricos para Máxima Diversificação (head):")
    print(prices_df_md.head())

    md_optimizer = MaxDiversificationOptimizer(historical_prices=prices_df_md)

    print("\n--- Otimização para Máxima Diversificação (Equal Weight) ---")
    weights_md, perf_md = md_optimizer.optimize_equal_weight()
    if weights_md:
        print("Pesos Otimizados (Equal Weight):")
        for ticker, weight in weights_md.items():
            print(f"  {ticker}: {weight:.4f}")
        if perf_md is not None:
            print("\nPerformance Esperada (Equal Weight):")
            print(perf_md)
        else:
            print("\nPerformance não pôde ser calculada.")
    else:
        print("Falha na otimização de Máxima Diversificação (Equal Weight).")

    # Teste com DataFrame vazio
    print("\n--- Teste Máxima Diversificação com DataFrame Vazio ---")
    empty_md_optimizer = MaxDiversificationOptimizer(pd.DataFrame(index=pd.to_datetime([]), columns=tickers_md))
    w_empty_md, p_empty_md = empty_md_optimizer.optimize_equal_weight()
    # Este teste precisa ser ajustado, pois self.tickers será populado com colunas vazias.
    # Se o DataFrame de preços estiver vazio, mu e S não podem ser calculados.
    # O construtor já lida com o índice, mas o cálculo de mu/S falhará.
    # A lógica atual de optimize_equal_weight retornará pesos, mas a performance falhará.
    if w_empty_md is not None and p_empty_md is None:
         print("Otimização de Máxima Diversificação (Equal Weight) com dados vazios retornou pesos, mas performance falhou como esperado.")
         print(f"Pesos: {w_empty_md}")
    elif not w_empty_md:
        print("Otimização de Máxima Diversificação (Equal Weight) com dados vazios falhou como esperado.")

    print("\n--- Teste Máxima Diversificação com DataFrame com uma única ação ---")
    single_stock_df = prices_df_md[["Stock1"]]
    single_md_optimizer = MaxDiversificationOptimizer(historical_prices=single_stock_df)
    weights_single_md, perf_single_md = single_md_optimizer.optimize_equal_weight()
    if weights_single_md:
        print("Pesos Otimizados (Equal Weight - 1 ativo):")
        for ticker, weight in weights_single_md.items():
            print(f"  {ticker}: {weight:.4f}") # Deve ser 1.0000
        if perf_single_md is not None:
            print("\nPerformance Esperada (Equal Weight - 1 ativo):")
            print(perf_single_md)

