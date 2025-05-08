# -*- coding: utf-8 -*-
"""
Módulo para realizar backtesting de carteiras de investimento.

Funcionalidades:
- Calcular o desempenho histórico de uma carteira.
- Comparar com benchmarks (ex: IBOV).
- Gerar métricas de risco e retorno (Sharpe, Sortino, Drawdown Máximo, etc.).
- Visualizar resultados através de gráficos (preparar dados para Streamlit).
"""

import pandas as pd
import numpy as np
import quantstats as qs
from datetime import datetime

__version__ = "0.0.1"
__author__ = "Manus AI Agent"
__email__ = ""

class Backtester:
    """Classe para realizar o backtesting de uma estratégia ou carteira."""

    def __init__(self, 
                 portfolio_values: pd.Series = None, 
                 portfolio_returns: pd.Series = None, 
                 benchmark_returns: pd.Series = None, 
                 start_date: str | datetime = "2015-01-01", 
                 end_date: str | datetime = None,
                 initial_capital: float = 100000.0):
        """
        Inicializa o Backtester.

        Args:
            portfolio_values (pd.Series, optional): Série com os valores diários/periódicos da carteira.
                                                 Índice deve ser DatetimeIndex.
            portfolio_returns (pd.Series, optional): Série com os retornos diários/periódicos da carteira.
                                                   Índice deve ser DatetimeIndex. Usado se portfolio_values não for fornecido.
            benchmark_returns (pd.Series, optional): Série com os retornos diários/periódicos do benchmark.
                                                   Índice deve ser DatetimeIndex.
            start_date (str | datetime): Data de início do backtest. Formato "YYYY-MM-DD" ou objeto datetime.
            end_date (str | datetime, optional): Data de fim do backtest. Formato "YYYY-MM-DD" ou objeto datetime.
                                                 Se None, usa a última data disponível.
            initial_capital (float): Capital inicial para calcular a curva de capital a partir dos retornos.
        """
        if portfolio_values is None and portfolio_returns is None:
            raise ValueError("É necessário fornecer `portfolio_values` ou `portfolio_returns`.")

        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date) if end_date else None
        self.initial_capital = initial_capital

        if portfolio_values is not None:
            if not isinstance(portfolio_values.index, pd.DatetimeIndex):
                portfolio_values.index = pd.to_datetime(portfolio_values.index)
            self.portfolio_values = portfolio_values.sort_index()
            self.portfolio_returns = self.portfolio_values.pct_change().fillna(0)
        else: # portfolio_returns is not None
            if not isinstance(portfolio_returns.index, pd.DatetimeIndex):
                portfolio_returns.index = pd.to_datetime(portfolio_returns.index)
            self.portfolio_returns = portfolio_returns.sort_index().fillna(0)
            # Calcular valores da carteira a partir dos retornos e capital inicial
            self.portfolio_values = (1 + self.portfolio_returns).cumprod() * self.initial_capital
            # Adicionar o capital inicial no primeiro dia
            first_day_value = pd.Series([self.initial_capital], index=[self.portfolio_returns.index[0] - pd.Timedelta(days=1)])
            if not isinstance(first_day_value.index, pd.DatetimeIndex):
                 first_day_value.index = pd.to_datetime(first_day_value.index)
            self.portfolio_values = pd.concat([first_day_value, self.portfolio_values]).sort_index()
            self.portfolio_values.iloc[0] = self.initial_capital # Garante o valor inicial correto
            self.portfolio_returns.iloc[0] = 0 # Retorno no primeiro dia é 0

        # Filtrar por data
        self.portfolio_returns = self.portfolio_returns[self.portfolio_returns.index >= self.start_date]
        self.portfolio_values = self.portfolio_values[self.portfolio_values.index >= self.start_date]
        if self.end_date:
            self.portfolio_returns = self.portfolio_returns[self.portfolio_returns.index <= self.end_date]
            self.portfolio_values = self.portfolio_values[self.portfolio_values.index <= self.end_date]

        self.benchmark_returns = None
        if benchmark_returns is not None:
            if not isinstance(benchmark_returns.index, pd.DatetimeIndex):
                benchmark_returns.index = pd.to_datetime(benchmark_returns.index)
            self.benchmark_returns = benchmark_returns.sort_index().fillna(0)
            self.benchmark_returns = self.benchmark_returns[self.benchmark_returns.index >= self.start_date]
            if self.end_date:
                self.benchmark_returns = self.benchmark_returns[self.benchmark_returns.index <= self.end_date]
            
            # Alinhar datas com os retornos da carteira
            common_index = self.portfolio_returns.index.intersection(self.benchmark_returns.index)
            self.portfolio_returns = self.portfolio_returns.loc[common_index]
            self.portfolio_values = self.portfolio_values.loc[common_index]
            self.benchmark_returns = self.benchmark_returns.loc[common_index]

        # Configurar quantstats para usar retornos em vez de preços para algumas funções
        qs.utils.download_data = lambda _ : _ # Evita downloads
        qs.utils.daily_returns = lambda x: x # Passa os retornos diretamente

    def get_performance_summary(self, risk_free_rate: float = 0.0) -> pd.Series:
        """
        Calcula um resumo das principais métricas de desempenho usando quantstats.

        Args:
            risk_free_rate (float): Taxa livre de risco anualizada para cálculo do Sharpe Ratio, etc.
                                    O quantstats espera a taxa diária, então converteremos.
                                    Se 0, o Sharpe pode ser calculado como Retorno/Vol.

        Returns:
            pd.Series: Série com as métricas de desempenho.
        """
        if self.portfolio_returns.empty:
            return pd.Series(dtype=float, name="Métricas")

        # quantstats espera retornos diários para algumas métricas anuais. 
        # Se os retornos já são diários, ok. Se não, as métricas anuais podem precisar de ajuste.
        # Para simplificar, assumimos que os retornos são da frequência correta para as métricas.
        
        metrics = pd.Series(dtype='object')
        metrics["Período Analisado"] = f"{self.portfolio_returns.index.min().strftime('%Y-%m-%d')} a {self.portfolio_returns.index.max().strftime('%Y-%m-%d')}"
        metrics["Capital Inicial"] = self.initial_capital
        metrics["Capital Final"] = self.portfolio_values.iloc[-1]
        metrics["Retorno Total"] = (self.portfolio_values.iloc[-1] / self.initial_capital) - 1
        
        # Métricas do QuantStats
        metrics["CAGR"] = qs.stats.cagr(self.portfolio_returns)
        metrics["Volatilidade Anualizada"] = qs.stats.volatility(self.portfolio_returns, annualize=True)
        metrics["Sharpe Ratio"] = qs.stats.sharpe(self.portfolio_returns, rf=risk_free_rate/252, annualize=True) # rf diária
        metrics["Sortino Ratio"] = qs.stats.sortino(self.portfolio_returns, rf=risk_free_rate/252, annualize=True)
        metrics["Max Drawdown"] = qs.stats.max_drawdown(self.portfolio_returns)
        metrics["Calmar Ratio"] = qs.stats.calmar(self.portfolio_returns)
        metrics["Skew"] = qs.stats.skew(self.portfolio_returns)
        metrics["Kurtosis"] = qs.stats.kurtosis(self.portfolio_returns)
        
        if self.benchmark_returns is not None and not self.benchmark_returns.empty:
            metrics["Beta"] = qs.stats.beta(self.portfolio_returns, self.benchmark_returns)
            metrics["Alpha Anualizado (Jensen)"] = qs.stats.jensens_alpha(self.portfolio_returns, self.benchmark_returns, rf=risk_free_rate/252)
            metrics["Information Ratio"] = qs.stats.information_ratio(self.portfolio_returns, self.benchmark_returns)
            metrics["Tracking Error"] = qs.stats.tracking_error(self.portfolio_returns, self.benchmark_returns)
            metrics["Retorno Total (Benchmark)"] = (1 + self.benchmark_returns).prod() - 1
            metrics["CAGR (Benchmark)"] = qs.stats.cagr(self.benchmark_returns)
            metrics["Volatilidade Anualizada (Benchmark)"] = qs.stats.volatility(self.benchmark_returns, annualize=True)
            metrics["Sharpe Ratio (Benchmark)"] = qs.stats.sharpe(self.benchmark_returns, rf=risk_free_rate/252, annualize=True)
            metrics["Max Drawdown (Benchmark)"] = qs.stats.max_drawdown(self.benchmark_returns)

        return metrics.map(lambda x: f"{x*100:.2f}%" if isinstance(x, (float, np.floating)) and any(s in str(metrics[metrics == x].index[0]).lower() for s in ["retorno", "cagr", "drawdown", "volatilidade", "alpha", "tracking"]) and "ratio" not in str(metrics[metrics == x].index[0]).lower() else (f"{x:.2f}" if isinstance(x, (float, np.floating)) else x))

    def get_returns_df(self) -> pd.DataFrame:
        """Retorna um DataFrame com os retornos da carteira e do benchmark (se disponível)."""
        df = self.portfolio_returns.to_frame(name="Carteira")
        if self.benchmark_returns is not None:
            df["Benchmark"] = self.benchmark_returns
        return df

    def get_values_df(self) -> pd.DataFrame:
        """Retorna um DataFrame com os valores (curva de capital) da carteira e do benchmark (se disponível)."""
        df = self.portfolio_values.to_frame(name="Carteira")
        if self.benchmark_returns is not None:
            benchmark_values = (1 + self.benchmark_returns).cumprod() * self.initial_capital
            # Adicionar o capital inicial no primeiro dia para o benchmark também
            first_day_bm_value = pd.Series([self.initial_capital], index=[self.benchmark_returns.index[0] - pd.Timedelta(days=1)])
            if not isinstance(first_day_bm_value.index, pd.DatetimeIndex):
                 first_day_bm_value.index = pd.to_datetime(first_day_bm_value.index)
            benchmark_values = pd.concat([first_day_bm_value, benchmark_values]).sort_index()
            benchmark_values.iloc[0] = self.initial_capital
            df["Benchmark"] = benchmark_values.loc[df.index] # Alinha com o índice da carteira
        return df

    def get_drawdown_series(self) -> pd.DataFrame:
        """Retorna as séries de drawdown para carteira e benchmark."""
        dd_portfolio = qs.timeseries.to_drawdown_series(self.portfolio_returns)
        df = dd_portfolio.to_frame(name="Carteira Drawdown")
        if self.benchmark_returns is not None:
            dd_benchmark = qs.timeseries.to_drawdown_series(self.benchmark_returns)
            df["Benchmark Drawdown"] = dd_benchmark
        return df

if __name__ == "__main__":
    # Exemplo de uso (para teste direto do módulo)
    print("Executando exemplos locais para Backtester...")
    # Datas
    start_dt = "2020-01-01"
    end_dt = "2023-12-31"
    date_rng = pd.date_range(start=start_dt, end=end_dt, freq="B") # Dias úteis

    # Gerar retornos fictícios
    np.random.seed(42)
    portfolio_ret = pd.Series(np.random.randn(len(date_rng)) / 100, index=date_rng) # Retornos diários
    benchmark_ret = pd.Series(np.random.randn(len(date_rng)) / 100 + 0.0001, index=date_rng) # Bench um pouco melhor
    
    portfolio_ret.name = "Carteira"
    benchmark_ret.name = "Benchmark"

    # Teste 1: Inicializando com retornos
    print("\n--- Teste com Retornos ---")
    backtester_from_returns = Backtester(
        portfolio_returns=portfolio_ret, 
        benchmark_returns=benchmark_ret, 
        start_date=start_dt,
        initial_capital=100000.0
    )
    summary_from_returns = backtester_from_returns.get_performance_summary(risk_free_rate=0.02)
    print("Resumo do Desempenho (a partir de retornos):")
    print(summary_from_returns)

    # Teste 2: Inicializando com valores
    print("\n--- Teste com Valores ---")
    initial_cap = 50000.0
    portfolio_val = (1 + portfolio_ret).cumprod() * initial_cap
    # Adicionar valor inicial
    portfolio_val = pd.concat([pd.Series([initial_cap], index=[portfolio_ret.index[0] - pd.Timedelta(days=1)]), portfolio_val]).sort_index()
    portfolio_val.iloc[0] = initial_cap
    
    backtester_from_values = Backtester(
        portfolio_values=portfolio_val, 
        benchmark_returns=benchmark_ret, 
        start_date=start_dt,
        initial_capital=initial_cap # initial_capital aqui é mais para referência, pois os valores já são dados
    )
    summary_from_values = backtester_from_values.get_performance_summary(risk_free_rate=0.02)
    print("Resumo do Desempenho (a partir de valores):")
    print(summary_from_values)

    # Verificar se os DataFrames para gráficos estão corretos
    print("\nDataFrame de Valores (Curva de Capital):")
    print(backtester_from_returns.get_values_df().head())
    print("\nDataFrame de Retornos:")
    print(backtester_from_returns.get_returns_df().head())
    print("\nDataFrame de Drawdowns:")
    print(backtester_from_returns.get_drawdown_series().head())

    # Teste sem benchmark
    print("\n--- Teste sem Benchmark ---")
    backtester_no_bm = Backtester(portfolio_returns=portfolio_ret, start_date=start_dt)
    summary_no_bm = backtester_no_bm.get_performance_summary()
    print(summary_no_bm)

