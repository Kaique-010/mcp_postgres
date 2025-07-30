from fastapi import FastAPI, Request
from .consulta_tool import ConsultaTool
from .model_registry import MODELS_MCP
from .relacionamento_registry import RELACIONAMENTOS_MCP
from .filtros_naturais import FILTROS_NATURAIS
from .model_tool_factory import ModelToolFactory
from .llm_config import llm

app = FastAPI()

factory = ModelToolFactory(
        slug="mcp",
        models=MODELS_MCP,
        relacionamentos=RELACIONAMENTOS_MCP,
        alias_filtros=FILTROS_NATURAIS
    )

consulta_tool = ConsultaTool(factory=factory, llm=llm)

@app.post("/api/consulta/")
async def consulta(request: Request):
    data = await request.json()
    query = data.get("query")
    if not query:
        return {"erro": "Campo 'query' é obrigatório"}
    
    resposta = consulta_tool.get_tool()(query)
    return {"response": resposta}
