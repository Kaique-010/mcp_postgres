from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain.tools import tool
import json
import logging
from .llm_config import llm
from .mcp_servers import MCP_SERVERS_CONFIG, MCP_DEV_CONFIG, MCP_VISUALIZATION_CONFIG
from .consulta_tool import ConsultaTool
from .model_tool_factory import ModelToolFactory
from .model_registry import MODELS_MCP
from .relacionamento_registry import RELACIONAMENTOS_MCP
from .filtros_naturais import FILTROS_NATURAIS

logger = logging.getLogger(__name__)

class WorkflowState(TypedDict):
    """Estado do workflow LangGraph"""
    messages: Annotated[List[BaseMessage], "Lista de mensagens"]
    query: str
    sql_generated: str
    db_results: List[Dict[str, Any]]
    mcp_tools_used: List[str]
    final_response: str
    error: str
    needs_visualization: bool
    visualization_type: str

class MCPLangGraphWorkflow:
    """Workflow LangGraph integrado com MCPs para consultas SQL inteligentes"""
    
    def __init__(self):
        self.llm = llm
        self.factory = ModelToolFactory(
            slug="mcp",
            models=MODELS_MCP,
            relacionamentos=RELACIONAMENTOS_MCP,
            alias_filtros=FILTROS_NATURAIS
        )
        self.consulta_tool = ConsultaTool(factory=self.factory, llm=self.llm)
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> StateGraph:
        """Cria o workflow LangGraph"""
        workflow = StateGraph(WorkflowState)
        
        # Adicionar nós
        workflow.add_node("analyze_query", self.analyze_query)
        workflow.add_node("select_mcp_tools", self.select_mcp_tools)
        workflow.add_node("generate_sql", self.generate_sql)
        workflow.add_node("execute_query", self.execute_query)
        workflow.add_node("check_visualization", self.check_visualization)
        workflow.add_node("generate_visualization", self.generate_visualization)
        workflow.add_node("format_response", self.format_response)
        workflow.add_node("handle_error", self.handle_error)
        
        # Definir fluxo
        workflow.set_entry_point("analyze_query")
        
        workflow.add_edge("analyze_query", "select_mcp_tools")
        workflow.add_edge("select_mcp_tools", "generate_sql")
        workflow.add_edge("generate_sql", "execute_query")
        
        # Condicionais
        workflow.add_conditional_edges(
            "execute_query",
            self._should_handle_error,
            {
                "error": "handle_error",
                "success": "check_visualization"
            }
        )
        
        workflow.add_conditional_edges(
            "check_visualization",
            self._should_visualize,
            {
                "visualize": "generate_visualization",
                "format": "format_response"
            }
        )
        
        workflow.add_edge("generate_visualization", "format_response")
        workflow.add_edge("format_response", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile()
    
    def analyze_query(self, state: WorkflowState) -> WorkflowState:
        """Analisa a query do usuário e identifica intenções"""
        query = state["query"]
        
        analysis_prompt = f"""
        Analise a seguinte consulta e identifique:
        1. Tipo de consulta (relatório, análise, busca simples)
        2. Se precisa de visualização (gráfico, dashboard)
        3. Complexidade (simples, média, alta)
        4. Entidades envolvidas (clientes, produtos, vendedores, pedidos)
        
        Consulta: {query}
        
        Responda em JSON com as chaves: tipo, visualizacao_necessaria, complexidade, entidades
        """
        
        try:
            analysis = self.llm.invoke(analysis_prompt).content
            # Parse do JSON se possível
            if analysis.startswith('{'):
                analysis_data = json.loads(analysis)
                state["needs_visualization"] = analysis_data.get("visualizacao_necessaria", False)
                state["visualization_type"] = analysis_data.get("tipo", "relatorio")
        except Exception as e:
            logger.warning(f"Erro na análise da query: {e}")
            state["needs_visualization"] = False
        
        state["messages"].append(HumanMessage(content=query))
        return state
    
    def select_mcp_tools(self, state: WorkflowState) -> WorkflowState:
        """Seleciona quais MCPs usar baseado na análise"""
        query = state["query"].lower()
        selected_tools = []
        
        # Lógica de seleção de MCPs baseada na query
        if any(word in query for word in ["passo", "sequencial", "etapa"]):
            selected_tools.append("passos_sequenciais")
        
        if any(word in query for word in ["buscar", "pesquisar", "encontrar"]):
            selected_tools.append("buscas_relevantes")
        
        if any(word in query for word in ["api", "integração", "contexto"]):
            selected_tools.append("auxilio_apis")
        
        if state.get("needs_visualization"):
            if any(word in query for word in ["gráfico", "chart", "visualizar"]):
                selected_tools.append("graficos_basicos")
        
        state["mcp_tools_used"] = selected_tools
        return state
    
    def generate_sql(self, state: WorkflowState) -> WorkflowState:
        """Gera SQL usando a ConsultaTool existente"""
        try:
            # Usar a ConsultaTool existente que já tem toda a lógica
            query = state["query"]
            
            # Aplicar filtros e relacionamentos
            for k, v in self.factory.alias_filtros.items():
                query = query.replace(k, v)
            
            for rel in RELACIONAMENTOS_MCP:
                query = query.replace(rel[0], rel[1])
            
            # Gerar contexto melhorado com MCPs selecionados
            mcp_context = ""
            if state["mcp_tools_used"]:
                mcp_context = f"\nMCPs selecionados para esta consulta: {', '.join(state['mcp_tools_used'])}"
            
            contexto = f"""
            Você é um agente SQL para PostgreSQL integrado com MCPs. Gere uma consulta SQL válida:

            - Use tabelas completas com schema 'public'.
            - Sempre filtre pela empresa usando o campo apropriado que termina com '_empr'.
            - Todos os campos *_empr são do tipo integer e devem ser comparados com um valor numérico.
            - Nunca use variáveis tipo :pedi_empr, use somente o campo diretamente.

            RELACIONAMENTOS CORRETOS:
            - PedidosVenda.pedi_forn = Entidades.enti_clie (para clientes)
            - PedidosVenda.pedi_vend = Entidades.enti_clie (para vendedores)
            - Itenspedidovenda.iped_prod = Produtos.prod_codi
            - Itenspedidovenda.iped_pedi = PedidosVenda.pedi_nume

            FILTROS DE DATA:
            - Para mês: EXTRACT(MONTH FROM pedi_data) = 7
            - Para ano: EXTRACT(YEAR FROM pedi_data) = 2024

            Modelos disponíveis: {', '.join(m.__name__ for m in self.factory.models)}
            {mcp_context}

            Pergunta do usuário: {query}

            Retorne somente o código SQL, nada mais.
            """
            
            sql = self.llm.invoke(contexto).content.strip().strip("```sql").strip("```")
            state["sql_generated"] = sql
            
        except Exception as e:
            state["error"] = f"Erro na geração SQL: {str(e)}"
            logger.error(f"Erro na geração SQL: {e}")
        
        return state
    
    def execute_query(self, state: WorkflowState) -> WorkflowState:
        """Executa a query SQL gerada"""
        try:
            # Usar a ConsultaTool para executar
            result = self.consulta_tool.get_tool()(state["query"])
            state["final_response"] = result
            
            # Simular resultados estruturados para visualização
            state["db_results"] = [{"resultado": result}]
            
        except Exception as e:
            state["error"] = f"Erro na execução da query: {str(e)}"
            logger.error(f"Erro na execução: {e}")
        
        return state
    
    def check_visualization(self, state: WorkflowState) -> WorkflowState:
        """Verifica se precisa de visualização"""
        query = state["query"].lower()
        
        # Lógica para detectar necessidade de visualização
        viz_keywords = ["gráfico", "chart", "visualizar", "dashboard", "plotar"]
        state["needs_visualization"] = any(keyword in query for keyword in viz_keywords)
        
        if state["needs_visualization"]:
            # Determinar tipo de visualização
            if any(word in query for word in ["linha", "temporal", "tempo"]):
                state["visualization_type"] = "line"
            elif any(word in query for word in ["barra", "coluna"]):
                state["visualization_type"] = "bar"
            elif any(word in query for word in ["pizza", "pie"]):
                state["visualization_type"] = "pie"
            else:
                state["visualization_type"] = "bar"  # default
        
        return state
    
    def generate_visualization(self, state: WorkflowState) -> WorkflowState:
        """Gera visualização usando MCPs de visualização"""
        try:
            viz_prompt = f"""
            Baseado nos dados: {state['db_results']}
            Gere um código de visualização {state['visualization_type']} usando Chart.js.
            
            Retorne apenas o código JavaScript necessário.
            """
            
            viz_code = self.llm.invoke(viz_prompt).content
            state["final_response"] += f"\n\n📊 **Visualização gerada:**\n```javascript\n{viz_code}\n```"
            
        except Exception as e:
            logger.warning(f"Erro na geração de visualização: {e}")
        
        return state
    
    def format_response(self, state: WorkflowState) -> WorkflowState:
        """Formata a resposta final"""
        if not state.get("final_response"):
            state["final_response"] = "Não foi possível gerar uma resposta adequada."
        
        # Adicionar informações sobre MCPs usados
        if state["mcp_tools_used"]:
            state["final_response"] += f"\n\n🔧 **MCPs utilizados:** {', '.join(state['mcp_tools_used'])}"
        
        # Adicionar SQL gerado se disponível
        if state.get("sql_generated"):
            state["final_response"] += f"\n\n🧠 **SQL gerado:**\n```sql\n{state['sql_generated']}\n```"
        
        state["messages"].append(AIMessage(content=state["final_response"]))
        return state
    
    def handle_error(self, state: WorkflowState) -> WorkflowState:
        """Trata erros do workflow"""
        error_msg = state.get("error", "Erro desconhecido")
        state["final_response"] = f"❌ **Erro:** {error_msg}\n\nPor favor, reformule sua consulta ou verifique os dados."
        state["messages"].append(AIMessage(content=state["final_response"]))
        return state
    
    def _should_handle_error(self, state: WorkflowState) -> str:
        """Decide se deve tratar erro"""
        return "error" if state.get("error") else "success"
    
    def _should_visualize(self, state: WorkflowState) -> str:
        """Decide se deve gerar visualização"""
        return "visualize" if state.get("needs_visualization") else "format"
    
    def run(self, query: str) -> str:
        """Executa o workflow completo"""
        initial_state = WorkflowState(
            messages=[],
            query=query,
            sql_generated="",
            db_results=[],
            mcp_tools_used=[],
            final_response="",
            error="",
            needs_visualization=False,
            visualization_type=""
        )
        
        try:
            final_state = self.workflow.invoke(initial_state)
            return final_state["final_response"]
        except Exception as e:
            logger.error(f"Erro no workflow: {e}")
            return f"❌ **Erro no workflow:** {str(e)}"

# Instância global do workflow
mcp_workflow = MCPLangGraphWorkflow()
