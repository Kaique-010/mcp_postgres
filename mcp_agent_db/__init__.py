
"""
MCP Agent DB - Ferramenta de consulta de bases de dados usando linguagem natural
"""

__version__ = "1.0.3"
__author__ = "Leonardo Sousa"
__email__ = "leokaique7@gmail.com"

# Importações principais para facilitar o uso
from .consulta_tool import consultar_banco_dados, consulta_postgres_tool
from .agente_inteligente_v2 import processar_pergunta_com_agente_v2

__all__ = [
    'consultar_banco_dados',
    'consulta_postgres_tool', 
    'processar_pergunta_com_agente_v2'
]
