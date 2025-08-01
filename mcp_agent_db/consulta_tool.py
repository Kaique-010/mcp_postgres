from langchain.tools import tool
from .agente_inteligente_v2 import gerar_sql_da_pergunta
from .schema_loader import carregar_schema
from .executores import executar_sql_com_slug

@tool
def consulta_postgres_tool(pergunta: str, slug: str) -> str:
    """
    Responde perguntas sobre dados do banco PostgreSQL com base no slug da empresa.
    """

    try:
        # Valida se schema existe
        schema = carregar_schema(slug)
        if not schema:
            return f"❌ Não foi possível encontrar o schema do banco para o slug '{slug}'."

        # Gera SQL com base na pergunta e schema real
        sql = gerar_sql_da_pergunta(pergunta, slug)

        # Executa SQL
        resposta = executar_sql_com_slug(sql, slug)

        return resposta

    except Exception as e:
        return f"❌ Erro ao processar consulta: {str(e)}"
