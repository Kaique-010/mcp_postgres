from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from sql_generator import gerar_sql_da_pergunta
from schema_loader import carregar_schema
from executores import executar_sql_com_slug
from dotenv import load_dotenv
import asyncio
import os
import django
from cache_manager import query_cache
from conversation_memory import conversation_memory
from tools.plotly_tool import gerar_grafico_com_plotly

load_dotenv()

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

# Inicializa o LLM
llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")

@tool
def consultar_banco_dados(pergunta: str, slug: str = "casaa") -> str:
    """Consulta o banco de dados com cache e memória"""
    try:
        print(f"🔍 Processando: {pergunta}")
        
        # 1. Verificar cache primeiro
        cached_result = query_cache.get(pergunta, slug)
        if cached_result:
            # Adicionar à memória conversacional
            conversation_memory.add_interaction(
                pergunta=pergunta,
                resposta=cached_result,
                sql="[CACHED]",
                resultado=cached_result
            )
            return cached_result
        
        # 2. Carregar schema
        schema = carregar_schema(slug)
        if not schema:
            return f"❌ Erro: Schema não encontrado para '{slug}'"
        
        print(f"✅ Schema carregado: {slug} ({len(schema)} tabelas)")
        
        # 3. Adicionar contexto conversacional ao prompt
        pergunta_com_contexto = pergunta + conversation_memory.get_context_prompt()
        
        # 4. Gerar SQL
        print(f"🔍 Gerando SQL para: {pergunta}")
        sql = gerar_sql_da_pergunta(pergunta_com_contexto, slug)
        print(f"📝 SQL gerado: {sql}")
        
        # 5. Executar consulta
        resultado = executar_sql_com_slug(sql, slug)
        print(f"✅ Consulta executada - {len(resultado)} registros encontrados")
        
        # 6. Formatar resultado
        if len(resultado) == 0:
            resposta_formatada = "📊 Nenhum registro encontrado para esta consulta."
        else:
            # Detectar se tem campos de empresa/filial
            tem_empresa_filial = any(
                any(campo in str(item.keys()).lower() for campo in ['empr', 'fili'])
                for item in resultado
            )
            
            if tem_empresa_filial:
                resposta_formatada = formatar_resultado_por_empresa(resultado, sql)
            else:
                resposta_formatada = formatar_resultado_simples(resultado, sql)
        
        # 7. Armazenar no cache
        query_cache.set(pergunta, slug, resposta_formatada, sql)
        
        # 8. Adicionar à memória conversacional
        conversation_memory.add_interaction(
            pergunta=pergunta,
            resposta=resposta_formatada,
            sql=sql,
            resultado=resultado
        )
        
        # 9. Adicionar sugestões
        suggestions = conversation_memory.get_suggestions()
        if suggestions:
            resposta_formatada += "\n\n💡 **Sugestões para próximas consultas:**\n"
            for i, suggestion in enumerate(suggestions, 1):
                resposta_formatada += f"{i}. {suggestion}\n"
        
        return resposta_formatada
        
    except Exception as e:
        error_msg = f"❌ Erro interno na ferramenta: {str(e)}"
        print(error_msg)
        return error_msg

def formatar_resultado_por_empresa(resultado, sql):
    """Formata resultados separando por empresa/filial"""
    dados_formatados = f"SQL: {sql}\n\n📊 RESULTADOS ({len(resultado)} registros):\n"
    
    # Agrupar por empresa/filial
    empresas = {}
    for item in resultado:
        # Encontrar campos de empresa e filial
        empr_key = next((k for k in item.keys() if 'empr' in str(k).lower()), None)
        fili_key = next((k for k in item.keys() if 'fili' in str(k).lower()), None)
        
        empr_val = item.get(empr_key, 'N/A') if empr_key else 'N/A'
        fili_val = item.get(fili_key, 'N/A') if fili_key else 'N/A'
        
        chave_empresa = f"Empresa {empr_val} - Filial {fili_val}"
        
        if chave_empresa not in empresas:
            empresas[chave_empresa] = []
        empresas[chave_empresa].append(item)
    
    # Formatar por empresa
    for empresa, registros in empresas.items():
        dados_formatados += f"\n🏢 {empresa}:\n"
        
        for i, item in enumerate(registros[:10], 1):
            dados_formatados += f"\n  🔸 Registro {i}:\n"
            for chave, valor in item.items():
                # Melhor detecção de campos monetários vs contagens
                if isinstance(valor, (int, float)):
                    # Campos que são claramente contagens (não monetários)
                    if any(x in chave.lower() for x in ['total_pedidos', 'total_vendas', 'total_clientes', 'total_produtos', 'quantidade', 'qtd', 'count']):
                        dados_formatados += f"     {chave}: {valor:,.0f}\n"
                    # Campos monetários
                    elif any(x in chave.lower() for x in ['prec', 'cust', 'valo', 'total_valor', 'valor_total']):
                        dados_formatados += f"     {chave}: R$ {valor:,.2f}\n"
                    else:
                        dados_formatados += f"     {chave}: {valor}\n"
                else:
                    dados_formatados += f"     {chave}: {valor}\n"
        
        if len(registros) > 10:
            dados_formatados += f"\n  ... e mais {len(registros) - 10} registros para esta empresa.\n"
    
    return dados_formatados

def formatar_resultado_simples(resultado, sql):
    """Formata resultados simples sem separação por empresa"""
    dados_formatados = f"SQL: {sql}\n\n📊 RESULTADOS ({len(resultado)} registros):\n"
    
    for i, item in enumerate(resultado[:15], 1):
        dados_formatados += f"\n🔸 Registro {i}:\n"
        for chave, valor in item.items():
            # Melhor detecção de campos monetários vs contagens
            if isinstance(valor, (int, float)):
                # Campos que são claramente contagens (não monetários)
                if any(x in chave.lower() for x in ['total_pedidos', 'total_vendas', 'total_clientes', 'total_produtos', 'quantidade', 'qtd', 'count']):
                    dados_formatados += f"   {chave}: {valor:,.0f}\n"
                # Campos monetários
                elif any(x in chave.lower() for x in ['prec', 'cust', 'valo', 'total_valor', 'valor_total']):
                    dados_formatados += f"   {chave}: R$ {valor:,.2f}\n"
                else:
                    dados_formatados += f"   {chave}: {valor}\n"
            else:
                dados_formatados += f"   {chave}: {valor}\n"
    
    if len(resultado) > 15:
        dados_formatados += f"\n... e mais {len(resultado) - 15} registros."
        
    return dados_formatados

# Template do agente
template_agente = """Você é um analista de dados especializado em sistemas de gestão.

Você tem acesso às seguintes ferramentas:
{tools}

Use este formato:
Question: a pergunta de entrada
Thought: meu raciocínio sobre o que preciso fazer
Action: a ação a tomar, deve ser uma das [{tool_names}]
Action Input: pergunta em linguagem natural para o banco
Observation: resultado da consulta
Thought: análise dos resultados
Final Answer: resposta final formatada EM PORTUGUÊS

IMPORTANTE: 
- SEMPRE responda em português brasileiro
- Use formatação clara e objetiva
- Seja preciso nos números e dados apresentados
- Mantenha um tom profissional e amigável
- Sempre que possível sirva o maior numero de informações 
- Se for uma informação relevante, gere insights
- Passar sugestões para as próximas perguntas.
- Se a pergunta não estiver clara, pergunte ao usuário para.claro.

Question: {input}
Thought:{agent_scratchpad}"""

# Criar o agente
prompt = PromptTemplate.from_template(template_agente)
tools = [consultar_banco_dados, gerar_grafico_com_plotly]
agent = create_react_agent(llm, tools, prompt)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    return_intermediate_steps=False,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=8,
    
)

def processar_pergunta_com_agente_v2(pergunta: str) -> str:
    """Processa pergunta usando o agente inteligente v2"""
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

def processar_pergunta_com_streaming_sync(pergunta: str) -> str:
    """Versão síncrona para streaming"""
    return processar_pergunta_com_agente_v2(pergunta)

def gerar_sql(pergunta: str, slug: str = "casaa") -> str:
    """Função auxiliar para gerar SQL"""
    return gerar_sql_da_pergunta(pergunta, slug)