import logging
import traceback
from typing import Dict, Any, Optional
from django.db import DatabaseError, IntegrityError
from django.core.exceptions import ValidationError
from langchain_core.exceptions import LangChainException

logger = logging.getLogger(__name__)

class MCPErrorHandler:
    """Tratamento centralizado de erros para o sistema MCP"""
    
    @staticmethod
    def handle_database_error(error: Exception, context: str = "") -> Dict[str, Any]:
        """Trata erros de banco de dados"""
        logger.error(f"Erro de banco de dados {context}: {error}")
        logger.error(traceback.format_exc())
        
        if isinstance(error, IntegrityError):
            return {
                "error_type": "integrity_error",
                "message": "Erro de integridade dos dados. Verifique se os dados estão corretos.",
                "user_message": "❌ **Erro:** Dados inconsistentes. Verifique as informações fornecidas.",
                "technical_details": str(error)
            }
        elif isinstance(error, DatabaseError):
            return {
                "error_type": "database_error", 
                "message": "Erro na conexão ou consulta ao banco de dados.",
                "user_message": "❌ **Erro:** Problema na consulta ao banco. Tente novamente em alguns instantes.",
                "technical_details": str(error)
            }
        else:
            return {
                "error_type": "unknown_db_error",
                "message": f"Erro desconhecido no banco: {error}",
                "user_message": "❌ **Erro:** Problema inesperado no banco de dados.",
                "technical_details": str(error)
            }
    
    @staticmethod
    def handle_validation_error(error: ValidationError, context: str = "") -> Dict[str, Any]:
        """Trata erros de validação"""
        logger.warning(f"Erro de validação {context}: {error}")
        
        return {
            "error_type": "validation_error",
            "message": f"Dados inválidos: {error}",
            "user_message": f"❌ **Erro de validação:** {error}",
            "technical_details": str(error)
        }
    
    @staticmethod
    def handle_llm_error(error: Exception, context: str = "") -> Dict[str, Any]:
        """Trata erros do LLM/LangChain"""
        logger.error(f"Erro do LLM {context}: {error}")
        logger.error(traceback.format_exc())
        
        if "rate limit" in str(error).lower():
            return {
                "error_type": "rate_limit_error",
                "message": "Limite de requisições atingido",
                "user_message": "⏳ **Limite atingido:** Muitas consultas em pouco tempo. Aguarde alguns instantes e tente novamente.",
                "technical_details": str(error)
            }
        elif "timeout" in str(error).lower():
            return {
                "error_type": "timeout_error",
                "message": "Timeout na consulta ao LLM",
                "user_message": "⏱️ **Timeout:** A consulta demorou muito para processar. Tente uma consulta mais simples.",
                "technical_details": str(error)
            }
        else:
            return {
                "error_type": "llm_error",
                "message": f"Erro no processamento de linguagem: {error}",
                "user_message": "🤖 **Erro do AI:** Problema no processamento da consulta. Reformule sua pergunta.",
                "technical_details": str(error)
            }
    
    @staticmethod
    def handle_sql_error(error: Exception, sql: str = "", context: str = "") -> Dict[str, Any]:
        """Trata erros específicos de SQL"""
        logger.error(f"Erro SQL {context}: {error}")
        logger.error(f"SQL problemático: {sql}")
        
        error_str = str(error).lower()
        
        if "syntax error" in error_str:
            return {
                "error_type": "sql_syntax_error",
                "message": "Erro de sintaxe no SQL gerado",
                "user_message": "🔧 **Erro de sintaxe:** A consulta gerada tem problemas. Reformule sua pergunta de forma mais clara.",
                "technical_details": f"SQL: {sql}\nErro: {error}"
            }
        elif "column" in error_str and "does not exist" in error_str:
            return {
                "error_type": "column_not_found",
                "message": "Campo não encontrado na consulta",
                "user_message": "📋 **Campo inexistente:** Um dos campos mencionados não existe. Verifique os nomes utilizados.",
                "technical_details": f"SQL: {sql}\nErro: {error}"
            }
        elif "table" in error_str and "does not exist" in error_str:
            return {
                "error_type": "table_not_found",
                "message": "Tabela não encontrada",
                "user_message": "📊 **Tabela inexistente:** Uma das tabelas mencionadas não existe no banco.",
                "technical_details": f"SQL: {sql}\nErro: {error}"
            }
        else:
            return {
                "error_type": "sql_execution_error",
                "message": f"Erro na execução do SQL: {error}",
                "user_message": "⚠️ **Erro na consulta:** Problema na execução da consulta SQL. Tente reformular.",
                "technical_details": f"SQL: {sql}\nErro: {error}"
            }
    
    @staticmethod
    def handle_mcp_error(error: Exception, mcp_name: str = "", context: str = "") -> Dict[str, Any]:
        """Trata erros específicos dos MCPs"""
        logger.error(f"Erro MCP {mcp_name} {context}: {error}")
        
        return {
            "error_type": "mcp_error",
            "message": f"Erro no MCP {mcp_name}: {error}",
            "user_message": f"🔌 **Erro MCP:** Problema na integração com {mcp_name}. Continuando sem essa funcionalidade.",
            "technical_details": str(error)
        }
    
    @staticmethod
    def handle_generic_error(error: Exception, context: str = "") -> Dict[str, Any]:
        """Trata erros genéricos"""
        logger.error(f"Erro genérico {context}: {error}")
        logger.error(traceback.format_exc())
        
        return {
            "error_type": "generic_error",
            "message": f"Erro inesperado: {error}",
            "user_message": "❌ **Erro inesperado:** Algo deu errado. Tente novamente ou reformule sua consulta.",
            "technical_details": str(error)
        }
    
    @staticmethod
    def format_user_error(error_info: Dict[str, Any], include_details: bool = False) -> str:
        """Formata erro para exibição ao usuário"""
        message = error_info.get("user_message", "Erro desconhecido")
        
        if include_details and error_info.get("technical_details"):
            message += f"\n\n**Detalhes técnicos:**\n```\n{error_info['technical_details']}\n```"
        
        return message
    
    @staticmethod
    def should_retry(error_info: Dict[str, Any]) -> bool:
        """Determina se o erro permite retry"""
        retry_types = ["rate_limit_error", "timeout_error", "database_error"]
        return error_info.get("error_type") in retry_types
    
    @staticmethod
    def get_retry_delay(error_info: Dict[str, Any]) -> int:
        """Retorna delay em segundos para retry"""
        error_type = error_info.get("error_type")
        
        if error_type == "rate_limit_error":
            return 60  # 1 minuto
        elif error_type == "timeout_error":
            return 10  # 10 segundos
        elif error_type == "database_error":
            return 5   # 5 segundos
        else:
            return 0   # Sem retry

class ErrorRecovery:
    """Estratégias de recuperação de erros"""
    
    @staticmethod
    def suggest_query_alternatives(original_query: str, error_type: str) -> list:
        """Sugere alternativas de consulta baseado no erro"""
        suggestions = []
        
        if error_type == "sql_syntax_error":
            suggestions = [
                "Tente usar termos mais simples",
                "Evite caracteres especiais",
                "Use 'total de vendas' em vez de 'vendas totais'",
                "Especifique o período: 'vendas de janeiro'"
            ]
        elif error_type == "column_not_found":
            suggestions = [
                "Use 'cliente' em vez de 'comprador'",
                "Use 'produto' em vez de 'item'",
                "Use 'vendedor' em vez de 'representante'",
                "Use 'total faturado' em vez de 'faturamento'"
            ]
        elif error_type == "rate_limit_error":
            suggestions = [
                "Aguarde alguns instantes antes de fazer nova consulta",
                "Tente uma consulta mais simples",
                "Divida consultas complexas em partes menores"
            ]
        
        return suggestions
    
    @staticmethod
    def get_example_queries() -> list:
        """Retorna exemplos de consultas válidas"""
        return [
            "Total faturado este mês",
            "Quantidade de pedidos hoje",
            "Vendas por cliente",
            "Produtos mais vendidos",
            "Faturamento por vendedor",
            "Pedidos cancelados",
            "Total de itens vendidos"
        ]
