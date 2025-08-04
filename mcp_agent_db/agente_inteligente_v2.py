from typing import List, Dict, Any
from langgraph.prebuilt import create_react_agent
from langchain.prompts import PromptTemplate
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langchain.memory import ConversationBufferMemory
from langgraph.checkpoint.memory import MemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient
from mcp_servers import MCP_SERVERS_CONFIG
from sql_generator import gerar_sql_da_pergunta
from dotenv import load_dotenv
from consulta_tool import consulta_postgres_tool, consultar_banco_dados
import asyncio
import os
import django
from cache_manager import query_cache
from conversation_memory import conversation_memory
from consulta_tool import consultar_banco_dados
from sql_generator import gerar_sql_da_pergunta

load_dotenv()

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

# Inicializar componentes globais
model_llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")
memory = ConversationBufferMemory(memory_key="chat_history")
memory_saver = MemorySaver()


mcp_client = None
agent_executor = None

def validar_schema_ferramenta(tool) -> bool:
    """Valida se o schema da ferramenta é compatível com Gemini"""
    try:
        # Lista de ferramentas conhecidas como problemáticas
        ferramentas_problematicas = [
            'generate_fishbone_diagram',
            'generate_mind_map', 
            'generate_organization_chart',
            'generate_word_cloud_chart',
            'generate_flow_diagram',
            'generate_network_graph'
        ]
        
        # Rejeitar ferramentas conhecidas como problemáticas
        if tool.name in ferramentas_problematicas:
            return False
        
        # Verificar se a ferramenta tem schema
        if not hasattr(tool, 'args_schema') or tool.args_schema is None:
            return True
        
        # Converter schema para dict para análise
        try:
            schema_dict = tool.args_schema.model_json_schema() if hasattr(tool.args_schema, 'model_json_schema') else {}
        except Exception:
            return False
        
        # Verificar se há propriedades recursivas problemáticas
        def verificar_recursao(obj, profundidade=0):
            if profundidade > 3:  # Limite de profundidade mais restritivo
                return False
            
            if isinstance(obj, dict):
                # Verificar se há chave '$schema' problemática
                if '$schema' in obj:
                    return False
                    
                if 'properties' in obj:
                    for prop_name, prop_value in obj['properties'].items():
                        if isinstance(prop_value, dict):
                            # Verificar estruturas recursivas específicas
                            if 'items' in prop_value and isinstance(prop_value['items'], dict):
                                if 'properties' in prop_value['items']:
                                    # Verificar se há 'children' recursivos
                                    if 'children' in prop_value['items']['properties']:
                                        children_prop = prop_value['items']['properties']['children']
                                        if isinstance(children_prop, dict) and 'items' in children_prop:
                                            return False
                            
                            # Verificar recursivamente
                            if not verificar_recursao(prop_value, profundidade + 1):
                                return False
                                
                if 'items' in obj and isinstance(obj['items'], dict):
                    if not verificar_recursao(obj['items'], profundidade + 1):
                        return False
            
            return True
        
        return verificar_recursao(schema_dict)
        
    except Exception as e:
        print(f"⚠️ Erro ao validar schema da ferramenta {tool.name}: {e}")
        return False

def filtrar_ferramentas_validas(mcp_tools: List) -> List:
    """Filtra ferramentas MCP com schemas válidos - APENAS whitelist restrita"""
    ferramentas_validas = []
    ferramentas_removidas = []
    
    # Lista MUITO restrita de ferramentas básicas e seguras
    ferramentas_seguras = [
        'generate_bar_chart',
        'generate_pie_chart', 
        'generate_line_chart',
        'generate_column_chart'
    ]
    
    for tool in mcp_tools:
        # Usar APENAS whitelist - não validar outras
        if tool.name in ferramentas_seguras:
            ferramentas_validas.append(tool)
        else:
            ferramentas_removidas.append(tool.name)
    
    if ferramentas_removidas:
        print(f"⚠️ Ferramentas removidas (whitelist restrita): {len(ferramentas_removidas)} ferramentas")
    
    print(f"✅ Ferramentas válidas mantidas: {', '.join([t.name for t in ferramentas_validas])}")
    
    return ferramentas_validas

async def inicializar_agente():
    """Inicializa o agente com MCP client de forma assíncrona"""
    global mcp_client, agent_executor
    
    try:
        print("🔄 Inicializando MCP Client... ", MCP_SERVERS_CONFIG)
        
        # Inicializar MCP Client com a configuração correta
        mcp_client = MultiServerMCPClient(MCP_SERVERS_CONFIG)
        
        # Obter ferramentas do MCP client
        mcp_tools_raw = await mcp_client.get_tools()
        print(f"✅ {len(mcp_tools_raw)} ferramentas MCP obtidas")
        
        # Filtrar ferramentas com schemas válidos
        mcp_tools = filtrar_ferramentas_validas(mcp_tools_raw)
        print(f"✅ {len(mcp_tools)} ferramentas MCP válidas carregadas")
        
        # Listar ferramentas disponíveis
        for tool in mcp_tools:
            print(f"🔧 Ferramenta MCP: {tool.name}")
        
        print("🔄 Criando agente...")
        
        # Criar prompt personalizado com suporte a gráficos
        system_prompt = """Você é um analista de dados especializado em sistemas de gestão empresarial com capacidade de gerar visualizações.

INSTRUÇÕES CRÍTICAS:
1. Para perguntas sobre DADOS: use a ferramenta consultar_banco_dados
2. Para perguntas sobre GRÁFICOS: use as ferramentas MCP disponíveis para gerar gráficos
3. Faça APENAS UMA chamada da ferramenta por pergunta
4. NÃO tente múltiplas variações ou reformulações
5. NÃO pergunte detalhes ao usuário - os metadados já contêm as informações necessárias

FERRAMENTAS DISPONÍVEIS:
- consultar_banco_dados: Para consultas de dados do PostgreSQL
- Ferramentas MCP: Para criar gráficos interativos (generate_bar_chart, generate_pie_chart, etc.)

DETECÇÃO DE SOLICITAÇÕES DE GRÁFICO:
Se a pergunta contém palavras como: "gráfico", "grafico", "chart", "visualiza", "gere um gráfico", "criar gráfico"
→ Use as ferramentas MCP de gráficos disponíveis

METADADOS DISPONÍVEIS:
- Campo enti_tipo_enti na tabela entidades (CL=Cliente, VE=Vendedor, FO=Fornecedor)
- Tabelas: entidades, pedidosvenda, produtos, funcionarios
- Relacionamentos já mapeados nos metadados

FLUXO PARA GRÁFICOS:
1. Primeiro obtenha os dados com consultar_banco_dados
2. Depois use a ferramenta MCP apropriada
3. Formate os dados no padrão esperado pela ferramenta MCP

TIPOS DE GRÁFICO DISPONÍVEIS:
- generate_bar_chart: Gráfico de barras (padrão)
- generate_pie_chart: Gráfico de pizza
- generate_line_chart: Gráfico de linhas
- generate_column_chart: Gráfico de colunas

SEMPRE responda em português brasileiro e seja DIRETO."""

        # Incluir ferramentas MCP nas ferramentas do agente
        todas_ferramentas = [consultar_banco_dados, consulta_postgres_tool] + mcp_tools

        agent_executor = create_react_agent(
            model=model_llm,
            tools=todas_ferramentas,
            checkpointer=memory_saver,
            state_modifier=system_prompt
        )
        
        print("✅ Agente inicializado com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao inicializar MCP Client: {e}")
        print("🔄 Tentando modo fallback...")
        try:
            # Fallback: criar agente com ferramentas locais apenas
            system_prompt_fallback = """Você é um analista de dados especializado em sistemas de gestão empresarial.

INSTRUÇÕES IMPORTANTES:
1. Para consultas de dados: use consultar_banco_dados
2. Para gráficos: informe que a funcionalidade de gráficos está temporariamente indisponível
3. Para entidades por tipo, use o campo enti_tipo_enti (CL=Cliente, VE=Vendedor, etc.)
4. NÃO pergunte ao usuário sobre campos que estão nos metadados
5. SEMPRE consulte o banco de dados quando solicitado
6 - Se solicitado Pedidso por cliente, não usar o filtro de enti_tipo_enti, trazer todos, e discriminados por tipo da entidade

FERRAMENTAS DISPONÍVEIS:
- consultar_banco_dados: Para consultas de dados
- consulta_postgres_tool: Para consultas SQL diretas

METADADOS IMPORTANTES DISPONÍVEIS:
- Campo enti_tipo_enti na tabela entidades para classificar tipos
- Exemplos: 'CL' = Clientes, 'VE' = Vendedores


EXEMPLOS DE CONSULTAS:
- "entidades por tipo" → Use consultar_banco_dados com "entidades por tipo"
- "clientes" → Use consultar_banco_dados com "clientes"
- "pedidos por cliente" → Use consultar_banco_dados com "pedidos por cliente"

SEMPRE responda em português brasileiro e USE AS FERRAMENTAS DISPONÍVEIS."""

            agent_executor = create_react_agent(
                model=model_llm,
                tools=[consultar_banco_dados, consulta_postgres_tool],
                checkpointer=memory_saver,
                state_modifier=system_prompt_fallback
            )
            print("⚠️ Agente criado sem MCP tools (modo fallback)")
            return True
        except Exception as fallback_error:
            print(f"❌ Erro no fallback: {fallback_error}")
            return False

def inicializar_agente_sync():
    """Versão síncrona para inicializar o agente"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(inicializar_agente())
    except Exception as e:
        print(f"❌ Erro na inicialização síncrona: {e}")
        return False

def processar_pergunta_com_agente_v2(pergunta: str) -> str:
    """Processa pergunta usando o agente inteligente v2 com contexto melhorado"""
    global agent_executor
    
    try:
        # Verificar se agente está inicializado
        if agent_executor is None:
            print("🔄 Inicializando agente...")
            if not inicializar_agente_sync():
                return "❌ Erro: Não foi possível inicializar o agente."
        
        print(f"\n🤖 Processando: {pergunta}")
        print("=" * 50)
        
        # Detectar se é uma solicitação de gráfico
        palavras_grafico = ['gráfico', 'grafico', 'chart', 'visualiza', 'gere um gráfico', 'criar gráfico']
        eh_solicitacao_grafico = any(palavra in pergunta.lower() for palavra in palavras_grafico)
        
        # Criar prompt mais direto e específico
        if eh_solicitacao_grafico:
            pergunta_com_contexto = f"""
            {pergunta}
            
            INSTRUÇÕES PARA GRÁFICOS:
            1. Use OBRIGATORIAMENTE as ferramentas MCP disponíveis para criar os gráficos
            2. Primeiro obtenha os dados com consultar_banco_dados se necessário
            3. Depois use a ferramenta MCP de gráficos com os dados obtidos
            4. Use tipo de gráfico "bar" como padrão
            5. Responda em português brasileiro
            
            FLUXO: dados → ferramenta MCP de gráficos → resposta com gráfico
            """
        else:
            pergunta_com_contexto = f"""
            {pergunta}
            
            INSTRUÇÕES PARA DADOS:
            1. Use a ferramenta consultar_banco_dados para obter os dados
            2. Faça UMA única chamada da ferramenta
            3. NÃO tente múltiplas variações da consulta
            4. Responda em português brasileiro
            5. Se houver erro de SQL, informe o erro diretamente
            """
        
        # Configurar thread_id para o checkpointer
        config = {"configurable": {"thread_id": "main_conversation"}}
        
        resultado = agent_executor.invoke({
            "messages": [{"role": "user", "content": pergunta_com_contexto}]
        }, config=config)
        
        # Extrair resposta do resultado
        resposta = ""
        if isinstance(resultado, dict):
            if "messages" in resultado and len(resultado["messages"]) > 0:
                ultima_mensagem = resultado["messages"][-1]
                
                # Tentar diferentes formas de extrair o conteúdo
                if hasattr(ultima_mensagem, 'content'):
                    resposta = ultima_mensagem.content
                elif isinstance(ultima_mensagem, dict) and 'content' in ultima_mensagem:
                    resposta = ultima_mensagem['content']
                else:
                    resposta = str(ultima_mensagem)
            else:
                resposta = str(resultado)
        else:
            resposta = str(resultado)
        
        print(f"\n✅ Resposta final gerada!")
        return resposta if resposta else "❌ Não foi possível gerar uma resposta."
        
    except Exception as e:
        error_msg = f"❌ Erro no agente: {str(e)}"
        print(error_msg)
        return error_msg

def processar_pergunta_com_streaming_sync(pergunta: str) -> dict:
    """Versão síncrona para streaming"""
    try:
        resposta = processar_pergunta_com_agente_v2(pergunta)
        return {
            "pergunta": pergunta,
            "resposta": resposta,
            "status": "sucesso",
            "etapas_executadas": 5
        }
    except Exception as e:
        return {
            "pergunta": pergunta,
            "resposta": f"Erro: {str(e)}",
            "status": "erro",
            "etapas_executadas": 0
        }

def gerar_sql(pergunta: str, slug: str = "casaa") -> str:
    """Função auxiliar para gerar SQL"""
    return gerar_sql_da_pergunta(pergunta, slug)

# Inicializar agente na importação (opcional)
if __name__ == "__main__":
    print("🚀 Testando inicialização do agente...")
    sucesso = inicializar_agente_sync()
    if sucesso:
        print("✅ Agente pronto para uso!")
    else:
        print("⚠️ Agente em modo fallback")