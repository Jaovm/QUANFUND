# Lista de Tarefas: Aplicativo de Análise de Investimentos

## Etapa 1: Definir Estrutura Modular do Aplicativo (Concluído)
- [x] Planejar a organização das pastas e arquivos do projeto.
- [x] Definir as principais classes e funções para cada módulo (coleta de dados, backtesting, valuation, otimização, interface).
- [x] Esboçar o fluxo de dados entre os módulos.

## Etapa 2: Coletar Dados de Ações e Macro (Concluído)
- [x] Implementar a coleta de dados históricos de ações brasileiras (Yahoo Finance, Financial Modeling Prep ou similar).
- [x] Implementar a coleta de dados de benchmarks (ex: IBOV).
- [x] Implementar a coleta de dados macroeconômicos relevantes (ex: taxa de juros, inflação).
- [x] Definir como os dados serão armazenados e acessados (ex: CSV, Parquet, banco de dados SQLite).

## Etapa 3: Implementar Backtest Comparativo (Concluído)
- [x] Desenvolver a lógica para calcular o retorno da carteira ao longo do tempo (desde 01/01/2015).
- [x] Implementar a comparação do desempenho da carteira com benchmarks (ex: IBOV).
- [x] Gerar gráficos e tabelas para visualização dos resultados do backtest.

## Etapa 4: Criar Módulo de Recomendação Setorial e Macro (Concluído)
- [x] Desenvolver um dicionário de sensibilidade setorial ao cenário macroeconômico.
- [x] Implementar a lógica para identificar o cenário macroeconômico atual (automático ou manual).
- [x] Gerar recomendações de setores com base no cenário e na sensibilidade setorial.

## Etapa 5: Desenvolver Sugestão de Aportes Baseada na Carteira (Concluído)
- [x] Permitir o upload da carteira atual do usuário.
- [x] Analisar a carteira atual e identificar setores sub-representados ou atrativos.
- [x] Identificar oportunidades de valuation atrativo dentro dos setores priorizados.
- [x] Sugerir aportes para rebalancear a carteira e aproveitar oportunidades.

## Etapa 6: Integrar Abordagens de Valuation Múltipla (Concluído)
- [x] Implementar o modelo de Fluxo de Caixa Descontado (DCF).
- [x] Implementar a análise por múltiplos (P/L, P/VP, EV/EBITDA, etc.).
- [x] Implementar o modelo de Graham (Número de Graham).
- [x] Implementar o modelo de Bazin (Preço Justo por Dividendos).
- [x] Implementar o Modelo de Desconto de Dividendos (DDM).
- [x] Implementar a análise por Valor Patrimonial por Ação (VPA).
- [x] Consolidar as diferentes métricas de valuation para uma análise completa.

## Etapa 7: Implementar Otimização de Carteira com Modelos Vários (Concluído)
- [x] Implementar o modelo da Fronteira Eficiente (Markowitz).
- [x] Implementar o modelo de Paridade de Risco Hierárquica (HRP).
- [x] Implementar o modelo de Diversificação Máxima.
- [x] Implementar a Simulação de Monte Carlo para otimização estocástica.
- [x] Permitir que o usuário escolha o modelo de otimização.

## Etapa 8: Criar Interface Streamlit com Painéis e Uploads (Concluído)
- [x] Desenvolver a estrutura principal da interface com Streamlit.
- [x] Criar a funcionalidade de upload da carteira atual do usuário (ex: arquivo CSV).
- [x] Criar campos para entrada do valor do novo aporte.
- [x] Implementar a seleção dos critérios de otimização.
- [x] Desenvolver a visualização de gráficos da carteira antes e depois da otimização.
- [x] Criar tabelas comparativas de alocação atual vs. sugerida.
- [x] Adicionar explicações e descrições em cada seção da interface.

## Etapa 9: Validar Funcionalidades e Fluxo do App (Concluído)
- [x] Realizar testes unitários e de integração para cada módulo.
- [x] Testar o fluxo completo do aplicativo com dados de exemplo.
- [x] Coletar feedback e realizar ajustes necessários.

## Etapa 10: Reportar e Entregar Código ao Usuário (Em Andamento)
- [ ] Organizar e comentar todo o código fonte.
- [ ] Preparar um relatório final descrevendo o aplicativo, suas funcionalidades e como utilizá-lo.
- [ ] Entregar o código fonte completo e o relatório ao usuário.
