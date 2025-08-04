from setuptools import setup, find_packages
import os

# Ler requirements.txt e extrair dependÃªncias
def read_requirements():
    requirements = []
    try:
        with open('requirements.txt', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Limpar caracteres especiais que podem estar no arquivo
                    clean_line = ''.join(char for char in line if ord(char) < 128)
                    if '==' in clean_line:
                        requirements.append(clean_line)
    except:
        # Fallback para dependÃªncias essenciais
        requirements = [
            'Django>=3.2.0',
            'fastapi>=0.100.0',
            'langchain>=0.3.0',
            'langchain-core>=0.3.0',
            'langchain-google-genai>=2.0.0',
            'psycopg2-binary>=2.9.0',
            'python-dotenv>=1.0.0',
            'uvicorn>=0.30.0',
            'pydantic>=2.0.0',
            'requests>=2.30.0'
        ]
    return requirements

# Ler descriÃ§Ã£o longa
long_description = """
# MCP Agent DB

Uma ferramenta poderosa para consulta de bases de dados usando linguagem natural.

## CaracterÃ­sticas

- ðŸ¤– **Agente Inteligente**: Converte perguntas em linguagem natural para SQL
- ðŸ” **Consultas AvanÃ§adas**: Suporte para consultas complexas com joins e agregaÃ§Ãµes
- ðŸ“Š **GeraÃ§Ã£o de GrÃ¡ficos**: IntegraÃ§Ã£o com ferramentas MCP para visualizaÃ§Ã£o
- ðŸ¢ **Multi-empresa**: Suporte para mÃºltiplas empresas e filiais
- ðŸ’¾ **Cache Inteligente**: Sistema de cache para otimizar performance
- ðŸ”„ **MemÃ³ria de ConversaÃ§Ã£o**: MantÃ©m contexto entre consultas

## InstalaÃ§Ã£o

```bash
pip install mcp-agent-db
```

## Uso BÃ¡sico

```python
from mcp_agent_db import consultar_banco_dados

resultado = consultar_banco_dados("TOP 10 clientes que mais compraram", "minha_empresa")
print(resultado)
```

## API REST

O pacote inclui uma API REST completa para integraÃ§Ã£o com aplicaÃ§Ãµes web e mobile.

```python
from mcp_agent_db.main import app
import uvicorn

uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Endpoints Principais

- `POST /api/consulta` - Realizar consultas em linguagem natural
- `GET /api/schemas` - Listar schemas disponÃ­veis
- `POST /api/grafico` - Gerar grÃ¡ficos a partir dos dados

## Suporte

Para mais informaÃ§Ãµes, visite: https://github.com/leokaique/mcp-agent-db
"""

setup(
    name='mcp-agent-db',
    version='1.0.8',
    author='Leonardo Sousa',
    author_email='leokaique7@gmail.com',
    description='Ferramenta de consulta de bases de dados usando linguagem natural com agente inteligente',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/leokaique/mcp-agent-db',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'mcp_agent_db': [
            'templates/*.html',
            'static/*.png',
            'schemas/*.json',
            '*.py'
        ],
    },
    install_requires=read_requirements(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Database",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
    keywords='database, natural language, sql, ai, agent, langchain, mcp',
    entry_points={
        'console_scripts': [
            'mcp-agent-db=mcp_agent_db.main:main',
        ],
    },
    project_urls={
        'Bug Reports': 'https://github.com/leokaique/mcp-agent-db/issues',
        'Source': 'https://github.com/leokaique/mcp-agent-db',
        'Documentation': 'https://github.com/leokaique/mcp-agent-db/wiki',
    },
)




