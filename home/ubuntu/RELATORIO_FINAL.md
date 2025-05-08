# Relatório Final: Aplicativo de Análise de Investimentos em Ações Brasileiras

## 1. Introdução

Este documento descreve o aplicativo Python com Streamlit desenvolvido para auxiliar na análise fundamentalista, quantitativa e macroeconômica de investimentos em ações brasileiras. A plataforma visa fornecer uma ferramenta robusta e intuitiva para investidores, desde o acompanhamento de carteiras até a otimização de novos aportes e avaliação de ativos.

O aplicativo foi construído de forma modular, permitindo a fácil manutenção e expansão futura de suas funcionalidades. A interface gráfica foi desenvolvida com Streamlit, buscando uma experiência de usuário acessível mesmo para aqueles com conhecimento intermediário em finanças e programação.

## 2. Funcionalidades Implementadas

O aplicativo contempla as seguintes funcionalidades principais, conforme solicitado:

1.  **Backtest da Carteira:**
    *   Permite ao usuário definir uma carteira (via upload de CSV ou entrada manual de tickers e pesos).
    *   Realiza o backtest histórico da carteira desde uma data especificada (padrão 01/01/2015) até uma data final.
    *   Compara o desempenho da carteira com um benchmark escolhido pelo usuário (ex: IBOVESPA - `^BVSP`).
    *   Gera um relatório detalhado em HTML (utilizando a biblioteca `quantstats`) com métricas de desempenho, gráficos de evolução patrimonial, drawdowns, retornos mensais, entre outros.

2.  **Recomendações de Ações por Cenário Macroeconômico:**
    *   O usuário pode inserir manualmente os principais indicadores macroeconômicos (Taxa Selic, Inflação IPCA, Crescimento do PIB).
    *   Com base nesses indicadores e em um dicionário de sensibilidade setorial pré-definido, o sistema sugere setores potencialmente favorecidos.
    *   Apresenta um score de atratividade para cada setor analisado.

3.  **Sugestão de Aportes:**
    *   O usuário faz o upload de sua carteira atual (CSV com Ticker, Quantidade e, opcionalmente, Preço Médio).
    *   Informa o valor do novo aporte que deseja realizar.
    *   Define o cenário macroeconômico (Selic, IPCA, PIB) para ponderação setorial.
    *   O sistema analisa a carteira atual, identifica setores sub-representados ou atrativos no cenário atual e busca oportunidades com valuation interessante (utilizando modelos como Graham e Bazin).
    *   Sugere uma lista de ações para o aporte, com valores e quantidades, e uma justificativa baseada no score combinado de atratividade setorial e valuation.

4.  **Análise de Valuation de Ações:**
    *   Permite ao usuário inserir o ticker de uma ação brasileira (ex: `PETR4.SA`).
    *   Calcula e exibe diversas métricas de valuation para a ação selecionada:
        *   Número de Graham.
        *   Valor Patrimonial por Ação (VPA).
        *   Preço Teto (segundo a fórmula de Décio Bazin, com yield alvo de 6%).
        *   Modelo de Desconto de Dividendos (DDM - Gordon Growth Model), com taxas de retorno e crescimento ajustáveis pelo usuário.
        *   Fluxo de Caixa Descontado (DCF) - Implementado de forma simplificada/placeholder, destacando a necessidade de premissas robustas para um cálculo preciso.
        *   Múltiplos de mercado: P/L, P/VP, P/S, EV/EBITDA, PEG Ratio (quando disponíveis na API).
    *   Apresenta as margens de segurança em relação ao preço atual para os modelos de Graham, Bazin e DDM.

5.  **Montagem e Otimização de Carteira:**
    *   O usuário faz o upload de um arquivo CSV com os preços históricos de fechamento ajustado dos ativos que deseja incluir na otimização.
    *   Permite a escolha entre diferentes modelos de otimização de portfólio:
        *   **Fronteira Eficiente (Markowitz):** Com opções para maximizar o Índice de Sharpe, minimizar a volatilidade ou atingir um retorno alvo específico.
        *   **Paridade de Risco Hierárquica (HRP):** Modelo que não depende de estimativas de retorno esperado e foca na diversificação do risco.
        *   **Diversificação Máxima (Equal Weight):** Atribui pesos iguais a todos os ativos da carteira.
        *   **Simulação de Monte Carlo:** Gera um grande número de carteiras aleatórias para visualizar a fronteira eficiente e identificar carteiras ótimas (máximo Sharpe ou mínima volatilidade dentro da simulação).
    *   Exibe os pesos otimizados para cada ativo e a performance esperada da carteira (retorno, volatilidade, Índice de Sharpe).
    *   Para a Simulação de Monte Carlo, apresenta um gráfico interativo da fronteira eficiente.

6.  **Interface com Painel Intuitivo em Streamlit:**
    *   Navegação lateral para acessar os diferentes módulos do aplicativo.
    *   Upload de arquivos CSV para entrada de dados (carteira atual, preços históricos).
    *   Campos para entrada de valores numéricos (novo aporte, taxas, etc.) e texto (tickers).
    *   Seleção de modelos e critérios de otimização através de menus e botões de rádio.
    *   Visualização de resultados em tabelas formatadas e gráficos (quando aplicável, como no backtest e Monte Carlo).
    *   Explicações e descrições abaixo de cada seção para guiar o usuário.

## 3. Estrutura do Projeto

O projeto está organizado na pasta `invest_app` com a seguinte estrutura modular:

```
invest_app/
├── app.py                     # Arquivo principal da aplicação Streamlit
├── data_collection/           # Módulos para coleta de dados
│   ├── __init__.py
│   ├── yahoo_finance_api.py   # Interface com API Yahoo Finance (via Datasource ou yfinance)
│   └── other_apis.py          # Interface com outras APIs (ex: WorldBank via Datasource, FMP)
├── analysis/                  # Módulos para lógicas de análise
│   ├── __init__.py
│   ├── backtesting.py         # Lógica de backtest de carteira (usa quantstats)
│   ├── valuation.py           # Modelos de valuation (Graham, Bazin, DDM, DCF, Múltiplos)
│   ├── macro_analysis.py      # Análise de cenário macroeconômico e sensibilidade setorial
│   └── portfolio_analyzer.py  # Lógica para sugestão de aportes
├── optimization/              # Módulos para otimização de carteira (usa PyPortfolioOpt)
│   ├── __init__.py
│   ├── markowitz.py           # Otimização pela Fronteira Eficiente de Markowitz
│   ├── hrp.py                 # Otimização por Hierarchical Risk Parity
│   ├── max_diversification.py # Otimização por Máxima Diversificação (Equal Weight)
│   └── monte_carlo.py         # Otimização por Simulação de Monte Carlo
├── ui/                        # Módulos relacionados à interface do usuário
│   ├── __init__.py
│   └── components.py          # Componentes reutilizáveis da UI Streamlit para cada seção
├── utils/                     # Módulos utilitários (se necessário)
│   ├── __init__.py
│   └── helpers.py             # Funções auxiliares gerais (atualmente vazio)
├── reports/                   # Diretório para salvar relatórios gerados (ex: backtest.html)
└── todo.md                    # Arquivo de acompanhamento de tarefas (para desenvolvimento)
```

## 4. Como Executar o Aplicativo

### 4.1. Dependências

O aplicativo requer Python 3.9+ e as seguintes bibliotecas principais (além de suas dependências):

*   `streamlit`
*   `pandas`
*   `numpy`
*   `quantstats` (para backtesting)
*   `PyPortfolioOpt` (para otimização de carteira)
*   `yfinance` (como fallback se o Datasource do Yahoo Finance não estiver disponível ou para dados não cobertos)
*   `plotly` (para gráficos interativos na Simulação de Monte Carlo)

É recomendado criar um ambiente virtual para instalar as dependências:

```bash
python -m venv venv
source venv/bin/activate  # No Linux/macOS
# venv\Scripts\activate    # No Windows

pip install streamlit pandas numpy quantstats PyPortfolioOpt yfinance plotly
```

No ambiente Manus, as APIs de Datasource (`YahooFinance/get_stock_chart`, `YahooFinance/get_stock_insights`, `DataBank/indicator_data`) são acessadas através de um `ApiClient` injetado. O código foi preparado para utilizar este cliente quando disponível.

### 4.2. Executando

Após instalar as dependências e navegar para o diretório raiz do projeto (`invest_app`), execute o seguinte comando no terminal:

```bash
streamlit run app.py
```

Isso iniciará o servidor Streamlit e abrirá o aplicativo no seu navegador padrão.

## 5. Detalhes dos Módulos da Interface

Cada módulo da interface é projetado para ser intuitivo, com explicações e campos de entrada claros.

*   **Visão Geral:** Página inicial com a descrição do aplicativo.
*   **1. Backtest de Carteira:**
    *   Inputs: Definição da carteira (CSV ou manual), ticker do benchmark, datas de início e fim.
    *   Output: Relatório HTML interativo do `quantstats` embutido na página, com opção de download.
*   **2. Recomendações por Cenário:**
    *   Inputs: Taxa Selic, Inflação IPCA, Crescimento do PIB.
    *   Output: Tabela de setores favorecidos com seus scores de atratividade.
*   **3. Sugestão de Aportes:**
    *   Inputs: CSV da carteira atual, valor do novo aporte, cenário macroeconômico.
    *   Output: Tabela com sugestões de ações, valores, quantidades e justificativas.
*   **4. Análise de Valuation:**
    *   Inputs: Ticker da ação, parâmetros para DDM e DCF (ajustáveis via sliders).
    *   Output: Métricas de preço atual, valores calculados pelos modelos (Graham, Bazin, DDM, DCF, VPA), margens de segurança e tabela de múltiplos.
*   **5. Otimização de Carteira:**
    *   Inputs: CSV de preços históricos, escolha do modelo de otimização, taxa livre de risco, e parâmetros específicos do modelo (ex: tipo de otimização Markowitz, retorno alvo, número de simulações Monte Carlo).
    *   Output: Pesos otimizados, performance esperada da carteira. Gráfico da fronteira para Monte Carlo.

## 6. APIs e Fontes de Dados Utilizadas

*   **Yahoo Finance:** Utilizado extensivamente para obter dados históricos de preços de ações e benchmarks, além de informações fundamentalistas das empresas (LPA, VPA, dividendos, múltiplos, etc.). O acesso é primariamente através do `ApiClient` do Datasource (`YahooFinance/get_stock_chart`, `YahooFinance/get_stock_insights`) quando no ambiente Manus. Como fallback ou para dados não cobertos, a biblioteca `yfinance` pode ser utilizada (embora a implementação atual priorize o Datasource).
*   **DataBank (World Bank):** Para dados macroeconômicos (como PIB, inflação, etc.), o acesso pode ser feito via `ApiClient` do Datasource (`DataBank/indicator_data`). A implementação atual do módulo `macro_analysis.py` está preparada para isso, mas os inputs na UI são manuais para simplificar a demonstração.
*   **Financial Modeling Prep (FMP):** A estrutura para utilizar a API da FMP (para dados fundamentalistas adicionais ou demonstrativos financeiros) está presente no módulo `other_apis.py`, mas requer uma chave de API do usuário, que pode ser inserida opcionalmente na interface. Atualmente, não é um requisito central para as funcionalidades implementadas.

## 7. Limitações e Considerações

*   **Qualidade dos Dados:** A precisão das análises depende da qualidade e disponibilidade dos dados fornecidos pelas APIs. Eventuais inconsistências ou dados faltantes podem afetar os resultados.
*   **Modelos Financeiros:** Os modelos de valuation e otimização são baseados em premissas e simplificações. Os resultados são estimativas e não devem ser considerados como recomendações de investimento infalíveis. O modelo DCF, em particular, é uma versão simplificada e um DCF completo exigiria projeções financeiras detalhadas.
*   **Cenário Macroeconômico:** A análise de sensibilidade setorial é baseada em um dicionário pré-definido e pode não capturar todas as nuances do mercado.
*   **Dados de Setor:** A funcionalidade de sugestão de aportes depende da obtenção da informação de setor para cada ação da carteira do usuário. A implementação atual tenta obter isso via `stock_info` do Yahoo Finance, o que pode não ser sempre completo ou padronizado para todas as ações. Uma fonte de dados de classificação setorial mais robusta melhoraria essa funcionalidade.
*   **APIs Externas:** A disponibilidade e os termos de uso das APIs gratuitas (como Yahoo Finance via `yfinance`) podem mudar.
*   **Não é Recomendação de Investimento:** Este aplicativo é uma ferramenta de análise e aprendizado. Todas as decisões de investimento devem ser tomadas com base em uma análise individual e, se necessário, com o auxílio de um profissional qualificado.

## 8. Próximos Passos (Sugestões para Melhorias Futuras)

*   **Detecção Automática de Cenário Macroeconômico:** Integrar a coleta automática de dados macro (ex: via API do Banco Central do Brasil ou DataBank) para popular os campos de cenário.
*   **DCF Detalhado:** Permitir que o usuário insira premissas mais detalhadas para o modelo de Fluxo de Caixa Descontado.
*   **Análise de Risco Avançada:** Incorporar métricas de risco mais sofisticadas (ex: Value at Risk - VaR, Conditional VaR - CVaR).
*   **Comparação de Múltiplas Ações:** Facilitar a comparação lado a lado do valuation de várias ações.
*   **Alertas e Notificações:** Implementar um sistema de alertas para eventos de mercado ou quando ações atingem determinados patamares de valuation.
*   **Persistência de Dados do Usuário:** Permitir que os usuários salvem suas carteiras e configurações.
*   **Testes Unitários e de Integração Mais Abrangentes:** Embora o código tenha sido testado durante o desenvolvimento, a criação de um conjunto formal de testes automatizados aumentaria a robustez.

---
Fim do Relatório.

