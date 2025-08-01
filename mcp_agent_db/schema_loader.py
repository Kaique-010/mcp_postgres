"""
Função para carregar schema
"""

import json
import os
from typing import Dict, Optional

def carregar_schema(slug: str) -> Optional[Dict]:
    """
    Carrega schema de um cliente específico
    
    Args:
        slug: Identificador do cliente (ex: 'cliente_abc', 'spartacus')
        
    Returns:
        Dict com schema ou None se não encontrado
    """
    caminho = f"schemas/{slug}.json"
    
    try:
        if not os.path.exists(caminho):
            print(f"⚠️ Schema não encontrado: {caminho}")
            return None
            
        with open(caminho, "r", encoding="utf-8") as f:
            schema = json.load(f)
            print(f"✅ Schema carregado: {slug} ({len(schema)} tabelas)")
            return schema
            
    except json.JSONDecodeError as e:
        print(f"❌ Erro ao decodificar JSON: {e}")
        return None
    except Exception as e:
        print(f"❌ Erro ao carregar schema: {e}")
        return None

def listar_schemas_disponiveis() -> list:
    """
    Lista todos os schemas disponíveis no diretório schemas/
    
    Returns:
        Lista com nomes dos schemas (sem extensão .json)
    """
    schemas_dir = "schemas"
    
    if not os.path.exists(schemas_dir):
        return []
    
    schemas = []
    for arquivo in os.listdir(schemas_dir):
        if arquivo.endswith('.json'):
            schemas.append(arquivo[:-5])  # Remove .json
    
    return schemas

def formatar_schema_para_prompt(schema: Dict) -> str:
    """
    Formata schema para uso em prompts do LLM
    
    Args:
        schema: Schema carregado do JSON
        
    Returns:
        String formatada para prompt
    """
    if not schema:
        return "Nenhum schema disponível"
    
    linhas = []
    linhas.append("TABELAS DISPONÍVEIS:")
    
    for tabela, info in schema.items():
        colunas = info.get('colunas', [])
        colunas_str = ", ".join([col['nome'] for col in colunas])
        linhas.append(f"- {tabela}: {colunas_str}")
    
    return "\n".join(linhas)