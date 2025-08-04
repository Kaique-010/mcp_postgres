# tools/mcp_wrappers.py

import requests
from mcp_servers import MCP_VISUALIZATION_CONFIG

def usar_mcp_plotly(data: list[dict]) -> str:
    url = MCP_VISUALIZATION_CONFIG["graficos_interativos"]["plotly_generator"]["url"]
    response = requests.post(url, json={"data": data})
    return response.json().get("chart_url", "Erro ao gerar gráfico")


def usar_mcp_passos(texto: str) -> str:
    url = MCP_VISUALIZATION_CONFIG["passos_sequenciais"]["url"]
    response = requests.post(url, json={"input": texto})
    return response.json().get("passos", "Não foi possível quebrar em etapas")
