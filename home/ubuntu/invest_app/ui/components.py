# -*- coding: utf-8 -*-
"""
Módulo para componentes reutilizáveis da interface Streamlit.

Este módulo conterá funções que renderizam partes específicas da UI,
como seções de input, gráficos, tabelas, etc., para manter o `app.py` mais limpo.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Importar classes dos módulos de backend
from data_collection.yahoo_finance_api import YahooFinanceAPI
from analysis.backtesting import Backtester
from analysis.valuation import ValuationModels
from analysis.macro_analysis import MacroEconomicAnalysis
from analysis.portfolio_analyzer import PortfolioSuggestor

__version__ = "0.0.2"
__author__ = "Manus AI Agent"
__email__ = ""

# --- Componentes Gerais ---

def render_data_upload_section(label: str = "Faça o upload da sua carteira (CSV)", key_suffix: str = "portfolio") -> pd.DataFrame | None:
    """Renderiza a seção de upload de arquivo CSV e retorna o DataFrame."""
    uploaded_file = st.file_uploader(label, type=["csv"], key=f"upload_{key_suffix}")
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.success("Arquivo carregado com sucesso!")
            # Tentar converter a primeira coluna para datetime se for o caso de preços históricos
            if df.columns[0].lower() in ["date", "data"] and key_suffix == "prices":
                df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
                df = df.set_index(df.columns[0])
            return df
        except Exception as e:
            st.error(f"Erro ao ler o arquivo: {e}")
            return None
    return None

def display_df_if_exists(df: pd.DataFrame | None, title: str = "Pré-visualização dos Dados"):
    if df is not None and not df.empty:
        st.subheader(title)
        st.dataframe(df.head())

# --- Componentes Específicos das Seções ---

def render_backtest_section(yf_client: YahooFinanceAPI):
    st.header("1. Backtest de Carteira")
    st.markdown("""
    Analise o desempenho histórico de uma carteira de ações. 
    Faça o upload de um arquivo CSV com os tickers e pesos da sua carteira, ou defina manualmente.
    O backtest será realizado desde 01/01/2015 até a data mais recente disponível.
    """)

    st.subheader("Definição da Carteira")
    # Opção de upload ou manual
    input_method = st.radio("Como deseja definir a carteira?", ("Upload CSV", "Entrada Manual"), key="backtest_input_method", horizontal=True)

    portfolio_dict = None
    if input_method == "Upload CSV":
        st.markdown("O CSV deve ter duas colunas: `Ticker` e `Peso`. Ex: `PETR4.SA, 0.6`")
        portfolio_df = render_data_upload_section(label="Upload CSV da Carteira (Ticker, Peso)", key_suffix="backtest_portfolio")
        if portfolio_df is not None:
            if "Ticker" in portfolio_df.columns and "Peso" in portfolio_df.columns:
                try:
                    portfolio_df["Peso"] = pd.to_numeric(portfolio_df["Peso"])
                    total_weight = portfolio_df["Peso"].sum()
                    if not np.isclose(total_weight, 1.0):
                        st.warning(f"A soma dos pesos é {total_weight:.2f}, normalizando para 1.0.")
                        portfolio_df["Peso"] = portfolio_df["Peso"] / total_weight
                    portfolio_dict = pd.Series(portfolio_df.Peso.values, index=portfolio_df.Ticker).to_dict()
                    st.write("Carteira Carregada:", portfolio_dict)
                except Exception as e:
                    st.error(f"Erro ao processar o CSV da carteira: {e}")
            else:
                st.error("CSV da carteira deve conter as colunas 'Ticker' e 'Peso'.")
    else: # Entrada Manual
        num_assets = st.number_input("Número de Ativos na Carteira:", min_value=1, value=3, step=1, key="backtest_num_assets")
        temp_portfolio = {}
        cols = st.columns(2)
        for i in range(num_assets):
            ticker = cols[0].text_input(f"Ticker do Ativo {i+1} (ex: PETR4.SA)", key=f"bt_ticker_{i}").upper()
            weight = cols[1].number_input(f"Peso do Ativo {i+1} (ex: 0.3)", min_value=0.0, max_value=1.0, value=1.0/num_assets, step=0.01, key=f"bt_weight_{i}")
            if ticker: # Adicionar apenas se o ticker for preenchido
                temp_portfolio[ticker] = weight
        
        if temp_portfolio:
            total_weight_manual = sum(temp_portfolio.values())
            if not np.isclose(total_weight_manual, 1.0) and total_weight_manual > 0:
                st.warning(f"Soma dos pesos é {total_weight_manual:.2f}. Normalizando para 1.0 se você prosseguir.")
                # Normalização será feita antes de passar para o backtester se o usuário clicar em rodar
            portfolio_dict = temp_portfolio # Será normalizado depois
            st.write("Carteira Definida Manualmente (pré-normalização):", portfolio_dict)

    benchmark_ticker = st.text_input("Ticker do Benchmark (ex: ^BVSP para IBOVESPA)", value="^BVSP").upper()
    start_date_bt = st.date_input("Data de Início do Backtest", value=datetime(2015, 1, 1))
    end_date_bt = st.date_input("Data de Fim do Backtest", value=datetime.today() - timedelta(days=1))

    if st.button("Rodar Backtest", key="run_backtest_button"):
        if not portfolio_dict:
            st.error("Defina a carteira antes de rodar o backtest.")
            return
        if not benchmark_ticker:
            st.error("Defina um ticker para o benchmark.")
            return
        
        # Normalizar pesos se entrada manual e soma não for 1
        if input_method == "Entrada Manual":
            total_weight_manual_final = sum(portfolio_dict.values())
            if not np.isclose(total_weight_manual_final, 1.0) and total_weight_manual_final > 0:
                portfolio_dict = {t: w / total_weight_manual_final for t, w in portfolio_dict.items()}
                st.info(f"Pesos manualizados normalizados: {portfolio_dict}")
            elif total_weight_manual_final == 0 and len(portfolio_dict) > 0:
                st.error("Pesos manuais somam zero. Defina pesos válidos.")
                return

        with st.spinner("Coletando dados e rodando backtest..."):
            try:
                all_tickers = list(portfolio_dict.keys()) + [benchmark_ticker]
                historical_data = yf_client.get_multiple_stocks_history(all_tickers, 
                                                                        period1=start_date_bt.strftime("%Y-%m-%d"), 
                                                                        period2=end_date_bt.strftime("%Y-%m-%d"),
                                                                        interval="1d")
                if historical_data.empty:
                    st.error("Não foi possível obter dados históricos para os tickers fornecidos.")
                    return
                
                # Verificar se todos os tickers da carteira estão nos dados baixados
                missing_tickers = [ticker for ticker in portfolio_dict.keys() if ticker not in historical_data.columns]
                if missing_tickers:
                    st.error(f"Dados não encontrados para os seguintes tickers da carteira: {', '.join(missing_tickers)}. Remova-os ou verifique os nomes.")
                    # Remover tickers ausentes do portfolio_dict para prosseguir com o que tem
                    for mt in missing_tickers: del portfolio_dict[mt]
                    if not portfolio_dict: return # Se todos foram removidos
                    # Renormalizar pesos se alguns foram removidos
                    current_sum = sum(portfolio_dict.values())
                    if current_sum > 0 and not np.isclose(current_sum, 1.0):
                        portfolio_dict = {t: w/current_sum for t,w in portfolio_dict.items()}
                        st.warning(f"Carteira ajustada devido a tickers ausentes: {portfolio_dict}")
                
                if benchmark_ticker not in historical_data.columns:
                    st.error(f"Não foi possível obter dados para o benchmark {benchmark_ticker}.")
                    return

                backtester = Backtester(portfolio_weights=portfolio_dict, 
                                        benchmark_ticker=benchmark_ticker, 
                                        historical_prices=historical_data)
                
                report_html_path = backtester.run_backtest_and_generate_report(output_dir="/home/ubuntu/invest_app/reports", 
                                                                             report_filename="backtest_report.html")
                if report_html_path:
                    st.success("Backtest concluído! Visualizando relatório...")
                    # Ler o HTML e exibir no Streamlit
                    with open(report_html_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    st.components.v1.html(html_content, height=800, scrolling=True)
                    st.download_button("Baixar Relatório do Backtest (HTML)", data=html_content, file_name="backtest_report.html", mime="text/html")
                else:
                    st.error("Falha ao gerar o relatório do backtest.")
            except Exception as e:
                st.error(f"Erro durante o backtest: {e}")
                st.exception(e) # Mostra o traceback para debug

    st.markdown("---_---")
    st.markdown("**Observações:**")
    st.markdown("- Certifique-se que os tickers estão corretos e incluem o sufixo `.SA` para ações brasileiras (ex: `PETR4.SA`).")
    st.markdown("- O backtest utiliza dados de fechamento ajustado.")

def render_valuation_section(yf_client: YahooFinanceAPI, ValuationModelsClass: type[ValuationModels]):
    st.header("4. Análise de Valuation de Ações")
    st.markdown("Avalie uma ação utilizando múltiplas metodologias de valuation.")

    ticker_val = st.text_input("Digite o ticker da ação (ex: PETR4.SA):", key="valuation_ticker_input").upper()

    if ticker_val:
        if st.button("Analisar Valuation", key="run_valuation_button"):
            with st.spinner(f"Buscando dados e calculando valuation para {ticker_val}..."):
                try:
                    stock_info = yf_client.get_stock_info(ticker_val)
                    if not stock_info or not isinstance(stock_info, dict):
                        st.error(f"Não foi possível obter informações para o ticker {ticker_val}. Verifique o ticker.")
                        return
                    
                    # Parâmetros para DDM e DCF (podem ser inputs do usuário no futuro)
                    ddm_k = st.slider("Taxa de Retorno Requerida (k) para DDM (%)", 0.0, 30.0, 12.0, 0.5, format="%.1f%%")/100
                    ddm_g = st.slider("Taxa de Crescimento Perpétuo (g) para DDM (%)", 0.0, 10.0, 3.0, 0.1, format="%.1f%%")/100
                    dcf_wacc = st.slider("WACC para DCF (%)", 0.0, 30.0, 10.0, 0.5, format="%.1f%%")/100
                    dcf_g_st = st.slider("Crescimento Curto Prazo FCF para DCF (%)", 0.0, 20.0, 7.0, 0.5, format="%.1f%%")/100
                    dcf_g_lt = st.slider("Crescimento Longo Prazo FCF para DCF (%)", 0.0, 10.0, 2.0, 0.1, format="%.1f%%")/100

                    valuation_model = ValuationModelsClass(stock_info_data=stock_info)
                    all_valuations = valuation_model.get_all_valuations(
                        ddm_k=ddm_k, ddm_g=ddm_g, 
                        dcf_wacc=dcf_wacc, dcf_g_st=dcf_g_st, dcf_g_lt=dcf_g_lt
                    )

                    if all_valuations:
                        st.subheader(f"Resultados do Valuation para {all_valuations.get('Ticker', ticker_val)}")
                        
                        current_price_val = all_valuations.get("Preço Atual")
                        if current_price_val is not None:
                            st.metric(label="Preço Atual", value=f"R$ {current_price_val}")
                        
                        # Exibir cada métrica de valuation
                        # Organizar em colunas para melhor visualização
                        col_val1, col_val2 = st.columns(2)
                        metrics_to_display = [
                            ("Graham Number", "Número de Graham"),
                            ("VPA (Valor Patrimonial por Ação)", "VPA"),
                            ("Bazin (Yield 6%)", "Preço Teto (Bazin)"),
                            (f"DDM (k={ddm_k*100:.1f}%, g={ddm_g*100:.1f}%)", "DDM"),
                            ("DCF (Simplificado)", "DCF Simplificado")
                        ]
                        
                        count = 0
                        for key, label_display in metrics_to_display:
                            val = all_valuations.get(key)
                            margin_key = f"Margem Seg. {key.split('(')[0].strip()} (%)"
                            margin_val_str = all_valuations.get(margin_key)
                            
                            target_col = col_val1 if count % 2 == 0 else col_val2
                            if val is not None:
                                display_val_str = f"R$ {val}" if isinstance(val, str) and val.replace('.','',1).isdigit() else str(val)
                                if margin_val_str is not None:
                                    target_col.metric(label=label_display, value=display_val_str, delta=str(margin_val_str) + " de margem")
                                else:
                                    target_col.metric(label=label_display, value=display_val_str)
                            count += 1
                        
                        st.subheader("Múltiplos")
                        multiples_data = all_valuations.get("Múltiplos")
                        if isinstance(multiples_data, dict) and multiples_data:
                            multiples_df = pd.DataFrame.from_dict(multiples_data, orient="index", columns=["Valor"])
                            st.table(multiples_df)
                        else:
                            st.info("Não foi possível calcular os múltiplos.")
                            
                        st.markdown("---_---")
                        st.markdown("**Disclaimer:** Os valores apresentados são estimativas baseadas em modelos e dados públicos. Não constituem recomendação de investimento.")
                        st.markdown("- O DCF Simplificado é uma estimativa e pode não refletir todas as nuances de um DCF completo.")

                    else:
                        st.error(f"Não foi possível calcular o valuation para {ticker_val}.")
                except Exception as e:
                    st.error(f"Erro ao realizar a análise de valuation: {e}")
                    st.exception(e)


def render_macro_recommendation_section(macro_analyzer: MacroEconomicAnalysis):
    st.header("2. Recomendações por Cenário Macroeconômico")
    st.markdown("""
    Receba sugestões de setores e, futuramente, ações, com base no cenário macroeconômico atual.
    Você pode definir o cenário manualmente ou tentar uma detecção automática (funcionalidade futura).
    """)

    st.subheader("Definição do Cenário Macroeconômico")
    # No momento, apenas manual. Automático pode ser adicionado depois.
    selic_rate = st.number_input("Taxa Selic Atual (% a.a.):", value=10.5, min_value=0.0, max_value=30.0, step=0.25, format="%.2f") / 100
    inflation_ipca = st.number_input("Inflação IPCA Acumulada 12 meses (%):", value=3.9, min_value=-5.0, max_value=20.0, step=0.1, format="%.1f") / 100
    gdp_growth = st.number_input("Crescimento do PIB Esperado (% a.a.):", value=2.0, min_value=-10.0, max_value=10.0, step=0.1, format="%.1f") / 100
    # Adicionar mais variáveis macro se o dicionário de sensibilidade for mais complexo

    current_scenario = {
        "selic": selic_rate,
        "inflation": inflation_ipca,
        "gdp_growth": gdp_growth
    }
    st.write("Cenário Macroeconômico Definido:", current_scenario)

    if st.button("Analisar Setores Favoritos", key="run_macro_analysis_button"):
        with st.spinner("Analisando sensibilidade setorial..."):
            try:
                favored_sectors, sector_scores = macro_analyzer.get_favored_sectors(current_scenario)
                
                if favored_sectors:
                    st.subheader("Setores Potencialmente Favorecidos")
                    # Exibir como lista ou tabela
                    fav_df = pd.DataFrame(sector_scores.items(), columns=["Setor", "Score de Atratividade"])
                    fav_df = fav_df.sort_values(by="Score de Atratividade", ascending=False)
                    st.dataframe(fav_df)
                    st.markdown("**Observação:** Scores mais altos indicam maior atratividade teórica no cenário definido.")
                else:
                    st.info("Não foi possível determinar setores favorecidos com base no cenário e sensibilidade definidos.")
            except Exception as e:
                st.error(f"Erro ao analisar setores: {e}")
                st.exception(e)
    
    st.markdown("---_---")
    st.markdown("**Dicionário de Sensibilidade Setorial (Exemplo):**")
    st.json(macro_analyzer.sector_sensitivity) # Mostra o dicionário usado


def render_contribution_suggestion_section(yf_client: YahooFinanceAPI, macro_analyzer: MacroEconomicAnalysis, PortfolioSuggestorClass: type[PortfolioSuggestor], ValuationModelsClass: type[ValuationModels]):
    st.header("3. Sugestão de Aportes")
    st.markdown("""
    Receba sugestões de onde aportar seu próximo investimento, considerando sua carteira atual,
    o cenário macroeconômico e oportunidades de valuation atrativo.
    """)

    st.subheader("1. Carteira Atual")
    st.markdown("Faça o upload de um arquivo CSV com sua carteira atual. Colunas: `Ticker`, `Quantidade`, `PrecoMedio` (opcional). Ex: `PETR4.SA, 100, 28.50`")
    current_portfolio_df = render_data_upload_section(label="Upload CSV da Carteira Atual", key_suffix="contrib_portfolio")
    
    user_portfolio = None
    if current_portfolio_df is not None:
        if "Ticker" in current_portfolio_df.columns and "Quantidade" in current_portfolio_df.columns:
            try:
                current_portfolio_df["Quantidade"] = pd.to_numeric(current_portfolio_df["Quantidade"])
                if "PrecoMedio" in current_portfolio_df.columns:
                    current_portfolio_df["PrecoMedio"] = pd.to_numeric(current_portfolio_df["PrecoMedio"])
                else: # Adicionar PrecoMedio como 0 se não existir, para consistência
                    current_portfolio_df["PrecoMedio"] = 0.0 
                
                user_portfolio = current_portfolio_df[["Ticker", "Quantidade", "PrecoMedio"]].to_dict(orient="records")
                st.write("Carteira Atual Carregada:")
                st.dataframe(current_portfolio_df)
            except Exception as e:
                st.error(f"Erro ao processar o CSV da carteira atual: {e}")
                return
        else:
            st.error("CSV da carteira deve conter as colunas 'Ticker' e 'Quantidade'. 'PrecoMedio' é opcional.")
            return
    else:
        st.info("Aguardando upload da carteira atual.")
        return

    st.subheader("2. Valor do Novo Aporte")
    new_contribution_value = st.number_input("Valor do Novo Aporte (R$):", min_value=0.0, value=1000.0, step=100.0, key="new_contribution_val")

    st.subheader("3. Cenário Macroeconômico (para ponderação setorial)")
    selic_sug = st.number_input("Taxa Selic Atual (% a.a.):", value=10.5, min_value=0.0, max_value=30.0, step=0.25, format="%.2f", key="selic_sug") / 100
    inflation_sug = st.number_input("Inflação IPCA Acumulada 12 meses (%):", value=3.9, min_value=-5.0, max_value=20.0, step=0.1, format="%.1f", key="ipca_sug") / 100
    gdp_sug = st.number_input("Crescimento do PIB Esperado (% a.a.):", value=2.0, min_value=-10.0, max_value=10.0, step=0.1, format="%.1f", key="gdp_sug") / 100
    current_macro_scenario_sug = {"selic": selic_sug, "inflation": inflation_sug, "gdp_growth": gdp_sug}

    if st.button("Gerar Sugestões de Aporte", key="run_contribution_suggestion"):
        if not user_portfolio:
            st.error("Faça o upload da sua carteira atual primeiro.")
            return
        if new_contribution_value <= 0:
            st.error("O valor do novo aporte deve ser positivo.")
            return

        with st.spinner("Analisando carteira e gerando sugestões..."):
            try:
                # Para PortfolioSuggestor, precisamos de informações de setor para cada ticker.
                # Isso pode vir de uma API ou de um mapeamento manual.
                # Por simplicidade, vamos assumir que yf_client.get_stock_info pode ter "sector"
                # ou teremos um mapeamento fixo para demonstração.
                # Esta parte precisaria de uma fonte de dados de setor robusta.
                
                # Mock: Obter setores (idealmente, isso seria mais robusto)
                tickers_in_portfolio = [item["Ticker"] for item in user_portfolio]
                stock_infos_for_sectors = {}
                st.write("Obtendo informações de setor para os tickers (pode levar um momento)...")
                for ticker in tickers_in_portfolio:
                    info = yf_client.get_stock_info(ticker)
                    if info and isinstance(info, dict):
                        stock_infos_for_sectors[ticker] = info
                    else:
                        st.warning(f"Não foi possível obter info (e setor) para {ticker}. Será ignorado na análise setorial.")
                
                # Criar o PortfolioSuggestor
                # O PortfolioSuggestor precisa de ValuationModels para avaliar as ações.
                suggestor = PortfolioSuggestorClass(user_portfolio_list=user_portfolio, 
                                                  yf_client=yf_client, 
                                                  macro_economic_analyzer=macro_analyzer, 
                                                  valuation_models_class=ValuationModelsClass,
                                                  stock_infos_with_sector=stock_infos_for_sectors) # Passar infos para setor
                
                suggestions_df = suggestor.suggest_contributions(
                    contribution_amount=new_contribution_value,
                    current_macro_scenario=current_macro_scenario_sug,
                    num_suggestions=5 # Pode ser um input do usuário
                )

                if suggestions_df is not None and not suggestions_df.empty:
                    st.subheader("Sugestões de Aporte")
                    st.dataframe(suggestions_df)
                    st.markdown("**Colunas:**")
                    st.markdown("- `Ticker`: Ação sugerida.")
                    st.markdown("- `Valor Sugerido (R$)`: Montante a ser aportado na ação.")
                    st.markdown("- `Quantidade Sugerida`: Número de ações (aproximado)." )
                    st.markdown("- `Preço Atual (R$)`: Cotação usada para cálculo.")
                    st.markdown("- `Score Final`: Pontuação combinada (setor, valuation, etc.). Scores mais altos são melhores.")
                    st.markdown("- `Justificativa`: Breve resumo dos fatores.")
                else:
                    st.info("Não foi possível gerar sugestões de aporte com os critérios atuais. Tente ajustar o cenário ou a carteira.")
            except Exception as e:
                st.error(f"Erro ao gerar sugestões de aporte: {e}")
                st.exception(e)

    st.markdown("---_---")
    st.markdown("**Metodologia (Simplificada):**")
    st.markdown("- Analisa a exposição setorial da sua carteira atual.")
    st.markdown("- Identifica setores favorecidos pelo cenário macroeconômico.")
    st.markdown("- Busca ações com valuation atrativo (ex: Graham, Bazin) dentro dos setores priorizados ou para diversificação.")
    st.markdown("- Sugere aportes para equilibrar a carteira e/ou aproveitar oportunidades.")

# Adicionar mais componentes conforme necessário para outras seções.

if __name__ == "__main__":
    st.title("Teste de Componentes da UI")
    # Exemplo de como um componente pode ser testado ou visualizado isoladamente
    # st.subheader("Teste de Upload de Arquivo")
    # portfolio_df = render_data_upload_section()
    # if portfolio_df is not None:
    #     st.write("Pré-visualização do DataFrame carregado:")
    #     st.dataframe(portfolio_df.head())
    
    # Para testar seções específicas, você precisaria mockar os clientes de API
    # ou ter uma forma de injetá-los.
    # Ex: render_valuation_section(MockYahooFinanceAPI(), MockValuationModels)
    st.info("Este arquivo contém componentes de UI. Execute app.py para ver o aplicativo completo.")

