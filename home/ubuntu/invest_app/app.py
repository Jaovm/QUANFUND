# -*- coding: utf-8 -*-
"""
Arquivo principal do aplicativo Streamlit para análise de investimentos.

Este arquivo será responsável por orquestrar a interface do usuário,
chamar os diferentes módulos de análise, otimização e visualização de dados.
"""

import streamlit as st
import pandas as pd
import numpy as np

# Importar módulos locais
from data_collection.yahoo_finance_api import YahooFinanceAPI
from data_collection.other_apis import OtherAPIs
from analysis.backtesting import Backtester # Usado em components
from analysis.valuation import ValuationModels # Passado como classe
from analysis.macro_analysis import MacroEconomicAnalysis # Instanciado e passado
from analysis.portfolio_analyzer import PortfolioSuggestor # Passado como classe
from optimization.markowitz import MarkowitzOptimizer
from optimization.hrp import HRPOptimizer
from optimization.max_diversification import MaxDiversificationOptimizer
from optimization.monte_carlo import MonteCarloOptimizer
from ui import components # Contém as funções de renderização das seções
# from utils import helpers # Se houver helpers genéricos

__version__ = "0.0.4" # Incrementada a versão
__author__ = "Manus AI Agent"
__email__ = ""

# --- Inicialização de Clientes e Módulos --- 

st.set_page_config(
    layout="wide",
    page_title="Análise de Investimentos PRO"
)

# ... seus outros imports e código ...
@st.cache_resource
def get_yahoo_finance_client():
    try:
        import sys
        sys.path.append("/opt/.manus/.sandbox-runtime")
        from data_api import ApiClient
        print("ApiClient do Datasource encontrado e importado para YahooFinanceAPI.")
        return YahooFinanceAPI(api_client=ApiClient())
    except ImportError:
        print("ApiClient do Datasource não encontrado. YahooFinanceAPI operará sem ele para APIs do Datasource.")
        return YahooFinanceAPI(api_client=None) 

@st.cache_resource
def get_other_api_client(fmp_api_key=None):
    try:
        import sys
        sys.path.append("/opt/.manus/.sandbox-runtime")
        from data_api import ApiClient
        print("ApiClient do Datasource encontrado para OtherAPIs.")
        return OtherAPIs(fmp_api_key=fmp_api_key, api_client=ApiClient())
    except ImportError:
        print("ApiClient do Datasource não encontrado. OtherAPIs operará sem ele para APIs do Datasource.")
        return OtherAPIs(fmp_api_key=fmp_api_key, api_client=None)

@st.cache_resource
def get_macro_economic_analyzer(_other_api_client): # Passar o cliente other_api já instanciado
    # MacroEconomicAnalysis pode precisar do api_client do OtherAPIs se for usar WorldBank via Datasource
    return MacroEconomicAnalysis(api_client=_other_api_client.api_client if _other_api_client else None)

# Instâncias dos módulos (alguns podem precisar de dados para inicializar)
yf_client = get_yahoo_finance_client()
# A chave FMP é opcional, o usuário pode ou não fornecê-la.
# A instanciação de other_api_cli e macro_analyzer ocorrerá após a possível entrada da chave API.

# --- Funções Auxiliares para UI (movidas para components.py ou específicas da seção) ---

def display_portfolio_performance(weights: dict, performance: pd.Series):
    """Exibe os pesos e a performance da carteira otimizada."""
    if weights and not performance.empty:
        st.subheader("Resultados da Otimização")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Pesos Otimizados:**")
            weights_df = pd.DataFrame.from_dict(weights, orient="index", columns=["Peso"])
            weights_df = weights_df[weights_df["Peso"] > 1e-4] 
            weights_df["Peso"] = weights_df["Peso"].apply(lambda x: f"{x*100:.2f}%")
            st.dataframe(weights_df)
        with col2:
            st.write("**Performance Esperada:**")
            perf_df = performance.to_frame()
            perf_df.columns = ["Valor"]
            for idx in perf_df.index:
                if "Retorno" in idx or "Volatilidade" in idx:
                    if isinstance(perf_df.loc[idx, "Valor"], (float, np.floating)):
                        perf_df.loc[idx, "Valor"] = f"{perf_df.loc[idx, "Valor"]*100:.2f}%"
                elif "Sharpe" in idx:
                     if isinstance(perf_df.loc[idx, "Valor"], (float, np.floating)):
                        perf_df.loc[idx, "Valor"] = f"{perf_df.loc[idx, "Valor"]:.2f}"
            st.dataframe(perf_df)
    else:
        st.error("Não foi possível obter os resultados da otimização.")

# --- Seção de Otimização de Carteira (Exemplo de como estava, agora será chamada de components) ---

def portfolio_optimization_section_logic(): # Renomeado para evitar conflito e mostrar que a lógica está aqui
    st.header("5. Otimização de Carteira")
    st.markdown("""
    Esta seção permite montar e otimizar carteiras com base em diferentes modelos matemáticos.
    Você precisará fornecer dados históricos de preços para os ativos que deseja incluir na otimização.
    """)

    st.subheader("1. Upload de Dados de Preços Históricos")
    st.markdown("Faça o upload de um arquivo CSV com os preços históricos de fechamento ajustado. O arquivo deve ter a data como primeira coluna (índice) e cada coluna subsequente representando um ticker com seus preços.")
    
    uploaded_prices_file = st.file_uploader("Selecione o arquivo CSV de preços históricos", type=["csv"], key="prices_opt_upload")
    
    historical_prices_df = None
    if uploaded_prices_file is not None:
        try:
            # Usar a função de components para consistência, mas aqui é a lógica interna da seção
            historical_prices_df = pd.read_csv(uploaded_prices_file, index_col=0, parse_dates=True)
            if not isinstance(historical_prices_df.index, pd.DatetimeIndex):
                st.error("A primeira coluna (índice) deve ser de datas. Verifique o formato do seu CSV.")
                return
            st.success(f"Arquivo de preços carregado com {len(historical_prices_df.columns)} ativos e {len(historical_prices_df)} observações.")
            st.dataframe(historical_prices_df.head())
        except Exception as e:
            st.error(f"Erro ao ler o arquivo de preços: {e}")
            return
    else:
        st.info("Aguardando upload do arquivo de preços históricos.")
        return 

    st.subheader("2. Escolha do Modelo de Otimização")
    optimization_model_choice = st.selectbox(
        "Selecione o modelo de otimização:",
        ["Fronteira Eficiente (Markowitz)", "Paridade de Risco Hierárquica (HRP)", 
         "Diversificação Máxima (Equal Weight)", "Simulação de Monte Carlo"],
        key="opt_model_choice_main_app"
    )

    risk_free_rate_opt = st.number_input("Taxa Livre de Risco Anualizada (ex: 0.02 para 2%):", value=0.02, min_value=0.0, max_value=0.5, step=0.001, format="%.3f", key="rf_opt_main_app")

    # Inputs específicos para Markowitz e Monte Carlo
    markowitz_opt_type = None
    target_return_val = None
    num_sim_portfolios = None
    mc_opt_metric = None

    if optimization_model_choice == "Fronteira Eficiente (Markowitz)":
        markowitz_opt_type = st.radio("Tipo de Otimização Markowitz:", 
                                      ("Maximizar Sharpe Ratio", "Minimizar Volatilidade", "Retorno Alvo"), 
                                      key="markowitz_type_radio_main", horizontal=True)
        if markowitz_opt_type == "Retorno Alvo":
            target_return_val = st.number_input("Retorno Anualizado Alvo (ex: 0.15 para 15%):", 
                                                value=0.15, min_value=-0.5, max_value=1.0, step=0.01, format="%.2f",
                                                key="markowitz_target_return_input_main")
    elif optimization_model_choice == "Simulação de Monte Carlo":
        num_sim_portfolios = st.number_input("Número de Carteiras para Simulação:", value=5000, min_value=1000, max_value=50000, step=1000, key="mc_num_portfolios_main")
        mc_opt_metric_choice = st.radio("Otimizar para (dentro da simulação):", ("Máximo Sharpe Ratio", "Mínima Volatilidade"), key="mc_metric_radio_main", horizontal=True)
        metric_map = {"Máximo Sharpe Ratio": "SharpeRatio", "Mínima Volatilidade": "Volatilidade"}
        mc_opt_metric = metric_map[mc_opt_metric_choice]

    if st.button("Otimizar Carteira", key="run_optimization_button_main"):
        if historical_prices_df is None or historical_prices_df.empty:
            st.warning("Por favor, faça o upload de um arquivo de preços históricos primeiro.")
            return

        weights, performance = None, pd.Series(dtype=float)
        
        with st.spinner("Otimizando carteira, por favor aguarde..."):
            if optimization_model_choice == "Fronteira Eficiente (Markowitz)":
                optimizer = MarkowitzOptimizer(historical_prices=historical_prices_df)
                if markowitz_opt_type == "Maximizar Sharpe Ratio":
                    weights, performance = optimizer.optimize_for_max_sharpe(risk_free_rate=risk_free_rate_opt)
                elif markowitz_opt_type == "Minimizar Volatilidade":
                    weights, performance = optimizer.optimize_for_min_volatility()
                elif markowitz_opt_type == "Retorno Alvo":
                    if target_return_val is not None:
                         weights, performance = optimizer.optimize_for_target_return(target_return=target_return_val)
                    else:
                        st.warning("Por favor, defina um retorno alvo.")
                        return
            
            elif optimization_model_choice == "Paridade de Risco Hierárquica (HRP)":
                optimizer = HRPOptimizer(historical_prices=historical_prices_df)
                weights, performance = optimizer.optimize()

            elif optimization_model_choice == "Diversificação Máxima (Equal Weight)":
                optimizer = MaxDiversificationOptimizer(historical_prices=historical_prices_df)
                weights, performance = optimizer.optimize_equal_weight()

            elif optimization_model_choice == "Simulação de Monte Carlo":
                optimizer = MonteCarloOptimizer(historical_prices=historical_prices_df, num_portfolios=num_sim_portfolios if num_sim_portfolios else 5000)
                simulation_df = optimizer.run_simulation(risk_free_rate=risk_free_rate_opt)
                if simulation_df is not None and not simulation_df.empty:
                    st.subheader("Visualização da Simulação de Monte Carlo")
                    try:
                        import plotly.express as px
                        fig = px.scatter(simulation_df, x="Volatilidade", y="Retorno", color="SharpeRatio", 
                                         title="Fronteira Eficiente - Simulação de Monte Carlo", 
                                         hover_data=historical_prices_df.columns.tolist())
                        max_sharpe_port = simulation_df.loc[simulation_df["SharpeRatio"].idxmax()]
                        min_vol_port = simulation_df.loc[simulation_df["Volatilidade"].idxmin()]
                        fig.add_scatter(x=[max_sharpe_port["Volatilidade"]], y=[max_sharpe_port["Retorno"]], mode="markers", 
                                        marker=dict(color="red", size=12, symbol="star"), name="Max Sharpe")
                        fig.add_scatter(x=[min_vol_port["Volatilidade"]], y=[min_vol_port["Retorno"]], mode="markers", 
                                        marker=dict(color="blue", size=12, symbol="diamond"), name="Min Volatilidade")
                        st.plotly_chart(fig, use_container_width=True)
                    except ImportError:
                        st.warning("Plotly não instalado. Gráfico não pode ser exibido. Tente: pip install plotly")
                    except Exception as e_plot:
                        st.error(f"Erro ao gerar gráfico da simulação: {e_plot}")
                    
                    if mc_opt_metric:
                        weights, performance = optimizer.get_optimal_portfolio(metric=mc_opt_metric)
                else:
                    st.error("Falha ao executar a simulação de Monte Carlo.")
                    return

        if weights and performance is not None and not performance.empty:
            display_portfolio_performance(weights, performance)
        elif weights and (performance is None or performance.empty) and optimization_model_choice == "Paridade de Risco Hierárquica (HRP)": 
            # HRP pode retornar pesos sem performance detalhada se mu não for usado explicitamente para ela
            st.subheader("Resultados da Otimização (HRP)")
            st.write("**Pesos Otimizados (HRP):**")
            weights_df = pd.DataFrame.from_dict(weights, orient="index", columns=["Peso"])
            weights_df = weights_df[weights_df["Peso"] > 1e-4]
            weights_df["Peso"] = weights_df["Peso"].apply(lambda x: f"{x*100:.2f}%")
            st.dataframe(weights_df)
            st.info("HRP foca na paridade de risco. A performance detalhada (retorno/sharpe) pode ser avaliada via backtest.")
        else:
            st.error("Otimização falhou ou não produziu resultados válidos.")

    st.markdown("---_---")
    st.markdown("**Observações:**")
    st.markdown("- Os retornos esperados e a volatilidade são baseados em dados históricos e não garantem performance futura.")
    st.markdown("- A taxa livre de risco é usada para calcular o Índice de Sharpe.")
    st.markdown("- Para Markowitz com Retorno Alvo, certifique-se que o alvo é factível com base nos retornos históricos dos ativos.")

# --- Função Principal --- 

def main():
    st.set_page_config(layout="wide", page_title="Análise de Investimentos PRO")
    st.title("Plataforma Avançada de Análise de Investimentos em Ações Brasileiras")
    st.caption(f"Versão {__version__}")

    st.sidebar.header("Navegação")
    app_mode = st.sidebar.selectbox(
        "Selecione o Módulo",
        [
            "Visão Geral",
            "1. Backtest de Carteira",
            "2. Recomendações por Cenário",
            "3. Sugestão de Aportes",
            "4. Análise de Valuation",
            "5. Otimização de Carteira",
        ],
        key="main_app_mode_selector"
    )

    st.sidebar.markdown("---_---")
    st.sidebar.subheader("Configurações Globais")
    # A chave FMP é opcional. Se fornecida, o cliente OtherAPIs será atualizado.
    # api_key_fmp = st.sidebar.text_input("Chave API Financial Modeling Prep (Opcional)", type="password", key="fmp_api_key_input_main")
    
    # Instanciar other_api_cli e macro_analyzer aqui, após a sidebar ser renderizada
    # para que a chave FMP possa ser usada se fornecida.
    # No entanto, para @st.cache_resource, a inicialização acontece uma vez. 
    # Se a chave FMP for dinâmica, o cache precisa ser gerenciado ou o cliente recriado.
    # Por simplicidade, vamos instanciar com None se não houver chave.
    other_api_cli = get_other_api_client(fmp_api_key=None) # Passar api_key_fmp se descomentado e preenchido
    macro_economic_analyzer_instance = get_macro_economic_analyzer(other_api_cli)

    if app_mode == "Visão Geral":
        st.header("Bem-vindo à Plataforma de Análise de Investimentos!")
        st.markdown("""
            Esta plataforma integra diversas ferramentas para auxiliar na tomada de decisão de investimentos
            em ações brasileiras. Utilize o menu lateral para navegar entre os módulos.
            
            **Funcionalidades:**
            - **Backtest de Carteira:** Analise o desempenho histórico de sua carteira comparado a benchmarks.
            - **Recomendações por Cenário:** Receba sugestões de setores e ações com base no cenário macroeconômico.
            - **Sugestão de Aportes:** Otimize seus aportes com base na sua carteira atual e oportunidades de mercado.
            - **Análise de Valuation:** Avalie ações utilizando múltiplas metodologias (DCF, Múltiplos, Graham, etc.).
            - **Otimização de Carteira:** Construa carteiras otimizadas com modelos como Markowitz, HRP, e mais.
            
            Comece selecionando um módulo na barra lateral.
            """
        )

    elif app_mode == "1. Backtest de Carteira":
        components.render_backtest_section(yf_client)

    elif app_mode == "2. Recomendações por Cenário":
        components.render_macro_recommendation_section(macro_economic_analyzer_instance)

    elif app_mode == "3. Sugestão de Aportes":
        components.render_contribution_suggestion_section(yf_client, macro_economic_analyzer_instance, PortfolioSuggestor, ValuationModels)

    elif app_mode == "4. Análise de Valuation":
        components.render_valuation_section(yf_client, ValuationModels)

    elif app_mode == "5. Otimização de Carteira":
        # A lógica de otimização de carteira é complexa e tem seus próprios inputs, 
        # então mantê-la aqui ou em components.py é uma escolha de design.
        # Por ora, a lógica principal está aqui para fácil acesso, mas poderia ser movida.
        portfolio_optimization_section_logic()

    st.sidebar.markdown("---_---")
    st.sidebar.info("Desenvolvido por Manus AI Agent")

if __name__ == "__main__":
    main()

