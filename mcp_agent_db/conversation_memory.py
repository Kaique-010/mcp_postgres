from typing import List, Dict, Any
from datetime import datetime

class ConversationMemory:
    def __init__(self, max_history: int = 10):
        self.history: List[Dict] = []
        self.context: Dict[str, Any] = {
            'empresa_atual': None,
            'filial_atual': None,
            'periodo_atual': None,
            'ultimo_resultado': None,
            'topico_atual': None
        }
        self.max_history = max_history
    
    def add_interaction(self, pergunta: str, resposta: str, sql: str = None, resultado: Any = None):
        """Adiciona interação ao histórico"""
        interaction = {
            'timestamp': datetime.now(),
            'pergunta': pergunta,
            'resposta': resposta,
            'sql': sql,
            'resultado': resultado
        }
        
        self.history.append(interaction)
        
        # Manter apenas as últimas N interações
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        # Atualizar contexto
        self._update_context(pergunta, resultado)
    
    def _update_context(self, pergunta: str, resultado: Any):
        """Atualiza contexto baseado na pergunta e resultado"""
        pergunta_lower = pergunta.lower()
        
        # Detectar tópicos
        if any(word in pergunta_lower for word in ['cliente', 'clientes']):
            self.context['topico_atual'] = 'clientes'
        elif any(word in pergunta_lower for word in ['vendedor', 'vendedores', 'funcionario']):
            self.context['topico_atual'] = 'vendedores'
        elif any(word in pergunta_lower for word in ['produto', 'produtos', 'estoque']):
            self.context['topico_atual'] = 'produtos'
        elif any(word in pergunta_lower for word in ['pedido', 'pedidos', 'venda']):
            self.context['topico_atual'] = 'pedidos'
        
        # Detectar filtros de empresa/filial
        if resultado and isinstance(resultado, list) and len(resultado) > 0:
            first_result = resultado[0]
            if 'empr' in str(first_result):
                # Extrair empresa do resultado
                for key, value in first_result.items():
                    if 'empr' in key.lower():
                        self.context['empresa_atual'] = value
                        break
        
        self.context['ultimo_resultado'] = resultado
    
    def get_context_prompt(self) -> str:
        """Gera prompt com contexto para o agente"""
        context_parts = []
        
        if self.context['topico_atual']:
            context_parts.append(f"Tópico atual: {self.context['topico_atual']}")
        
        if self.context['empresa_atual']:
            context_parts.append(f"Empresa em foco: {self.context['empresa_atual']}")
        
        if len(self.history) > 0:
            last_interaction = self.history[-1]
            context_parts.append(f"Última consulta: {last_interaction['pergunta'][:100]}...")
        
        if context_parts:
            return "\n\nCONTEXTO DA CONVERSA:\n" + "\n".join(f"- {part}" for part in context_parts)
        
        return ""
    
    def get_suggestions(self) -> List[str]:
        """Gera sugestões baseadas no contexto"""
        suggestions = []
        
        if self.context['topico_atual'] == 'clientes':
            suggestions.extend([
                "Quantos pedidos esses clientes fizeram?",
                "Qual o valor total de vendas para esses clientes?",
                "Mostre os vendedores desses clientes"
            ])
        elif self.context['topico_atual'] == 'produtos':
            suggestions.extend([
                "Qual o estoque desses produtos?",
                "Quantas vezes foram vendidos?",
                "Qual a margem de lucro?"
            ])
        elif self.context['topico_atual'] == 'pedidos':
            suggestions.extend([
                "Quais produtos foram mais vendidos?",
                "Qual vendedor fez mais vendas?",
                "Mostre o faturamento por período"
            ])
        
        return suggestions[:3]  # Máximo 3 sugestões

# Instância global da memória
conversation_memory = ConversationMemory()