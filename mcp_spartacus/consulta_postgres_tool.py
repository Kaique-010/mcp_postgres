from langchain.tools import tool
from sql_generator import gerar_sql_da_pergunta
from executores import executar_sql_com_slug

@tool
def consulta_postgres_tool(pergunta: str, slug: str) -> list:
    """
    Executa uma consulta no banco PostgreSQL com base em uma pergunta em linguagem natural.
    """
    try:
        sql = gerar_sql_da_pergunta(pergunta, slug)
        resultado = executar_sql_com_slug(sql, slug)
        return resultado  # Retorna a lista diretamente
    except Exception as e:
        return [{"erro": f"Erro ao processar: {str(e)}"}]