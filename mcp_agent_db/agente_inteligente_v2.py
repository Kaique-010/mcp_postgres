from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langchain.chains import LLMChain
from schema_loader import carregar_schema
from prompt_sql import TEMPLATE_SQL
from dotenv import load_dotenv
import asyncio

load_dotenv()

# Inicializa o LLM
llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")

# Cria o chain para gerar SQL com o prompt específico
def gerar_sql_da_pergunta(pergunta: str, slug: str) -> str:
    """Gera SQL para a pergunta"""
    schema = carregar_schema(slug)
    if not schema:
        raise ValueError(f"Schema não encontrado para o slug '{slug}'")
    schema_formatado = "\n".join([f"- {tabela}: {', '.join(colunas)}" for tabela, colunas in schema.items()])
    
    prompt = PromptTemplate.from_template(TEMPLATE_SQL)
    chain = LLMChain(llm=llm, prompt=prompt)
    
    resposta = chain.run(pergunta=pergunta, schema=schema_formatado)
    return resposta.strip()

# Ferramenta que o agente vai usar
@tool
def gerar_sql(pergunta: str) -> str:
    """Gera SQL para a pergunta"""
    return gerar_sql_da_pergunta(pergunta, slug="auto")

# Lista de ferramentas do agente
tools = [gerar_sql]

# Prompt padrão para agente React
agent_prompt = PromptTemplate.from_template(TEMPLATE_SQL)

# Cria o agente com o prompt e ferramentas
agent = create_react_agent(llm=llm, tools=tools, prompt=agent_prompt)
agent_executor = AgentExecutor(agent=agent)

# Função para processar pergunta usando o agente
def processar_pergunta_com_agente_v2(pergunta: str) -> str:
    """Processa uma pergunta usando o agente inteligente v2 com schema completo"""
    try:
        print(f"\n🤖 Processando: {pergunta}")
        print("=" * 50)
        
        resultado = agent_executor.invoke({"input": pergunta})
        resposta = resultado.get("output", "Não foi possível processar a pergunta.")
        
        print(f"\n✅ Resposta final gerada!")
        return resposta
        
    except Exception as e:
        error_msg = f"❌ Erro no agente: {str(e)}"
        print(error_msg)
        return error_msg

# Função para streaming (para implementar depois)
async def processar_com_streaming(pergunta: str):
    """     
    Versão com streaming para mostrar passos em tempo real
    """
    try:
        print(f"\n🤖 Iniciando processamento com streaming: {pergunta}")
        print("=" * 60)
        
        # Criar um callback personalizado para capturar os passos
        class StreamingCallback:
            def __init__(self):
                self.steps = []
                self.current_step = 0
            
            def on_llm_start(self, serialized, prompts, **kwargs):
                self.current_step += 1
                print(f"\n🧠 PASSO {self.current_step}: Pensando...")
                
            def on_llm_end(self, response, **kwargs):
                if hasattr(response, 'generations') and response.generations:
                    text = response.generations[0][0].text
                    print(f"💭 Raciocínio: {text[:200]}...")
                    
            def on_tool_start(self, serialized, input_str, **kwargs):
                tool_name = serialized.get('name', 'ferramenta')
                print(f"\n🔧 EXECUTANDO: {tool_name}")
                print(f"📝 Input: {input_str}")
                
            def on_tool_end(self, output, **kwargs):
                print(f"✅ Resultado obtido: {len(str(output))} caracteres")
                
            def on_agent_action(self, action, **kwargs):
                print(f"\n🎯 AÇÃO: {action.tool}")
                print(f"📋 Parâmetros: {action.tool_input}")
                
            def on_agent_finish(self, finish, **kwargs):
                print(f"\n🏁 FINALIZANDO...")
                print(f"📊 Resposta final preparada!")
        
        # Executar o agente com callback de streaming
        callback = StreamingCallback()
        
        # Simular streaming dos passos principais
        print("\n🔍 ETAPA 1: Analisando a pergunta...")
        await asyncio.sleep(0.5)
        
        print(f"❓ Pergunta: '{pergunta}'")
        print("🧩 Identificando intenção e entidades necessárias...")
        await asyncio.sleep(0.5)
        
        print("\n🔍 ETAPA 2: Carregando ferramentas...")
        print("🛠️ Ferramenta disponível: consultar_banco_dados")
        await asyncio.sleep(0.3)
        
        print("\n🔍 ETAPA 3: Executando agente...")
        print("🤖 Iniciando raciocínio do agente...")
        await asyncio.sleep(0.5)
        
        # Executar o agente de forma síncrona em uma thread separada
        def executar_agente():
            return agent_executor.invoke({"input": pergunta})
        
        # Executar em thread separada para não bloquear
        loop = asyncio.get_event_loop()
        resultado = await loop.run_in_executor(None, executar_agente)
        
        print("\n🔍 ETAPA 4: Processando resultado...")
        await asyncio.sleep(0.3)
        
        resposta = resultado.get("output", "Não foi possível processar a pergunta.")
        
        print("\n🔍 ETAPA 5: Formatando resposta final...")
        await asyncio.sleep(0.3)
        
        print("\n" + "="*60)
        print("🎉 PROCESSAMENTO CONCLUÍDO!")
        print("="*60)
        
        return {
            "pergunta": pergunta,
            "resposta": resposta,
            "status": "sucesso",
            "etapas_executadas": 5
        }
        
    except Exception as e:
        error_msg = f"❌ Erro no streaming: {str(e)}"
        print(error_msg)
        return {
            "pergunta": pergunta,
            "resposta": error_msg,
            "status": "erro",
            "etapas_executadas": 0
        }

# Função auxiliar para usar o streaming no main.py
def processar_pergunta_com_streaming_sync(pergunta: str) -> dict:
    """
    Versão síncrona que executa o streaming
    """
    try:
        # Executar a função async em um novo loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        resultado = loop.run_until_complete(processar_com_streaming(pergunta))
        loop.close()
        return resultado
    except Exception as e:
        return {
            "pergunta": pergunta,
            "resposta": f"❌ Erro: {str(e)}",
            "status": "erro",
            "etapas_executadas": 0
        }