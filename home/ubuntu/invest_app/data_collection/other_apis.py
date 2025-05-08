# -*- coding: utf-8 -*-
"""
Módulo para interagir com outras APIs financeiras (ex: Financial Modeling Prep)
E para buscar dados macroeconômicos de fontes diversas, incluindo o World Bank DataBank.

Este módulo será responsável por buscar dados complementares que podem não estar
disponíveis ou serem de melhor qualidade em outras fontes além do Yahoo Finance,
assim como dados macroeconômicos.

Funções principais:
- `get_fmp_profile(ticker, api_key)`: Busca perfil da empresa da FMP.
- `get_world_bank_indicator_data(indicator_code, country_iso3, start_year, end_year)`: Busca dados de indicadores do World Bank.
- `list_world_bank_indicators(search_query, page, page_size)`: Lista indicadores do World Bank.
- `save_data_to_csv(df: pd.DataFrame, filename: str, data_dir: str)`: Salva DataFrame em CSV.
"""

import pandas as pd
import requests # Para chamadas HTTP diretas, se necessário para FMP
import os
from datetime import datetime

# Importar ApiClient do Datasource quando executado no ambiente do Manus
# import sys
# sys.path.append("/opt/.manus/.sandbox-runtime")
# from data_api import ApiClient

__version__ = "0.0.1"
__author__ = "Manus AI Agent"
__email__ = ""

class OtherAPIs:
    """Classe para encapsular a lógica de acesso a outras APIs financeiras e fontes de dados."""

    def __init__(self, fmp_api_key: str = None, api_client=None):
        """
        Inicializa o cliente com chaves de API e o ApiClient do Datasource.

        Args:
            fmp_api_key (str, optional): Chave da API para Financial Modeling Prep.
            api_client: Cliente da API do Datasource para APIs como World Bank.
        """
        self.fmp_api_key = fmp_api_key
        self.fmp_base_url = "https://financialmodelingprep.com/api/v3"
        self.api_client = api_client

    def get_fmp_profile(self, ticker: str) -> dict:
        """
        Busca o perfil de uma empresa da API Financial Modeling Prep.
        Nota: FMP usa tickers como "AAPL". Para B3, pode ser necessário adaptar ou usar outra fonte.

        Args:
            ticker (str): O símbolo da ação (ex: "AAPL").

        Returns:
            dict: Dicionário com dados do perfil da empresa. Retorna dicionário vazio em caso de erro.
        """
        if not self.fmp_api_key:
            print("Chave da API da Financial Modeling Prep não fornecida.")
            return {}
        ticker_fmp = ticker 
        try:
            url = f"{self.fmp_base_url}/profile/{ticker_fmp}?apikey={self.fmp_api_key}"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            return data[0] if data and isinstance(data, list) and len(data) > 0 else (data if isinstance(data, dict) else {})
        except requests.exceptions.RequestException as e:
            print(f"Erro ao buscar perfil FMP para {ticker_fmp}: {e}")
            return {}
        except Exception as e:
            print(f"Erro inesperado ao processar perfil FMP para {ticker_fmp}: {e}")
            return {}

    def list_world_bank_indicators(self, search_query: str = None, page: int = 1, page_size: int = 10) -> dict:
        """
        Lista indicadores do World Development Indicators (DataBank).

        Args:
            search_query (str, optional): Termo para buscar indicadores.
            page (int): Número da página.
            page_size (int): Tamanho da página.

        Returns:
            dict: Resposta da API contendo a lista de indicadores e metadados de paginação.
                  Retorna dicionário vazio em caso de erro.
        """
        if not self.api_client:
            print("Erro: ApiClient não fornecido para list_world_bank_indicators.")
            return {}
        
        query_params = {"page": page, "pageSize": page_size}
        if search_query:
            query_params["q"] = search_query
        
        try:
            print(f"Listando indicadores do World Bank com query: {query_params}")
            response = self.api_client.call_api("DataBank/indicator_list", query=query_params)
            return response
        except Exception as e:
            print(f"Erro ao listar indicadores do World Bank: {e}")
            return {}

    def get_world_bank_indicator_data(
        self, indicator_code: str, country_iso3: str, 
        start_year: int = None, end_year: int = None
    ) -> pd.DataFrame:
        """
        Busca dados para um indicador específico do World Development Indicators (DataBank).

        Args:
            indicator_code (str): O código do indicador (ex: "NY.GDP.MKTP.CD" para PIB em USD correntes).
            country_iso3 (str): Código ISO 3166 alpha-3 do país (ex: "BRA" para Brasil).
            start_year (int, optional): Ano de início para filtrar os dados.
            end_year (int, optional): Ano de fim para filtrar os dados.

        Returns:
            pd.DataFrame: DataFrame com colunas "Year" e "Value" para o indicador e país especificados.
                          Retorna DataFrame vazio em caso de erro ou se nenhum dado for encontrado.
        """
        if not self.api_client:
            print("Erro: ApiClient não fornecido para get_world_bank_indicator_data.")
            return pd.DataFrame()

        query_params = {"indicator": indicator_code, "country": country_iso3}
        
        try:
            print(f"Buscando dados do World Bank para {indicator_code} ({country_iso3}) com query: {query_params}")
            response = self.api_client.call_api("DataBank/indicator_data", query=query_params)

            if response and response.get("data"):
                data_dict = response["data"]
                # A API retorna dados como {"year": value}, precisamos transformar isso
                # e também tratar anos com valor null (que podem ser strings "null" ou Python None)
                valid_data = []
                for year_str, value in data_dict.items():
                    try:
                        year = int(year_str)
                        if value is not None and str(value).lower() != "null": # Checa por None e string "null"
                            if start_year and year < start_year:
                                continue
                            if end_year and year > end_year:
                                continue
                            valid_data.append({"Year": year, "Value": float(value), "Indicator": indicator_code, "Country": country_iso3})
                    except ValueError:
                        print("Aviso: Não foi possível converter o ano" 
{year_str}" ou valor 
{value}" para o indicador {indicator_code}")
                        continue
                
                if not valid_data:
                    print(f"Nenhum dado válido encontrado para {indicator_code} ({country_iso3}) no período especificado.")
                    return pd.DataFrame()
                
                df = pd.DataFrame(valid_data)
                df = df.sort_values(by="Year").reset_index(drop=True)
                # Definir o índice para o ano pode ser útil para algumas análises
                # df.set_index("Year", inplace=True)
                return df
            else:
                print(f"Nenhum dado retornado pela API DataBank para {indicator_code} ({country_iso3}). Resposta: {response}")
                return pd.DataFrame()

        except Exception as e:
            print(f"Erro ao buscar dados do World Bank para {indicator_code} ({country_iso3}): {e}")
            return pd.DataFrame()

    def save_data_to_csv(self, df: pd.DataFrame, filename: str, data_dir: str = "/home/ubuntu/invest_app/data_cache") -> str | None:
        """
        Salva um DataFrame em um arquivo CSV no diretório especificado.
        O diretório será criado se não existir.
        """
        if df.empty:
            print(f"DataFrame para {filename} está vazio. Nada para salvar.")
            return None
        try:
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
                print(f"Diretório criado: {data_dir}")
            
            filepath = os.path.join(data_dir, filename)
            df.to_csv(filepath, index=False) # index=False para não salvar o índice default do pandas
            print(f"Dados salvos com sucesso em: {filepath}")
            return filepath
        except Exception as e:
            print(f"Erro ao salvar dados em {filename}: {e}")
            return None

if __name__ == "__main__":
    print("Executando exemplos locais para OtherAPIs...")

    # Crie um mock ApiClient para testes locais das APIs do Datasource
    class MockDatasourceApiClient:
        def call_api(self, api_name, query):
            print(f"MockDatasourceApiClient: Chamando API {api_name} com query {query}")
            if api_name == "DataBank/indicator_list":
                return {
                    "total": 1,
                    "page": query.get("page", 1),
                    "pageSize": query.get("pageSize", 10),
                    "items": [
                        {"indicatorCode": "NY.GDP.MKTP.CD", "indicatorName": "GDP (current US$)"}
                    ]
                }
            if api_name == "DataBank/indicator_data":
                if query.get("indicator") == "NY.GDP.MKTP.CD" and query.get("country") == "BRA":
                    return {
                        "countryCode": "BRA",
                        "countryName": "Brazil",
                        "indicatorCode": "NY.GDP.MKTP.CD",
                        "indicatorName": "GDP (current US$)",
                        "data": {
                            "2015": 1802214302430.24,
                            "2016": 1794677860907.13,
                            "2017": 2063515097202.14,
                            "2018": 1916933699106.94,
                            "2019": 1873247807090.78,
                            "2020": 1476105490011.84,
                            "2021": 1649623190548.23, # Exemplo de valor mais recente
                            "2022": 1920095876745.82, # Exemplo de valor mais recente
                            "2023": None # Exemplo de valor nulo
                        }
                    }
            return {}

    mock_ds_client = MockDatasourceApiClient()
    other_api_client = OtherAPIs(api_client=mock_ds_client)

    # Teste list_world_bank_indicators
    print("\n--- Teste list_world_bank_indicators ---")
    indicators_list = other_api_client.list_world_bank_indicators(search_query="GDP", page_size=5)
    if indicators_list and indicators_list.get("items"):
        print("Indicadores encontrados:")
        for item in indicators_list["items"]:
            print(f"  {item["indicatorCode"]}: {item["indicatorName"]}")
    else:
        print("Nenhum indicador encontrado ou erro na listagem.")

    # Teste get_world_bank_indicator_data
    print("\n--- Teste get_world_bank_indicator_data ---")
    gdp_brazil = other_api_client.get_world_bank_indicator_data(
        indicator_code="NY.GDP.MKTP.CD", 
        country_iso3="BRA", 
        start_year=2018, 
        end_year=2022
    )
    if not gdp_brazil.empty:
        print("\nPIB do Brasil (USD Correntes) - World Bank (Mock):")
        print(gdp_brazil)
        # Teste save_data_to_csv
        saved_wb_path = other_api_client.save_data_to_csv(gdp_brazil, "gdp_brazil_worldbank_mock.csv")
        if saved_wb_path:
            print(f"Dados do World Bank salvos em: {saved_wb_path}")
    else:
        print("\nNenhum dado do World Bank (PIB Brasil) encontrado ou erro.")

    # Exemplo de como buscar múltiplos indicadores e juntá-los (requereria múltiplas chamadas)
    # inflacao_code = "FP.CPI.TOTL.ZG" # Exemplo: Inflação, índice de preços ao consumidor (% anual)
    # selic_code = "FR.INR.RINR" # Exemplo: Taxa de juros real (%)
    # (Estes códigos são exemplos e podem não ser os mais adequados para o Brasil ou podem requerer tratamento específico)

    # inflacao_br = other_api_client.get_world_bank_indicator_data(inflacao_code, "BRA", 2015, 2022)
    # if not inflacao_br.empty:
    #     print("\nInflação Brasil (World Bank Mock):")
    #     print(inflacao_br)

