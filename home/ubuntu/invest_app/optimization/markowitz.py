# -*- coding: utf-8 -*-
"""
Módulo para otimização de carteira usando o modelo da Fronteira Eficiente de Markowitz.

Utiliza a biblioteca PyPortfolioOpt para os cálculos.
"""

import pandas as pd
import numpy as np
from pypfopt import EfficientFrontier, risk_models, expected_returns
from pypfopt.exceptions import OptimizationError

__version__ = "0.0.1"
__author__ = "Manus AI Agent"
__email__ = ""

class MarkowitzOptimizer:
    """Classe para otimizar uma carteira usando a Fronteira Eficiente de Markowitz."""

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
        self.mu = None
        self.S = None
        self._calculate_mu_S()

    def _calculate_mu_S(self):
        """Calcula o retorno esperado (mu) e a matriz de covariância (S)."""
        if self.historical_prices.empty:
            self.mu = pd.Series(dtype=float)
            self.S = pd.DataFrame()
            return

        # Retornos logarítmicos são geralmente preferidos para modelagem financeira
        # log_returns = np.log(self.historical_prices / self.historical_prices.shift(1))
        # self.mu = expected_returns.mean_historical_return(self.historical_prices, returns_data=False, compounding=True, frequency=252)
        # self.S = risk_models.sample_cov(self.historical_prices, returns_data=False, frequency=252)
        
        # Usando retornos simples para consistência com outras partes do PyPortfolioOpt e exemplos comuns
        self.mu = expected_returns.mean_historical_return(self.historical_prices)
        self.S = risk_models.CovarianceShrinkage(self.historical_prices).ledoit_wolf()
        # Alternativas para S:
        # self.S = risk_models.sample_cov(self.historical_prices)
        # self.S = risk_models.exp_cov(self.historical_prices)

    def optimize_for_max_sharpe(self, risk_free_rate: float = 0.02) -> tuple[dict | None, pd.Series | None]:
        """
        Otimiza a carteira para o máximo Índice de Sharpe.

        Args:
            risk_free_rate (float): Taxa livre de risco anualizada.

        Returns:
            tuple[dict | None, pd.Series | None]: Pesos otimizados e performance esperada (retorno, volatilidade, Sharpe).
                                                  Retorna (None, None) em caso de erro.
        """
        if self.mu is None or self.S is None or self.mu.empty or self.S.empty:
            print("Erro: Retornos esperados (mu) ou matriz de covariância (S) não calculados.")
            return None, None
        
        ef = EfficientFrontier(self.mu, self.S)
        try:
            weights = ef.max_sharpe(risk_free_rate=risk_free_rate)
            cleaned_weights = ef.clean_weights()
            performance = ef.portfolio_performance(verbose=False, risk_free_rate=risk_free_rate)
            
            perf_series = pd.Series({
                "Retorno Esperado Anualizado": performance[0],
                "Volatilidade Anualizada": performance[1],
                "Índice de Sharpe": performance[2]
            }, name="Performance Esperada (Max Sharpe)")
            return cleaned_weights, perf_series
        except OptimizationError as e:
            print(f"Erro de otimização (Max Sharpe): {e}")
            return None, None
        except ValueError as e:
            print(f"Erro de valor nos dados de entrada (Max Sharpe): {e}")
            return None, None

    def optimize_for_min_volatility(self) -> tuple[dict | None, pd.Series | None]:
        """
        Otimiza a carteira para a mínima volatilidade.

        Returns:
            tuple[dict | None, pd.Series | None]: Pesos otimizados e performance esperada.
                                                  Retorna (None, None) em caso de erro.
        """
        if self.mu is None or self.S is None or self.mu.empty or self.S.empty:
            print("Erro: Retornos esperados (mu) ou matriz de covariância (S) não calculados.")
            return None, None

        ef = EfficientFrontier(self.mu, self.S)
        try:
            weights = ef.min_volatility()
            cleaned_weights = ef.clean_weights()
            performance = ef.portfolio_performance(verbose=False)
            
            perf_series = pd.Series({
                "Retorno Esperado Anualizado": performance[0],
                "Volatilidade Anualizada": performance[1],
                "Índice de Sharpe": performance[2]
            }, name="Performance Esperada (Min Volatilidade)")
            return cleaned_weights, perf_series
        except OptimizationError as e:
            print(f"Erro de otimização (Min Volatilidade): {e}")
            return None, None
        except ValueError as e:
            print(f"Erro de valor nos dados de entrada (Min Volatilidade): {e}")
            return None, None

    def optimize_for_target_return(self, target_return: float) -> tuple[dict | None, pd.Series | None]:
        """
        Otimiza a carteira para um dado retorno alvo, minimizando a volatilidade.

        Args:
            target_return (float): O retorno anualizado alvo (ex: 0.20 para 20%).

        Returns:
            tuple[dict | None, pd.Series | None]: Pesos otimizados e performance esperada.
                                                  Retorna (None, None) em caso de erro.
        """
        if self.mu is None or self.S is None or self.mu.empty or self.S.empty:
            print("Erro: Retornos esperados (mu) ou matriz de covariância (S) não calculados.")
            return None, None

        ef = EfficientFrontier(self.mu, self.S)
        try:
            weights = ef.efficient_return(target_return=target_return)
            cleaned_weights = ef.clean_weights()
            performance = ef.portfolio_performance(verbose=False)
            
            perf_series = pd.Series({
                "Retorno Esperado Anualizado": performance[0],
                "Volatilidade Anualizada": performance[1],
                "Índice de Sharpe": performance[2]
            }, name=f"Performance Esperada (Retorno Alvo: {target_return*100:.1f}%)")
            return cleaned_weights, perf_series
        except OptimizationError as e:
            print(f"Erro de otimização (Retorno Alvo {target_return}): {e}")
            return None, None
        except ValueError as e:
            print(f"Erro de valor nos dados de entrada (Retorno Alvo {target_return}): {e}")
            return None, None

if __name__ == "__main__":
    print("Executando exemplos locais para MarkowitzOptimizer...")
    # Gerar dados de preços históricos fictícios
    tickers = ["AcaoA", "AcaoB", "AcaoC", "AcaoD"]
    date_rng = pd.date_range(start="2020-01-01", end="2023-12-31", freq="B")
    np.random.seed(42)
    prices_data = {}
    for ticker in tickers:
        prices_data[ticker] = 100 + np.random.randn(len(date_rng)).cumsum() * 0.2 + np.random.rand() * 20
    
    prices_df = pd.DataFrame(prices_data, index=date_rng)
    prices_df = prices_df.clip(lower=1) # Evitar preços negativos ou zero

    print("\nPreços Históricos (head):")
    print(prices_df.head())

    optimizer = MarkowitzOptimizer(historical_prices=prices_df)

    print("\n--- Otimização para Máximo Sharpe Ratio ---")
    weights_sharpe, perf_sharpe = optimizer.optimize_for_max_sharpe(risk_free_rate=0.01)
    if weights_sharpe:
        print("Pesos Otimizados:")
        for ticker, weight in weights_sharpe.items():
            if weight > 1e-4: # Mostrar apenas pesos significativos
                print(f"  {ticker}: {weight:.4f}")
        print("\nPerformance Esperada:")
        print(perf_sharpe)

    print("\n--- Otimização para Mínima Volatilidade ---")
    weights_min_vol, perf_min_vol = optimizer.optimize_for_min_volatility()
    if weights_min_vol:
        print("Pesos Otimizados:")
        for ticker, weight in weights_min_vol.items():
            if weight > 1e-4:
                print(f"  {ticker}: {weight:.4f}")
        print("\nPerformance Esperada:")
        print(perf_min_vol)

    target_ret = 0.15 # 15% de retorno alvo
    print(f"\n--- Otimização para Retorno Alvo de {target_ret*100:.0f}% ---")
    weights_target_ret, perf_target_ret = optimizer.optimize_for_target_return(target_return=target_ret)
    if weights_target_ret:
        print("Pesos Otimizados:")
        for ticker, weight in weights_target_ret.items():
            if weight > 1e-4:
                print(f"  {ticker}: {weight:.4f}")
        print("\nPerformance Esperada:")
        print(perf_target_ret)
    
    # Teste com dados vazios ou insuficientes
    print("\n--- Teste com DataFrame Vazio ---")
    empty_optimizer = MarkowitzOptimizer(pd.DataFrame(index=pd.to_datetime([])))
    w_empty, p_empty = empty_optimizer.optimize_for_max_sharpe()
    if w_empty is None:
        print("Otimização com dados vazios falhou como esperado.")

