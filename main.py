import uvicorn
from mcp_postgres_sps.server import criar_app


app = criar_app()

if __name__ == "__main__":
    uvicorn.run("mcp_postgres_sps.main:app", host="0.0.0.0", port=8000, reload=True)
