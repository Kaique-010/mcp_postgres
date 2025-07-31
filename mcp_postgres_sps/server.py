from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .consulta_tool import ConsultaTool
from .model_registry import MODELS_MCP
from .relacionamento_registry import RELACIONAMENTOS_MCP
from .filtros_naturais import FILTROS_NATURAIS
from .model_tool_factory import ModelToolFactory
from .llm_config import llm
from .langgraph_workflow import mcp_workflow
import logging
import traceback

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MCP Postgres SPS",
    description="Sistema de consultas SQL com integração LangChain/LangGraph e MCPs",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Manter compatibilidade com versão anterior
factory = ModelToolFactory(
        slug="mcp",
        models=MODELS_MCP,
        relacionamentos=RELACIONAMENTOS_MCP,
        alias_filtros=FILTROS_NATURAIS
    )

consulta_tool = ConsultaTool(factory=factory, llm=llm)

@app.get("/")
async def root():
    """Endpoint raiz com informações da API"""
    return {
        "message": "MCP Postgres SPS API",
        "version": "1.0.0",
        "endpoints": {
            "/api/consulta/": "Consulta tradicional (compatibilidade)",
            "/api/consulta-mcp/": "Consulta com workflow LangGraph + MCPs",
            "/api/health/": "Status da API"
        }
    }

@app.get("/api/health/")
async def health():
    """Endpoint de saúde da API"""
    return {"status": "healthy", "timestamp": "2025-01-30T19:00:00"}

@app.post("/api/consulta/")
async def consulta_tradicional(request: Request):
    """Endpoint tradicional mantido para compatibilidade"""
    try:
        data = await request.json()
        query = data.get("query")
        if not query:
            raise HTTPException(status_code=400, detail="Campo 'query' é obrigatório")
        
        logger.info(f"Consulta tradicional recebida: {query}")
        resposta = consulta_tool.get_tool()(query)
        
        return {
            "response": resposta,
            "method": "tradicional",
            "mcp_integrated": False
        }
    
    except Exception as e:
        logger.error(f"Erro na consulta tradicional: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.post("/api/consulta-mcp/")
async def consulta_com_mcp(request: Request):
    """Novo endpoint com workflow LangGraph integrado aos MCPs"""
    try:
        data = await request.json()
        query = data.get("query")
        use_visualization = data.get("visualization", False)
        
        if not query:
            raise HTTPException(status_code=400, detail="Campo 'query' é obrigatório")
        
        logger.info(f"Consulta MCP recebida: {query} (viz: {use_visualization})")
        
        # Executar workflow LangGraph
        resposta = mcp_workflow.run(query)
        
        return {
            "response": resposta,
            "method": "langgraph_mcp",
            "mcp_integrated": True,
            "workflow_completed": True
        }
    
    except Exception as e:
        logger.error(f"Erro na consulta MCP: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
