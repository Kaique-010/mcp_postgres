from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from sql_generator import gerar_sql_da_pergunta
from executores import executar_sql_com_slug
from dotenv import load_dotenv

load_dotenv()

# Inicializar LLM
llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")

@tool
def consultar_banco_dados(pergunta: str) -> str:
    """
    Executa uma consulta no banco PostgreSQL com base em uma pergunta em linguagem natural.
    Retorna os dados brutos para que o agente possa interpretar.
    """
    try:
        sql = gerar_sql_da_pergunta(pergunta, "default")
        resultado = executar_sql_com_slug(sql, "default")
        
        if not resultado:
            return "Nenhum resultado encontrado para esta consulta."
        
        # Formatar os dados de forma estruturada para o agente
        dados_formatados = f"SQL executado: {sql}\n\nResultados encontrados ({len(resultado)} registros):\n"
        
        for i, item in enumerate(resultado[:10], 1):  # Limitar a 10 para não sobrecarregar
            dados_formatados += f"\nRegistro {i}:\n"
            for chave, valor in item.items():
                dados_formatados += f"  {chave}: {valor}\n"
        
        if len(resultado) > 10:
            dados_formatados += f"\n... e mais {len(resultado) - 10} registros."
            
        return dados_formatados
        
    except Exception as e:
        return f"Erro ao executar consulta: {str(e)}"

# Template do prompt para o agente - versão simplificada
template_agente = """Você é um assistente especializado em análise de dados de um sistema de vendas.

Você tem acesso a ferramentas para consultar o banco de dados PostgreSQL.
Use essas ferramentas quando precisar de dados para responder perguntas.

Após obter os dados, analise-os e forneça uma resposta clara e útil em português.

Você tem acesso às seguintes ferramentas:

{tools}

Use o seguinte formato:

Question: a pergunta de entrada
Thought: você deve sempre pensar sobre o que fazer
Action: a ação a tomar, deve ser uma das [{tool_names}]
Action Input: a entrada para a ação
Observation: o resultado da ação
... (este Thought/Action/Action Input/Observation pode se repetir N vezes)
Thought: Agora sei a resposta final
Final Answer: a resposta final para a pergunta original

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

# Criar o prompt
prompt = PromptTemplate.from_template(template_agente)

# Criar o agente
tools = [consultar_banco_dados]
agent = create_react_agent(llm, tools, prompt)

# Criar o executor do agente
agent_executor = AgentExecutor(
    agent=agent, 
    tools=tools, 
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=5,
    early_stopping_method="generate"
)

def processar_pergunta_com_agente(pergunta: str) -> str:
    """
    Processa uma pergunta usando o agente inteligente
    """
    try:
        resultado = agent_executor.invoke({"input": pergunta})
        return resultado.get("output", "Não foi possível processar a pergunta.")
    except Exception as e:
        return f"Erro no agente: {str(e)}"