from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from mcp_postgres_sps.consulta_tool import ConsultaMCPTool
from mcp_postgres_sps.prompts_agents import agent_consulta_banco
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
load_dotenv()
import os


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class ConsultaRequest(BaseModel):
    query: str

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/consulta")
async def process_prompt(prompt: ConsultaRequest):
    try:
        user_question = prompt.query.strip()
    except Exception as e:
        return JSONResponse(content={"resposta": f"❌ Erro: {str(e)}"})

    # Usar a tool corretamente - ela já é decorada com @tool
    tools = [ConsultaMCPTool]
    model = init_chat_model("google_genai:gemini-2.0-flash")
    memoria = MemorySaver()

    agente = create_react_agent(
        tools=tools,
        model=model,
        prompt=agent_consulta_banco,
        checkpointer=memoria,
    )

    config = {"configurable": {"thread_id": "consulta"}}
    # ATENÇÃO: mensagem no formato correto para prompt string simples
    mensagem_usuario = {
        "messages": [
            {"role": "user", "content": user_question}
        ]
    }

    resposta = ""
    async for step in agente.astream(mensagem_usuario, config, stream_mode="values"):
        resposta += step["messages"][-1].content

    return JSONResponse(content={"resposta": resposta})
    print("GOOGLE_API_KEY:", os.getenv("GOOGLE_API_KEY"))
print("DATABASE_URL_EMPRESA_1:", os.getenv("DATABASE_URL_EMPRESA_1"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
