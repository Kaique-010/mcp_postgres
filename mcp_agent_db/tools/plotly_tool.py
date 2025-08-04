from langchain.tools import tool
from tools.mcp_wrappers import usar_mcp_plotly
import json

@tool
def gerar_grafico_com_plotly(dados: str | list[dict]) -> str:
    """
    Gera um gráfico interativo com Plotly.
    Aceita string JSON ou lista de dicionários como entrada.
    """
    try:
        # Se for string, tenta converter pra lista
        if isinstance(dados, str):
            dados = json.loads(dados)

        if not isinstance(dados, list) or not isinstance(dados[0], dict):
            return "⚠️ Entrada inválida. Esperado: lista de dicionários com colunas e valores."

        # Gera gráfico e retorna URL ou caminho
        chart_url = usar_mcp_plotly(dados)
        return f"📊 Gráfico gerado com sucesso: {chart_url}"

    except Exception as e:
        return f"❌ Erro ao gerar gráfico: {str(e)}"
