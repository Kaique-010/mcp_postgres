# mcp_servers.py
import os
from dotenv import load_dotenv

load_dotenv()

SMITHERY_API_KEY = os.getenv("SMITHERY_API_KEY")
if not SMITHERY_API_KEY:
    raise ValueError("SMITHERY_API_KEY não definida no ambiente.")

# Configurações originais dos MCP servers
MCP_SERVERS_CONFIG = {
    'passos_sequenciais': {
        'url': f'https://server.smithery.ai/@xinzhongyouhai/mcp-sequentialthinking-tools/mcp?api_key={SMITHERY_API_KEY}&profile=liable-rhinoceros-zBrJHu',
        'transport': 'streamable_http',
    },
    'buscas_relevantes': {
        'url': f'https://server.smithery.ai/@nickclyde/duckduckgo-mcp-server/mcp?api_key={SMITHERY_API_KEY}&profile=liable-rhinoceros-zBrJHu',
        'transport': 'streamable_http',
    },
    'auxilio_apis': {
        'url': f'https://server.smithery.ai/@upstash/context7-mcp/mcp?api_key={SMITHERY_API_KEY}&profile=liable-rhinoceros-zBrJHu',
        'transport': 'streamable_http',
    },
}

# Configurações para MCP Tools de Visualização
MCP_VISUALIZATION_CONFIG = {
    "graficos_basicos": {
        "chart_js_generator": {
            "url": f"https://server.smithery.ai/@chartjs/chartjs-mcp/mcp?api_key={SMITHERY_API_KEY}&profile=liable-rhinoceros-zBrJHu",
            "transport": "streamable_http",
        },
        "matplotlib_generator": {
            "url": f"https://server.smithery.ai/@matplotlib/matplotlib-mcp/mcp?api_key={SMITHERY_API_KEY}&profile=liable-rhinoceros-zBrJHu",
            "transport": "streamable_http",
        },
    },
    "graficos_interativos": {
        "plotly_generator": {
            "url": f"https://server.smithery.ai/@plotly/plotly-mcp/mcp?api_key={SMITHERY_API_KEY}&profile=liable-rhinoceros-zBrJHu",
            "transport": "streamable_http",
        },
        "d3_generator": {
            "url": f"https://server.smithery.ai/@d3js/d3-visualization-mcp/mcp?api_key={SMITHERY_API_KEY}&profile=liable-rhinoceros-zBrJHu",
            "transport": "streamable_http",
        },
    },
    "dashboards": {
        "dashboard_generator": {
            "url": f"https://server.smithery.ai/@dashboard/dashboard-mcp/mcp?api_key={SMITHERY_API_KEY}&profile=liable-rhinoceros-zBrJHu",
            "transport": "streamable_http",
        },
    },
    "exports": {
        "pdf_chart_export": {
            "url": f"https://server.smithery.ai/@export/pdf-chart-mcp/mcp?api_key={SMITHERY_API_KEY}&profile=liable-rhinoceros-zBrJHu",
            "transport": "streamable_http",
        },
        "image_export": {
            "url": f"https://server.smithery.ai/@export/image-export-mcp/mcp?api_key={SMITHERY_API_KEY}&profile=liable-rhinoceros-zBrJHu",
            "transport": "streamable_http",
        },
    }
}

# Configuração completa de desenvolvimento (seus MCP_DEV_CONFIG originais + visualização)
MCP_DEV_CONFIG = {
    "backend": {
        "django_boilerplate": {
            "url": f"https://server.smithery.ai/@smithery/toolbox/mcp?api_key={SMITHERY_API_KEY}&profile=liable-rhinoceros-zBrJHu",
            "transport": "streamable_http",
        },
        "codigo_ajustado": {
           'url': f'https://server.smithery.ai/@upstash/context7-mcp/mcp?api_key={SMITHERY_API_KEY}&profile=liable-rhinoceros-zBrJHu',
           'transport': 'streamable_http',
        },
    },
    "frontend": {
        "react_native_scaffold": {
            "url": f"https://server.smithery.ai/@seu-usuario/react-native-scaffold/mcp?api_key={SMITHERY_API_KEY}&profile=liable-rhinoceros-zBrJHu",
            "transport": "streamable_http",
        },
        "gerador_snippet": {
            "url": f"https://server.smithery.ai/@Yaxin9Luo/openai_agent_library_mcp/mcp?api_key={SMITHERY_API_KEY}&profile=liable-rhinoceros-zBrJHu",
            "transport": "streamable_http",
        },
    },
    "refatoracao": {
        "codigo_ajustado": {
           'url': f'https://server.smithery.ai/@upstash/context7-mcp/mcp?api_key={SMITHERY_API_KEY}&profile=liable-rhinoceros-zBrJHu',
           'transport': 'streamable_http',
        },
        "avaliador_codigo": {
            'url': f'https://server.smithery.ai/@upstash/context7-mcp/mcp?api_key={SMITHERY_API_KEY}&profile=liable-rhinoceros-zBrJHu',
            'transport': 'streamable_http',  
        },
    },
    "explicacao": {
        "explicador_codigo": {
           'url': f'https://server.smithery.ai/@upstash/context7-mcp/mcp?api_key={SMITHERY_API_KEY}&profile=liable-rhinoceros-zBrJHu',
           'transport': 'streamable_http',
        }
    },
    "debug": {
        "busca_stackoverflow": {
            "url": f"https://server.smithery.ai/@nickclyde/duckduckgo-mcp-server/mcp?api_key={SMITHERY_API_KEY}&profile=liable-rhinoceros-zBrJHu",
            "transport": "streamable_http",
        }
    },
    "snippet": {
        "busca_stackoverflow": {
            "url": f"https://server.smithery.ai/@nickclyde/duckduckgo-mcp-server/mcp?api_key={SMITHERY_API_KEY}&profile=liable-rhinoceros-zBrJHu",
            "transport": "streamable_http",
        }
    },
    "geral": {
        "codigo_ajustado": {
            'url': f'https://server.smithery.ai/@xinzhongyouhai/mcp-sequentialthinking-tools/mcp?api_key={SMITHERY_API_KEY}&profile=liable-rhinoceros-zBrJHu',
            'transport': 'streamable_http',
        },
        "explicador_codigo": {
           'url': f'https://server.smithery.ai/@upstash/context7-mcp/mcp?api_key={SMITHERY_API_KEY}&profile=liable-rhinoceros-zBrJHu',
           'transport': 'streamable_http',
        },
    },
    # Adiciona as configurações de visualização ao MCP_DEV_CONFIG
    "visualizacao": MCP_VISUALIZATION_CONFIG
}