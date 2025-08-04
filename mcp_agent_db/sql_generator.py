from langchain.prompts import ChatPromptTemplate
from langchain.chat_models import init_chat_model
from schema_loader import carregar_schema, formatar_schema_para_prompt
from prompt_sql import TEMPLATE_SQL
from dotenv import load_dotenv
import re

load_dotenv()

llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")

def gerar_sql_da_pergunta(pergunta: str, slug: str) -> str:
    """Gera SQL para a pergunta usando schema do cliente"""
    schema = carregar_schema(slug)
    if not schema:
        raise ValueError(f"Schema não encontrado para o slug '{slug}'")
    
    schema_formatado = formatar_schema_para_prompt(schema)
    
    prompt = ChatPromptTemplate.from_template(TEMPLATE_SQL)
    chain = prompt | llm
    
    resposta = chain.invoke({"pergunta": pergunta, "schema": schema_formatado})
    
    # Extrair o texto da resposta
    if hasattr(resposta, 'content'):
        sql_texto = resposta.content
    else:
        sql_texto = str(resposta)
    
    # Limpar a resposta removendo marcadores markdown
    sql_limpo = sql_texto.strip()
    sql_limpo = re.sub(r'```sql\s*', '', sql_limpo)
    sql_limpo = re.sub(r'```\s*', '', sql_limpo)
    
    return sql_limpo.strip()