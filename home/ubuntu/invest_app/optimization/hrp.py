# -*- coding: utf-8 -*-
"""
Módulo para otimização de carteira usando o modelo Hierarchical Risk Parity (HRP).

Utiliza a biblioteca PyPortfolioOpt para os cálculos.
"""

import pandas as pd
import numpy as np
from pypfopt import HRPOpt
from pypfopt import CovarianceShrinkage # Para calcular a matriz de covariância de forma robusta
from pypfopt.exceptions import OptimizationError

__version__ = "0.0.1"
__author__ = "Manus AI Agent"
__email__ = ""

class HRPOptimizer:
    """Classe para otimizar uma carteira usando o modelo Hierarchical Risk Parity (HRP)."""

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
        self.returns = self.historical_prices.pct_change().dropna()
        self.S_hrp = None # Matriz de covariância para HRP
        self._calculate_S_hrp()

    def _calculate_S_hrp(self):
        """Calcula a matriz de covariância para HRP."""
        if self.returns.empty:
            self.S_hrp = pd.DataFrame()
            return
        # HRP usa a matriz de covariância dos retornos
        self.S_hrp = CovarianceShrinkage(self.historical_prices).ledoit_wolf()
        # Alternativamente, poderia ser a covariância simples dos retornos:
        # self.S_hrp = self.returns.cov()

    def optimize(self) -> tuple[dict | None, pd.Series | None]:
        """
        Otimiza a carteira usando HRP.

        Returns:
            tuple[dict | None, pd.Series | None]: Pesos otimizados e performance esperada (se calculável).
                                                  HRP não otimiza para um Sharpe específico, então a performance
                                                  aqui seria baseada nos pesos e retornos históricos.
                                                  Retorna (None, None) em caso de erro.
        """
        if self.returns.empty or self.S_hrp is None or self.S_hrp.empty:
            print("Erro: Retornos ou matriz de covariância não calculados para HRP.")
            return None, None

        hrp = HRPOpt(returns=self.returns, cov_matrix=self.S_hrp)
        try:
            weights = hrp.optimize()
            cleaned_weights = hrp.clean_weights()
            
            # HRP não tem um "portfolio_performance" como EfficientFrontier que retorna Sharpe etc.
            # Podemos calcular o retorno e volatilidade esperados da carteira HRP usando os pesos.
            # Para isso, precisamos dos retornos esperados (mu) como no Markowitz.
            # No entanto, HRP é um modelo focado em risco e diversificação, não em maximizar retorno esperado.
            # Por simplicidade, retornaremos apenas os pesos por enquanto.
            # A performance pode ser avaliada em um backtest.
            
            # Se quisermos uma estimativa de performance, podemos usar o mu histórico:
            from pypfopt import expected_returns as pypfopt_er
            mu_hist = pypfopt_er.mean_historical_return(self.historical_prices)
            
            expected_annual_return = np.sum(mu_hist * pd.Series(cleaned_weights))
            # Calcular volatilidade da carteira HRP
            # portfolio_volatility = np.sqrt(np.dot(pd.Series(cleaned_weights).T, np.dot(self.S_hrp, pd.Series(cleaned_weights)))) * np.sqrt(252) # Anualizada
            # A função portfolio_performance do HRPOpt faz isso:
            perf = hrp.portfolio_performance(verbose=False, risk_free_rate=0.02) # rf apenas para Sharpe, se calculado

            perf_series = pd.Series({
                "Retorno Esperado Anualizado (Histórico)": perf[0],
                "Volatilidade Anualizada": perf[1],
                "Índice de Sharpe (Histórico)": perf[2] # Baseado no mu histórico
            }, name="Performance Estimada (HRP)")
            
            return cleaned_weights, perf_series
        except OptimizationError as e:
            print(f"Erro de otimização (HRP): {e}")
            return None, None
        except Exception as e: # Captura outras exceções como ValueError de dados ruins
            print(f"Erro inesperado durante otimização HRP: {e}")
            return None, None

if __name__ == "__main__":
    print("Executando exemplos locais para HRPOptimizer...")
    # Gerar dados de preços históricos fictícios
    tickers_hrp = ["AtivoX", "AtivoY", "AtivoZ", "AtivoW"]
    date_rng_hrp = pd.date_range(start="2019-01-01", end="2023-12-31", freq="B")
    np.random.seed(123)
    prices_data_hrp = {}
    for ticker in tickers_hrp:
        prices_data_hrp[ticker] = 50 + np.random.randn(len(date_rng_hrp)).cumsum() * 0.3 + np.random.rand() * 10
    
    prices_df_hrp = pd.DataFrame(prices_data_hrp, index=date_rng_hrp)
    prices_df_hrp = prices_df_hrp.clip(lower=0.5) # Evitar preços negativos ou zero

    print("\nPreços Históricos para HRP (head):")
    print(prices_df_hrp.head())

    hrp_optimizer = HRPOptimizer(historical_prices=prices_df_hrp)

    print("\n--- Otimização usando Hierarchical Risk Parity (HRP) ---")
    weights_hrp, perf_hrp = hrp_optimizer.optimize()
    if weights_hrp:
        print("Pesos Otimizados (HRP):")
        for ticker, weight in weights_hrp.items():
            if weight > 1e-5: # Mostrar apenas pesos significativos
                print(f"  {ticker}: {weight:.4f}")
        print("\nPerformance Estimada (HRP - baseada em dados históricos):")
        print(perf_hrp)
    else:
        print("Falha na otimização HRP.")

    # Teste com dados que podem causar problemas (ex: poucas observações)
    print("\n--- Teste HRP com dados curtos ---")
    short_prices_df = prices_df_hrp.tail(20) # Apenas 20 dias de dados
    short_hrp_optimizer = HRPOptimizer(historical_prices=short_prices_df)
    weights_short_hrp, perf_short_hrp = short_hrp_optimizer.optimize()
    if weights_short_hrp:
        print("Pesos Otimizados (HRP - dados curtos):")
        for ticker, weight in weights_short_hrp.items():
            if weight > 1e-5:
                print(f"  {ticker}: {weight:.4f}")
        print("\nPerformance Estimada (HRP - dados curtos):")
        print(perf_short_hrp)
    else:
        print("Falha na otimização HRP com dados curtos.")

    # Teste com DataFrame vazio
    print("\n--- Teste HRP com DataFrame Vazio ---")
    empty_hrp_optimizer = HRPOptimizer(pd.DataFrame(index=pd.to_datetime([])))
    w_empty_hrp, p_empty_hrp = empty_hrp_optimizer.optimize()
    if w_empty_hrp is None:
        print("Otimização HRP com dados vazios falhou como esperado.")

