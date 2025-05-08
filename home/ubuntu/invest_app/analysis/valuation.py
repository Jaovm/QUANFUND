# -*- coding: utf-8 -*-
"""
Módulo para análise de valuation de ações.

Implementa diversas abordagens de valuation:
- Fluxo de Caixa Descontado (DCF) - Estrutura e necessita de dados de projeção
- Análise por Múltiplos (P/L, P/VP, EV/EBITDA, etc.)
- Modelo de Graham (Número de Graham)
- Modelo de Bazin (Preço Justo por Dividendos) - Simplificado
- Modelo de Desconto de Dividendos (DDM) - Gordon Growth Model
- Análise por Valor Patrimonial por Ação (VPA)
"""

import pandas as pd
import numpy as np

__version__ = "0.0.2"
__author__ = "Manus AI Agent"
__email__ = ""

class ValuationModels:
    """Classe para calcular o valor de ações usando diferentes modelos."""

    def __init__(self, stock_info_data: dict, financial_statements: dict = None):
        """
        Inicializa com dados da ação e, opcionalmente, demonstrativos financeiros.

        Args:
            stock_info_data (dict): Dicionário com informações da ação (ex: yf.Ticker("TICKER.SA").info).
                                    Contém preços, dividendos, LPA, VPA, beta, etc.
            financial_statements (dict, optional): Dicionário contendo DataFrames para balanço,
                                                 DRE, e fluxo de caixa. Ex: 
                                                 {
                                                     "balance_sheet": pd.DataFrame(...),
                                                     "income_statement": pd.DataFrame(...),
                                                     "cash_flow": pd.DataFrame(...)
                                                 }
                                                 Estes são necessários para modelos como o DCF.
        """
        self.stock_info = {k: v for k, v in stock_info_data.items() if isinstance(v, (int, float, str, bool))} 
        self.financials = financial_statements if financial_statements else {}

    def get_current_price(self) -> float | None:
        """Retorna o preço de mercado atual da ação."""
        for key in ["regularMarketPrice", "currentPrice", "previousClose"]:
            price = self.stock_info.get(key)
            if price is not None and isinstance(price, (int, float)):
                return float(price)
        return None

    def graham_valuation(self) -> float | None:
        """Calcula o Número de Graham. Fórmula: sqrt(22.5 * LPA * VPA). Retorna None se dados insuficientes."""
        eps = self.stock_info.get("trailingEps")
        bvps = self.stock_info.get("bookValue")
        if eps is not None and bvps is not None and isinstance(eps, (int, float)) and isinstance(bvps, (int, float)):
            if eps > 0 and bvps > 0:
                try:
                    return (22.5 * eps * bvps)**0.5
                except (TypeError, ValueError):
                    return None
        return None

    def vpa_analysis(self) -> float | None:
        """Retorna o Valor Patrimonial por Ação (VPA / BVPS)."""
        bvps = self.stock_info.get("bookValue")
        return float(bvps) if isinstance(bvps, (int, float)) else None

    def bazin_valuation_simplified(self, required_yield: float = 0.06) -> float | None:
        """Calcula o preço justo pela fórmula simplificada de Décio Bazin. Fórmula: Dividendo Anual / Yield Requerido."""
        annual_dividend_per_share = self.stock_info.get("trailingAnnualDividendRate")
        if annual_dividend_per_share is None:
            dividend_yield = self.stock_info.get("dividendYield")
            current_price = self.get_current_price()
            if dividend_yield is not None and current_price is not None and isinstance(dividend_yield, (int, float)) and isinstance(current_price, (int, float)):
                annual_dividend_per_share = dividend_yield * current_price
            else:
                return None
        
        if annual_dividend_per_share is not None and isinstance(annual_dividend_per_share, (int, float)) and annual_dividend_per_share > 0 and required_yield > 0:
            try:
                return annual_dividend_per_share / required_yield
            except (TypeError, ValueError, ZeroDivisionError):
                return None
        return None

    def ddm_gordon_growth(self, required_rate_of_return: float, perpetual_growth_rate: float) -> float | None:
        """Modelo de Desconto de Dividendos (Gordon Growth Model).
           Fórmula: D1 / (k - g), onde D1 = D0 * (1 + g).
           D0 é o dividendo anual mais recente por ação.
           k é a taxa de retorno requerida (custo do capital próprio).
           g é a taxa de crescimento perpétuo dos dividendos.
        """
        d0 = self.stock_info.get("trailingAnnualDividendRate")
        if d0 is None or not isinstance(d0, (int, float)) or d0 < 0:
            # Tentar calcular D0 a partir do dividendYield e preço, se D0 não explícito
            yield_val = self.stock_info.get("dividendYield")
            price = self.get_current_price()
            if yield_val is not None and price is not None and isinstance(yield_val, (int,float)) and isinstance(price, (int,float)):
                d0 = yield_val * price
            else:
                return None # Não foi possível obter D0
        
        if d0 is None or not isinstance(d0, (int, float)) or d0 < 0: return None # Checagem final de D0

        if not (isinstance(required_rate_of_return, (int, float)) and isinstance(perpetual_growth_rate, (int, float))):
            return None
        if required_rate_of_return <= perpetual_growth_rate:
            # print("Taxa de retorno requerida deve ser maior que a taxa de crescimento para o DDM.")
            return None # Modelo não aplicável

        d1 = d0 * (1 + perpetual_growth_rate)
        try:
            value = d1 / (required_rate_of_return - perpetual_growth_rate)
            return value if value > 0 else None # Preço não pode ser negativo
        except (ZeroDivisionError, TypeError, ValueError):
            return None

    def get_multiples(self) -> dict:
        """Retorna múltiplos comuns se os dados estiverem disponíveis."""
        multiples = {}
        eps = self.stock_info.get("trailingEps")
        price = self.get_current_price()
        bvps = self.vpa_analysis()

        if price is not None and eps is not None and isinstance(eps, (int, float)) and eps != 0:
            multiples["P/L"] = price / eps
        if price is not None and bvps is not None and isinstance(bvps, (int, float)) and bvps != 0:
            multiples["P/VP"] = price / bvps
        
        for key_yf, key_display in {
            "forwardPE": "P/L Projetivo", 
            "priceToSalesTrailing12Months": "P/S", 
            "enterpriseToEbitda": "EV/EBITDA",
            "pegRatio": "PEG Ratio"
        }.items():
            val = self.stock_info.get(key_yf)
            if val is not None and isinstance(val, (int, float)):
                multiples[key_display] = val
        return multiples

    def dcf_valuation_placeholder(self, discount_rate_wacc: float, 
                                  projection_years: int = 5, 
                                  short_term_growth_rate: float = 0.05, 
                                  long_term_growth_rate: float = 0.02) -> float | None:
        """ Placeholder para Fluxo de Caixa Descontado (DCF).
            Uma implementação real requer projeções de FCFE ou FCFF, que vêm de análise profunda
            dos demonstrativos financeiros e premissas de crescimento.
        Args:
            discount_rate_wacc (float): Custo Médio Ponderado de Capital (WACC).
            projection_years (int): Anos de projeção explícita do fluxo de caixa.
            short_term_growth_rate (float): Taxa de crescimento do FCF nos anos de projeção.
            long_term_growth_rate (float): Taxa de crescimento na perpetuidade.
        Returns:
            float | None: Valor intrínseco por ação estimado, ou None se não implementado.
        """
        # Para uma implementação real, precisaríamos:
        # 1. Último FCFE (Fluxo de Caixa para o Acionista) ou FCFF (Fluxo de Caixa da Firma).
        #    - FCFE = FCFF - Despesas de Juros * (1 - Imposto) + Novas Dívidas - Amortização de Dívidas
        #    - FCFF = EBIT * (1 - Imposto) + Depreciação/Amortização - CAPEX - Variação no Capital de Giro
        #    Estes dados viriam de self.financials["cash_flow"], self.financials["income_statement"].
        # 2. Projetar FCFE/FCFF para `projection_years` usando `short_term_growth_rate`.
        # 3. Calcular o valor terminal (TV) usando `long_term_growth_rate`:
        #    TV = FCF_ultimo_ano_proj * (1 + long_term_growth_rate) / (discount_rate_wacc - long_term_growth_rate)
        # 4. Descontar os FCFs projetados e o TV para o presente usando `discount_rate_wacc`.
        # 5. Somar os valores presentes para obter o valor total da firma (se FCFF) ou do equity (se FCFE).
        # 6. Se usou FCFF, subtrair o valor de mercado da dívida líquida para obter o valor do equity.
        # 7. Dividir o valor do equity pelo número de ações em circulação.
        #    num_shares = self.stock_info.get("sharesOutstanding")
        
        # Exemplo muito simplificado (NÃO USAR PARA DECISÕES REAIS - APENAS ILUSTRATIVO DA ESTRUTURA)
        last_fcfe_example = self.stock_info.get("trailingEps", 1.0) * self.stock_info.get("sharesOutstanding", 1e9) if self.stock_info.get("trailingEps") else 1e9 # Apenas um proxy grosseiro
        if not isinstance(last_fcfe_example, (int,float)): last_fcfe_example = 1e9
        
        projected_fcfes = []
        current_fcfe = last_fcfe_example
        for year in range(1, projection_years + 1):
            current_fcfe *= (1 + short_term_growth_rate)
            projected_fcfes.append(current_fcfe / ((1 + discount_rate_wacc)**year))
        
        terminal_value_num = current_fcfe * (1 + long_term_growth_rate)
        terminal_value_den = discount_rate_wacc - long_term_growth_rate
        if terminal_value_den <= 0: return None # WACC deve ser maior que g_longo
        
        terminal_value = terminal_value_num / terminal_value_den
        pv_terminal_value = terminal_value / ((1 + discount_rate_wacc)**projection_years)
        
        total_equity_value = sum(projected_fcfes) + pv_terminal_value
        num_shares = self.stock_info.get("sharesOutstanding")
        if num_shares and isinstance(num_shares, (int,float)) and num_shares > 0:
            return total_equity_value / num_shares
        
        print("DCF valuation é um placeholder e requer dados financeiros detalhados e premissas robustas.")
        return None # Indicar que é um placeholder ou cálculo incompleto

    def get_all_valuations(self, ddm_k: float = 0.12, ddm_g: float = 0.03, dcf_wacc: float = 0.10, dcf_g_st: float = 0.07, dcf_g_lt: float = 0.02) -> dict:
        """Retorna um resumo de todos os valuations calculados e múltiplos.
           Valores default para taxas do DDM e DCF são exemplificativos.
        """
        current_price = self.get_current_price()
        valuations = {
            "Ticker": self.stock_info.get("symbol", "N/A"),
            "Preço Atual": current_price,
            "Graham Number": self.graham_valuation(),
            "VPA (Valor Patrimonial por Ação)": self.vpa_analysis(),
            "Bazin (Yield 6%)": self.bazin_valuation_simplified(required_yield=0.06),
            "DDM (k=12%, g=3%)": self.ddm_gordon_growth(required_rate_of_return=ddm_k, perpetual_growth_rate=ddm_g),
            "DCF (Simplificado)": self.dcf_valuation_placeholder(discount_rate_wacc=dcf_wacc, short_term_growth_rate=dcf_g_st, long_term_growth_rate=dcf_g_lt),
            "Múltiplos": self.get_multiples()
        }
        
        # Adicionar margens de segurança
        for model_key in ["Graham Number", "Bazin (Yield 6%)", "DDM (k=12%, g=3%)", "DCF (Simplificado)"]:
            model_value = valuations.get(model_key)
            if current_price and model_value and isinstance(model_value, (int, float)) and current_price > 0:
                margin_key = f"Margem Seg. {model_key.split('(')[0].strip()} (%)"
                valuations[margin_key] = ((model_value / current_price) - 1) * 100
        
        # Formatação final
        formatted_valuations = {}
        for k, v in valuations.items():
            if v is None or v == {}: continue # Pula valores nulos ou dicts vazios
            if isinstance(v, (float, np.floating)):
                if "Margem" in k:
                    formatted_valuations[k] = f"{v:.2f}%"
                else:
                    formatted_valuations[k] = f"{v:.2f}"
            elif isinstance(v, dict) and k == "Múltiplos":
                formatted_multiples = {m_k: (f"{m_v:.2f}" if isinstance(m_v, (float, np.floating)) else m_v) for m_k, m_v in v.items() if m_v is not None}
                if formatted_multiples: formatted_valuations[k] = formatted_multiples
            else:
                formatted_valuations[k] = v
        return formatted_valuations

if __name__ == "__main__":
    mock_petr4_info = {
        "symbol": "PETR4.SA", "regularMarketPrice": 30.50, "trailingEps": 7.50, 
        "bookValue": 25.20, "dividendYield": 0.10, "trailingAnnualDividendRate": 3.05,
        "forwardPE": 5.5, "priceToSalesTrailing12Months": 0.8, "enterpriseToEbitda": 3.2,
        "sharesOutstanding": 6000000000, "beta": 1.2
    }
    valuation_petr4 = ValuationModels(stock_info_data=mock_petr4_info)
    print(f"--- Valuation para {mock_petr4_info['symbol']} ---")
    all_vals_petr4 = valuation_petr4.get_all_valuations(ddm_k=0.15, ddm_g=0.05, dcf_wacc=0.12, dcf_g_st=0.08, dcf_g_lt=0.03)
    for key, val in all_vals_petr4.items():
        print(f"  {key}: {val}")

    mock_mglu3_info = {
        "symbol": "MGLU3.SA", "regularMarketPrice": 2.50, "trailingEps": -0.20,
        "bookValue": 1.50, "dividendYield": 0.00, "trailingAnnualDividendRate": 0.0,
        "forwardPE": -10.0, "priceToSalesTrailing12Months": 0.5, "sharesOutstanding": 1000000000
    }
    valuation_mglu3 = ValuationModels(stock_info_data=mock_mglu3_info)
    print(f"\n--- Valuation para {mock_mglu3_info['symbol']} ---")
    all_vals_mglu3 = valuation_mglu3.get_all_valuations()
    for key, val in all_vals_mglu3.items():
        print(f"  {key}: {val}")

    mock_wege3_info = {
        "symbol": "WEGE3.SA", "regularMarketPrice": 38.00, "trailingEps": 1.20,
        "bookValue": 5.50, "dividendYield": 0.015, "trailingAnnualDividendRate": 0.57,
        "forwardPE": 25.0, "priceToSalesTrailing12Months": 4.0, "enterpriseToEbitda": 20.0,
        "sharesOutstanding": 2090000000, "beta": 0.8
    }
    # Supondo que temos dados financeiros para WEGE3 para um DCF mais elaborado (não usado no placeholder atual)
    # mock_financials_wege3 = { "income_statement": pd.DataFrame(...), ... }
    valuation_wege3 = ValuationModels(stock_info_data=mock_wege3_info)
    print(f"\n--- Valuation para {mock_wege3_info['symbol']} ---")
    all_vals_wege3 = valuation_wege3.get_all_valuations(ddm_k=0.10, ddm_g=0.07, dcf_wacc=0.09, dcf_g_st=0.10, dcf_g_lt=0.04)
    for key, val in all_vals_wege3.items():
        print(f"  {key}: {val}")

