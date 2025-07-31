from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import django
from django.conf import settings
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import time

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from agente_inteligente_v2 import processar_pergunta_com_agente_v2, processar_pergunta_com_streaming_sync

app = FastAPI()

# Montar arquivos estáticos
app.mount("/static", StaticFiles(directory="."), name="static")

# Executor para rodar código síncrono em contexto assíncrono
executor = ThreadPoolExecutor(max_workers=4)

class PerguntaRequest(BaseModel):
    pergunta: str
    slug: str = "auto"

def executar_agente_sync(pergunta):
    """Função síncrona para executar o agente"""
    return processar_pergunta_com_agente_v2(pergunta)

def executar_agente_streaming_sync(pergunta):
    """Função síncrona para executar o agente com streaming"""
    return processar_pergunta_com_streaming_sync(pergunta)

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("templates/index.html", "r", encoding="utf-8") as file:
        return HTMLResponse(content=file.read())

# Rota específica para servir a logo
@app.get("/logo.png")
async def get_logo():
    from fastapi.responses import FileResponse
    return FileResponse("logo.png")

@app.post("/api/consulta")
async def consultar(request: PerguntaRequest):
    print(f"Recebido: {request.pergunta}")
    
    try:
        # Executar o agente em thread separada
        loop = asyncio.get_event_loop()
        resposta = await loop.run_in_executor(
            executor, 
            executar_agente_sync, 
            request.pergunta
        )
        
        print(f"Resposta do agente: {resposta}")
        
        return JSONResponse(content={"resposta": resposta})
        
    except Exception as e:
        print(f"Erro: {str(e)}")
        return JSONResponse(
            content={"resposta": f"Erro ao processar consulta: {str(e)}"}, 
            status_code=500
        )

async def stream_agente_response(pergunta: str):
    """
    Gerador que simula o streaming real da resposta do agente
    """
    try:
        # Enviar evento de início
        yield f"data: {json.dumps({'tipo': 'inicio', 'mensagem': f'🤖 Analisando: {pergunta}'})}\n\n"
        await asyncio.sleep(0.5)
        
        # Enviar etapas do processamento
        etapas = [
            "🧠 Entendendo a pergunta...",
            "🔍 Identificando dados necessários...",
            "🛠️ Preparando consulta SQL...",
            "📊 Executando no banco de dados...",
            "✨ Formatando resposta..."
        ]
        
        for i, etapa in enumerate(etapas, 1):
            yield f"data: {json.dumps({'tipo': 'etapa', 'numero': i, 'mensagem': etapa})}\n\n"
            await asyncio.sleep(0.8)
        
        # Executar o agente em thread separada
        loop = asyncio.get_event_loop()
        resposta_completa = await loop.run_in_executor(
            executor, 
            executar_agente_sync, 
            pergunta
        )
        
        # Simular streaming da resposta palavra por palavra
        yield f"data: {json.dumps({'tipo': 'resposta_inicio', 'mensagem': '📝 Gerando resposta...'})}\n\n"
        await asyncio.sleep(0.5)
        
        # Dividir a resposta em chunks para simular digitação
        palavras = resposta_completa.split()
        resposta_parcial = ""
        
        for i, palavra in enumerate(palavras):
            resposta_parcial += palavra + " "
            
            # Enviar chunk da resposta
            yield f"data: {json.dumps({'tipo': 'resposta_chunk', 'texto': resposta_parcial, 'progresso': (i+1)/len(palavras)*100})}\n\n"
            
            # Velocidade variável baseada no tamanho da palavra
            delay = 0.05 if len(palavra) < 5 else 0.1
            await asyncio.sleep(delay)
        
        # Enviar evento de conclusão
        yield f"data: {json.dumps({'tipo': 'concluido', 'resposta_final': resposta_completa})}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'tipo': 'erro', 'mensagem': f'❌ Erro: {str(e)}'})}\n\n"

@app.post("/api/consulta-streaming")
async def consultar_com_streaming_real(request: PerguntaRequest):
    """
    Streaming real usando Server-Sent Events
    """
    print(f"🎬 Iniciando streaming real: {request.pergunta}")
    
    return StreamingResponse(
        stream_agente_response(request.pergunta),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.post("/api/consulta-streaming-old")
async def consultar_com_streaming(request: PerguntaRequest):
    """
    Versão antiga do streaming (mantida para compatibilidade)
    """
    print(f"🎬 Iniciando consulta com streaming: {request.pergunta}")
    
    try:
        # Executar o agente com streaming em thread separada
        loop = asyncio.get_event_loop()
        resultado = await loop.run_in_executor(
            executor, 
            executar_agente_streaming_sync, 
            request.pergunta
        )
        
        print(f"✅ Streaming concluído: {resultado['status']}")
        
        return JSONResponse(content={
            "pergunta": resultado["pergunta"],
            "resposta": resultado["resposta"],
            "status": resultado["status"],
            "etapas_executadas": resultado["etapas_executadas"],
            "tipo": "streaming"
        })
        
    except Exception as e:
        print(f"❌ Erro no streaming: {str(e)}")
        return JSONResponse(
            content={
                "pergunta": request.pergunta,
                "resposta": f"Erro ao processar consulta com streaming: {str(e)}",
                "status": "erro",
                "etapas_executadas": 0,
                "tipo": "streaming"
            }, 
            status_code=500
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
