from langchain.prompts import ChatPromptTemplate
from langchain.chat_models import init_chat_model
from relacionamento_registry import TABELAS_CONHECIDAS
from prompt_sql import prompt_sql
from dotenv import load_dotenv
import re

load_dotenv()

llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")
prompt = ChatPromptTemplate.from_template(prompt_sql)

# Usar RunnableSequence ao invés de LLMChain (depreciado)
chain = prompt | llm

def gerar_sql_da_pergunta(pergunta: str, slug: str) -> str:
    # Usar invoke com os parâmetros corretos
    resposta = chain.invoke({"pergunta": pergunta, "tabelas": TABELAS_CONHECIDAS})
    
    # Extrair o texto da resposta (pode ser string ou objeto)
    if hasattr(resposta, 'content'):
        sql_texto = resposta.content
    else:
        sql_texto = str(resposta)
    
    # Limpar a resposta removendo marcadores markdown e texto extra
    sql_limpo = sql_texto.strip()
    
    # Remover marcadores de código markdown
    sql_limpo = re.sub(r'```sql\s*', '', sql_limpo)
    sql_limpo = re.sub(r'```\s*', '', sql_limpo)
    
    # Remover quebras de linha extras e espaços
    sql_limpo = sql_limpo.strip()
    
    # Se houver múltiplas linhas, pegar apenas a primeira consulta SQL válida
    linhas = sql_limpo.split('\n')
    sql_final = ""
    
    for linha in linhas:
        linha = linha.strip()
        if linha and not linha.startswith('#') and not linha.startswith('--'):
            sql_final += linha + " "
    
    return sql_final.strip()
