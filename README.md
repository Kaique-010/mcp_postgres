# MCP Postgres SPS

Agente inteligente que responde perguntas em linguagem natural sobre o banco PostgreSQL usando Django e LangChain.

## 🔧 Instalação

```bash
git clone https://seurepo.com/mcp_postgres_sps.git
cd mcp_postgres_sps
docker build -t mcp-postgres .
docker run -p 8000:8000 mcp-postgres
```

Como usar
Faça requisições POST para:

css
Copiar
Editar
POST /consulta

Body:
{
"pergunta": "quantos pedidos tivemos no mês de julho?",
"slug": "empresa_xyz"
}

mcp_postgres_sps/
├── mcp_postgres_sps/
│ ├── **init**.py
│ ├── consulta_tool.py
│ ├── filtros_naturais.py
│ ├── model_registry.py
│ ├── model_tool_factory.py
│ ├── relacionamento_registry.py
│ └── server.py
├── main.py
├── Dockerfile
├── requirements.txt
├── README.md

#   m c p _ p o s t g r e s  
 