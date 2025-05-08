# -*- coding: utf-8 -*-
"""
Módulo de funções auxiliares e utilitários.

Contém funções genéricas que podem ser usadas em diferentes partes do aplicativo,
como formatação de datas, tratamento de strings, cálculos comuns não específicos
de um módulo de análise ou otimização, etc.
"""

import pandas as pd
from datetime import datetime

__version__ = "0.0.1"
__author__ = "Manus AI Agent"
__email__ = ""

def format_date_br(date_obj: datetime) -> str:
    """Formata um objeto datetime para o padrão brasileiro DD/MM/YYYY."""
    if isinstance(date_obj, datetime):
        return date_obj.strftime("%d/%m/%Y")
    return str(date_obj) # Retorna como string se não for datetime

def parse_brazilian_ticker(ticker: str) -> str:
    """
    Garante que o ticker brasileiro para Yahoo Finance termine com ".SA".
    Exemplos: PETR4 -> PETR4.SA, MGLU3 -> MGLU3.SA.
    Se já tiver .SA, não faz nada.
    """
    if isinstance(ticker, str) and not ticker.upper().endswith(".SA"):
        return ticker.upper() + ".SA"
    return ticker.upper() if isinstance(ticker, str) else ticker

def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Calcula a variação percentual entre dois valores."""
    if old_value == 0:
        return float("inf") if new_value > 0 else (float("-inf") if new_value < 0 else 0.0)
    return ((new_value - old_value) / old_value) * 100

# Outras funções utilitárias podem ser adicionadas aqui.

if __name__ == "__main__":
    print(f"PETR4 formatado: {parse_brazilian_ticker(\'petr4\')}")
    print(f"ITUB4.SA formatado: {parse_brazilian_ticker(\'ITUB4.SA\')}")
    print(f"Data formatada: {format_date_br(datetime.now())}")
    print(f"Variação percentual (100 para 120): {calculate_percentage_change(100, 120):.2f}%")
    print(f"Variação percentual (100 para 80): {calculate_percentage_change(100, 80):.2f}%")

