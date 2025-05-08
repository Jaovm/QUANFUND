# -*- coding: utf-8 -*-
"""
Módulo para interagir com a API do Yahoo Finance.

Este módulo será responsável por buscar dados históricos de preços,
informações fundamentalistas e outros dados relevantes de ações
diretamente da API do Yahoo Finance, utilizando a biblioteca yfinance ou chamadas diretas à API, se aplicável.

Funções principais:
- `get_stock_data(ticker, start_date, end_date, interval)`: Busca dados históricos.
- `get_stock_info(ticker)`: Busca informações gerais da empresa.
- `get_financials(ticker)`: Busca demonstrativos financeiros.
- `get_dividends(ticker)`: Busca histórico de dividendos.
- `get_benchmark_data(ticker, start_date, end_date, interval)`: Busca dados de benchmarks.
"""

import pandas as pd
from datetime import datetime

# Importar ApiClient do Datasource quando executado no ambiente do Manus
# import sys
# sys.path.append("/opt/.manus/.sandbox-runtime")
# from data_api import ApiClient

__version__ = "0.0.1"
__author__ = "Manus AI Agent"
__email__ = ""

# Constantes
DEFAULT_START_DATE = "2015-01-01"
DEFAULT_INTERVAL = "1d"

class YahooFinanceAPI:
    """Classe para encapsular a lógica de acesso à API do Yahoo Finance."""

    def __init__(self, api_client=None):
        """
        Inicializa o cliente da API.

        Args:
            api_client: Cliente da API para realizar as chamadas (se estiver usando uma API do Datasource).
        """
        self.api_client = api_client

    def _parse_ticker(self, ticker: str) -> str:
        """Adiciona .SA para tickers brasileiros se não presente."""
        if not ticker.upper().endswith(".SA"):
            return ticker.upper() + ".SA"
        return ticker.upper()

    def get_stock_data(self, ticker: str, start_date: str, end_date: str, interval: str = DEFAULT_INTERVAL) -> pd.DataFrame:
        """
        Busca dados históricos de uma ação utilizando a API do Datasource.

        Args:
            ticker (str): O símbolo da ação (ex: "PETR4" ou "PETR4.SA").
            start_date (str): Data de início no formato "YYYY-MM-DD".
            end_date (str): Data de fim no formato "YYYY-MM-DD".
            interval (str): Intervalo dos dados ("1d", "1wk", "1mo").

        Returns:
            pd.DataFrame: DataFrame com os dados históricos (Data, Open, High, Low, Close, Adj Close, Volume).
                          Retorna DataFrame vazio em caso de erro ou se nenhum dado for encontrado.
        """
        parsed_ticker = self._parse_ticker(ticker)
        print(f"Buscando dados para {parsed_ticker} de {start_date} a {end_date} com intervalo {interval} via Datasource API")

        if not self.api_client:
            print("Erro: ApiClient não fornecido para YahooFinanceAPI.")
            return pd.DataFrame()

        try:
            # Converter datas para timestamp epoch em segundos
            # A API espera que period1 seja o início do dia e period2 o início do dia seguinte ao último dia desejado.
            period1_dt = datetime.strptime(start_date, "%Y-%m-%d")
            period2_dt = datetime.strptime(end_date, "%Y-%m-%d")
            # Adiciona um dia a period2_dt para incluir os dados do end_date, e pega o início desse dia.
            period2_dt_inclusive = pd.Timestamp(period2_dt) + pd.Timedelta(days=1)
            
            period1_timestamp = str(int(period1_dt.timestamp()))
            period2_timestamp = str(int(period2_dt_inclusive.timestamp()))

            query_params = {
                "symbol": parsed_ticker,
                "region": "BR",
                "interval": interval,
                "period1": period1_timestamp,
                "period2": period2_timestamp,
                "includeAdjustedClose": True,
                "events": "history" # Para garantir que estamos pegando dados históricos
            }
            
            response = self.api_client.call_api(
                "YahooFinance/get_stock_chart",
                query=query_params
            )

            if response.get("chart") and response["chart"].get("result") and response["chart"]["result"][0]:
                result = response["chart"]["result"][0]
                timestamps = result.get("timestamp", [])
                if not timestamps:
                    print(f"Nenhum timestamp encontrado para {parsed_ticker} no período solicitado.")
                    return pd.DataFrame()

                ohlcv = result.get("indicators", {}).get("quote", [{}])[0]
                adj_close_list = result.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose", [])

                df = pd.DataFrame({
                    "Open": ohlcv.get("open", []),
                    "High": ohlcv.get("high", []),
                    "Low": ohlcv.get("low", []),
                    "Close": ohlcv.get("close", []),
                    "Volume": ohlcv.get("volume", []),
                    "Adj Close": adj_close_list
                }, index=pd.to_datetime(timestamps, unit="s"))
                
                # Remove linhas onde todos os valores de OHLC são NaN ou None (comum para datas sem pregão)
                df.dropna(subset=["Open", "High", "Low", "Close"], how="all", inplace=True)
                df.index.name = "Date"
                return df
            else:
                print(f"Nenhum dado retornado pela API para {parsed_ticker}. Resposta: {response}")
                return pd.DataFrame()

        except Exception as e:
            print(f"Erro ao buscar dados via API Datasource para {parsed_ticker}: {e}")
            return pd.DataFrame()

    def get_stock_info(self, ticker: str) -> dict:
        """
        Busca informações gerais de uma empresa/ação utilizando a API do Datasource.

        Args:
            ticker (str): O símbolo da ação (ex: "PETR4" ou "PETR4.SA").

        Returns:
            dict: Dicionário com informações da empresa. Retorna dicionário vazio em caso de erro.
        """
        parsed_ticker = self._parse_ticker(ticker)
        print(f"Buscando informações para {parsed_ticker} via Datasource API")

        if not self.api_client:
            print("Erro: ApiClient não fornecido para YahooFinanceAPI.")
            return {}

        try:
            response = self.api_client.call_api("YahooFinance/get_stock_insights", query={"symbol": parsed_ticker})
            
            if response.get("finance") and response["finance"].get("result"):
                result = response["finance"]["result"]
                # Extrair informações relevantes. A estrutura exata pode variar.
                # Baseado no schema: result.instrumentInfo, result.companySnapshot, etc.
                info = {
                    "symbol": result.get("symbol"),
                    "longName": result.get("instrumentInfo", {}).get("longName"),
                    "shortName": result.get("instrumentInfo", {}).get("shortName"),
                    "sector": result.get("companySnapshot", {}).get("sectorInfo"),
                    # Adicionar mais campos conforme a necessidade e disponibilidade na API
                    "currency": result.get("instrumentInfo", {}).get("currency"),
                    "exchangeName": result.get("instrumentInfo", {}).get("exchangeName"),
                    "marketCap": result.get("instrumentInfo", {}).get("marketCap") # Exemplo, verificar se existe
                }
                # Filtrar chaves com valores None para um dicionário mais limpo
                return {k: v for k, v in info.items() if v is not None}
            else:
                print(f"Nenhuma informação retornada pela API para {parsed_ticker}. Resposta: {response}")
                return {}
        except Exception as e:
            print(f"Erro ao buscar insights via API Datasource para {parsed_ticker}: {e}")
            return {}

    def get_benchmark_data(self, ticker: str, start_date: str, end_date: str, interval: str = DEFAULT_INTERVAL) -> pd.DataFrame:
        """
        Busca dados históricos de um benchmark (ex: IBOV).
        Reutiliza get_stock_data, pois a estrutura da chamada é similar.
        Para IBOVESPA, o ticker no Yahoo Finance é ^BVSP.

        Args:
            ticker (str): O símbolo do benchmark (ex: "^BVSP").
            start_date (str): Data de início no formato "YYYY-MM-DD".
            end_date (str): Data de fim no formato "YYYY-MM-DD".
            interval (str): Intervalo dos dados ("1d", "1wk", "1mo").

        Returns:
            pd.DataFrame: DataFrame com os dados históricos do benchmark.
        """
        print(f"Buscando dados do benchmark {ticker} de {start_date} a {end_date}")
        # Benchmarks podem não precisar do sufixo .SA ou da região BR estritamente,
        # mas a API get_stock_chart pode funcionar bem com region=BR para ^BVSP.
        return self.get_stock_data(ticker=ticker, start_date=start_date, end_date=end_date, interval=interval)


if __name__ == "__main__":
    # Este bloco __main__ é para teste local e não será executado pelo Manus Agent diretamente.
    # Para testar, você precisaria de uma implementação local do ApiClient.
    
    # Crie um mock ApiClient para testes locais
    class MockApiClient:
        def call_api(self, api_name, query):
            print(f"MockApiClient: Chamando API {api_name} com query {query}")
            if api_name == "YahooFinance/get_stock_chart":
                # Simular uma resposta da API para PETR4.SA
                if query.get("symbol") == "PETR4.SA":
                    return {
                        "chart": {
                            "result": [
                                {
                                    "meta": {"currency": "BRL", "symbol": "PETR4.SA"},
                                    "timestamp": [1672531200, 1672617600], # 2023-01-01, 2023-01-02 (exemplo)
                                    "indicators": {
                                        "quote": [
                                            {
                                                "open": [23.0, 23.5],
                                                "high": [23.6, 24.0],
                                                "low": [22.9, 23.3],
                                                "close": [23.5, 23.8],
                                                "volume": [1000000, 1200000]
                                            }
                                        ],
                                        "adjclose": [
                                            {"adjclose": [23.5, 23.8]}
                                        ]
                                    }
                                }
                            ],
                            "error": None
                        }
                    }
                elif query.get("symbol") == "^BVSP": # Simular IBOV
                     return {
                        "chart": {
                            "result": [
                                {
                                    "meta": {"currency": "PTS", "symbol": "^BVSP"},
                                    "timestamp": [1672531200, 1672617600],
                                    "indicators": {
                                        "quote": [
                                            {
                                                "open": [110000.0, 111000.0],
                                                "high": [111500.0, 112000.0],
                                                "low": [109500.0, 110500.0],
                                                "close": [111000.0, 111800.0],
                                                "volume": [2000000, 2200000]
                                            }
                                        ],
                                        "adjclose": [
                                            {"adjclose": [111000.0, 111800.0]}
                                        ]
                                    }
                                }
                            ],
                            "error": None
                        }
                    }
            elif api_name == "YahooFinance/get_stock_insights":
                if query.get("symbol") == "PETR4.SA":
                    return {
                        "finance": {
                            "result": {
                                "symbol": "PETR4.SA",
                                "instrumentInfo": {"longName": "Petroleo Brasileiro S.A. - Petrobras - Preferred Shares"},
                                "companySnapshot": {"sectorInfo": "Energy"}
                            },
                            "error": None
                        }
                    }
            return {} # Resposta vazia padrão

    print("Executando exemplos locais com MockApiClient...")
    mock_client = MockApiClient()
    yf_api = YahooFinanceAPI(api_client=mock_client)

    # Teste get_stock_data
    start = "2023-01-01"
    end = "2023-01-05"
    petr4_data = yf_api.get_stock_data(ticker="PETR4", start_date=start, end_date=end)
    if not petr4_data.empty:
        print("\nDados PETR4.SA (Mock):")
        print(petr4_data)
    else:
        print("\nDados PETR4.SA (Mock): DataFrame vazio ou erro.")

    # Teste get_stock_info
    petr4_info = yf_api.get_stock_info("PETR4")
    if petr4_info:
        print("\nInformações PETR4.SA (Mock):")
        print(petr4_info)
    else:
        print("\nInformações PETR4.SA (Mock): Dicionário vazio ou erro.")

    # Teste get_benchmark_data
    ibov_data = yf_api.get_benchmark_data(ticker="^BVSP", start_date=start, end_date=end)
    if not ibov_data.empty:
        print("\nDados ^BVSP (IBOVESPA) (Mock):")
        print(ibov_data)
    else:
        print("\nDados ^BVSP (Mock): DataFrame vazio ou erro.")

