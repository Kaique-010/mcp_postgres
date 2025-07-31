from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langchain.memory import ConversationBufferMemory
from sql_generator import gerar_sql_da_pergunta
from executores import executar_sql_com_slug
from dotenv import load_dotenv
import asyncio

load_dotenv()

# Inicializar LLM
llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")

# Schema completo do banco
SCHEMA_COMPLETO = """
=== SCHEMA COMPLETO DO BANCO DE DADOS ===

📋 TABELA: pedidosvenda
   - pedi_nume: INTEGER PRIMARY KEY (número único do pedido)
   - pedi_empr: INTEGER (código da empresa - 1, 2, 3...)
   - pedi_fili: INTEGER (código da filial - 1, 2, 3...)
   - pedi_forn: INTEGER (código do cliente/entidade - FK para entidades)
   - pedi_vend: INTEGER (código do vendedor - FK para entidades)
   - pedi_data: DATE (data do pedido)
   - pedi_tota: DECIMAL(15,2) (valor total do pedido)
   - pedi_stat: VARCHAR (status: 'A'=Aberto, 'F'=Fechado, 'C'=Cancelado)

📦 TABELA: itenspedidovenda
   - iped_pedi: INTEGER (número do pedido - FK)
   - iped_item: INTEGER (sequência do item)
   - iped_prod: INTEGER (código do produto - FK)
   - iped_quan: DECIMAL(15,3) (quantidade)
   - iped_unit: DECIMAL(15,2) (preço unitário)
   - iped_tota: DECIMAL(15,2) (valor total do item)

🛍️ TABELA: produtos
   - prod_codi: INTEGER PRIMARY KEY (código único do produto)
   - prod_nome: VARCHAR(100) (nome do produto)


👥 TABELA: entidades
   - enti_clie: INTEGER PRIMARY KEY (código único da entidade)
   - enti_nome: VARCHAR(100) (nome/razão social)
   - enti_tipo_enti: VARCHAR(2) (tipo da entidade)
   - enti_cida: VARCHAR(50) (cidade)
   - enti_esta: VARCHAR(2) (estado - UF)

🏷️ TIPOS DE ENTIDADE (enti_tipo_enti):
   - 'CL': Cliente
   - 'VE': Vendedor
   - 'FO': Fornecedor
   - 'TR': Transportadora
   - 'FU': Funcionário

🔗 RELACIONAMENTOS:
   - pedidosvenda.pedi_forn → entidades.enti_clie (entidade do pedido - QUALQUER TIPO)
   - pedidosvenda.pedi_vend → entidades.enti_clie (vendedor do pedido)
   - itenspedidovenda.iped_pedi → pedidosvenda.pedi_nume
   - itenspedidovenda.iped_prod → produtos.prod_codi


📊 CONSULTAS COMUNS:
   - Vendedores: SELECT * FROM entidades WHERE enti_tipo_enti = 'VE'
   - Pedidos com entidade: JOIN pedidosvenda pv ON pv.pedi_forn = entidades.enti_clie
   - Itens de pedido: JOIN itenspedidovenda ipv ON ipv.item_pedi = pv.pedi_nume

⚠️ IMPORTANTE PARA "PEDIDOS POR CLIENTE":
   - NUNCA filtrar por enti_tipo_enti quando perguntarem sobre "pedidos por cliente"
   - Usar: SELECT e.enti_nome, COUNT(pv.pedi_nume) FROM pedidosvenda pv JOIN entidades e ON pv.pedi_forn = e.enti_clie GROUP BY e.enti_nome
   - Mostrar TODAS as entidades que têm pedidos, independente do tipo
   - Clientes: SELECT * FROM entidades WHERE enti_tipo_enti = 'CL'
   - Pedidos com cliente: JOIN pedidosvenda pv ON pv.pedi_clie = entidades.enti_codi
   - Itens de pedido: JOIN itenspedidovenda ipv ON ipv.item_pedi = pv.pedi_nume
"""


@tool
def consultar_banco_dados(pergunta: str) -> str:
    """
    Executa uma consulta no banco PostgreSQL com base em uma pergunta em linguagem natural.
    Usa o schema completo para gerar SQL preciso.
    """
    try:
        print(f"🔍 Gerando SQL para: {pergunta}")
        sql = gerar_sql_da_pergunta(pergunta, "default")
        print(f"📝 SQL gerado: {sql}")
        
        resultado = executar_sql_com_slug(sql, "default")
        print(f"✅ Consulta executada - {len(resultado)} registros encontrados")
        
        if not resultado:
            return "❌ Nenhum resultado encontrado para esta consulta."
        
        # Formatar os dados de forma estruturada
        dados_formatados = f"SQL: {sql}\n\n📊 RESULTADOS ({len(resultado)} registros):\n"
        
        for i, item in enumerate(resultado[:15], 1):  # Mostrar até 15 registros
            dados_formatados += f"\n🔸 Registro {i}:\n"
            for chave, valor in item.items():
                if isinstance(valor, (int, float)) and any(x in chave.lower() for x in ['tota', 'prec', 'cust']):
                    dados_formatados += f"   {chave}: R$ {valor:,.2f}\n"
                else:
                    dados_formatados += f"   {chave}: {valor}\n"
        
        if len(resultado) > 15:
            dados_formatados += f"\n... e mais {len(resultado) - 15} registros."
            
        return dados_formatados
        
    except Exception as e:
        error_msg = f"❌ Erro ao executar consulta: {str(e)}"
        print(error_msg)
        return error_msg

# Template corrigido com todas as variáveis necessárias
template_agente = f"""Você é um analista de dados especializado em sistemas de vendas multi-empresa.

CONHECIMENTO DO BANCO:
{SCHEMA_COMPLETO}

INSTRUÇÕES:
- Use a ferramenta consultar_banco_dados quando precisar de dados
- Sempre explique seu raciocínio passo a passo
- Formate números monetários adequadamente
- Destaque insights importantes
- Use emojis para deixar a resposta mais clara

Você tem acesso às seguintes ferramentas:

{{tools}}

Use este formato EXATO:

Question: a pergunta de entrada
Thought: meu raciocínio sobre o que preciso fazer
Action: a ação a tomar, deve ser uma das [{{tool_names}}]
Action Input: pergunta em linguagem natural para o banco
Observation: resultado da consulta
Thought: análise dos resultados
Final Answer: resposta final formatada e com insights

Question: {{input}}
Thought:{{agent_scratchpad}}"""

# Criar o agente sem memória (removendo o warning)
prompt = PromptTemplate.from_template(template_agente)
tools = [consultar_banco_dados]
agent = create_react_agent(llm, tools, prompt)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=5,
    early_stopping_method="generate"
)

def processar_pergunta_com_agente_v2(pergunta: str) -> str:
    """
    Processa uma pergunta usando o agente inteligente v2 com schema completo
    """
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