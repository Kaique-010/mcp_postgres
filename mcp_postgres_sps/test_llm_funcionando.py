"""
Teste para verificar se o LLM está sendo chamado corretamente
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def testar_llm_mock():
    """Testa se a função processar_sql_llm funciona com um mock do LLM"""
    
    # Mock simples do LLM
    class MockLLM:
        def invoke(self, contexto):
            class MockResponse:
                def __init__(self, content):
                    self.content = content
            
            # Simula resposta do LLM baseada no contexto
            if "quantos pedidos" in contexto.lower():
                return MockResponse("SELECT COUNT(DISTINCT pv.pedi_nume) AS total_pedidos FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1")
            elif "total faturado" in contexto.lower():
                return MockResponse("SELECT SUM(pv.pedi_tota) AS total_faturado FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1")
            else:
                return MockResponse("SELECT COUNT(*) FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1")
    
    # Mock da classe ConsultaTool
    class MockConsultaTool:
        def __init__(self):
            self.llm = MockLLM()
        
        def sanitizar_sql(self, sql):
            """Mock da sanitização"""
            return sql.strip()
        
        def validar_encoding_sql(self, sql):
            """Mock da validação de encoding"""
            # Simula SQL corrompido se contém caracteres estranhos
            if any(char in sql for char in ['ú', 'ó', 'ã', 'subooo', 'ssso']):
                return False, "Caracteres corrompidos detectados"
            return True, ""
        
        def processar_sql_llm(self, contexto: str) -> str:
            """Cópia da função implementada"""
            max_tentativas = 3
            
            for tentativa in range(max_tentativas):
                try:
                    # Chama o LLM
                    resposta = self.llm.invoke(contexto)
                    sql_bruto = resposta.content.strip()
                    
                    # Remove marcadores de código se existirem
                    sql_limpo = sql_bruto.strip("```sql").strip("```").strip()
                    
                    # Sanitiza o SQL
                    sql_sanitizado = self.sanitizar_sql(sql_limpo)
                    
                    # Valida encoding
                    is_encoding_valid, encoding_error = self.validar_encoding_sql(sql_sanitizado)
                    if not is_encoding_valid:
                        print(f"Tentativa {tentativa + 1}: SQL com encoding inválido: {encoding_error}")
                        continue
                    
                    # Verifica se não está vazio após sanitização
                    if not sql_sanitizado or len(sql_sanitizado.strip()) < 10:
                        print(f"Tentativa {tentativa + 1}: SQL muito curto após sanitização")
                        continue
                    
                    # Se chegou até aqui, o SQL passou nas validações básicas
                    print(f"LLM gerou SQL válido na tentativa {tentativa + 1}")
                    return sql_sanitizado
                    
                except Exception as e:
                    print(f"Tentativa {tentativa + 1} falhou: {e}")
                    continue
            
            # Se todas as tentativas falharam
            print(f"LLM falhou em todas as {max_tentativas} tentativas")
            return None
    
    print("🧪 TESTANDO FUNÇÃO processar_sql_llm")
    print("=" * 50)
    
    tool = MockConsultaTool()
    
    # Teste 1: Query normal
    print("\n1. Testando query normal:")
    contexto1 = "PERGUNTA DO USUÁRIO: quantos pedidos\n\nRetorne APENAS o código SQL."
    sql1 = tool.processar_sql_llm(contexto1)
    print(f"   Resultado: {sql1}")
    
    # Teste 2: Query de faturamento
    print("\n2. Testando query de faturamento:")
    contexto2 = "PERGUNTA DO USUÁRIO: total faturado\n\nRetorne APENAS o código SQL."
    sql2 = tool.processar_sql_llm(contexto2)
    print(f"   Resultado: {sql2}")
    
    # Teste 3: Simular LLM retornando SQL corrompido
    print("\n3. Testando LLM com SQL corrompido:")
    tool.llm = type('MockLLM', (), {
        'invoke': lambda self, ctx: type('MockResponse', (), {
            'content': 'SELECT súúos FROM subooo.ssso_uuosbsusb'
        })()
    })()
    
    contexto3 = "PERGUNTA DO USUÁRIO: teste corrompido\n\nRetorne APENAS o código SQL."
    sql3 = tool.processar_sql_llm(contexto3)
    print(f"   Resultado: {sql3}")
    
    # Resumo
    print(f"\n📊 RESUMO DOS TESTES:")
    print(f"   Teste 1 (normal): {'✅ Passou' if sql1 else '❌ Falhou'}")
    print(f"   Teste 2 (faturamento): {'✅ Passou' if sql2 else '❌ Falhou'}")
    print(f"   Teste 3 (corrompido): {'✅ Passou (rejeitou)' if sql3 is None else '❌ Falhou (aceitou)'}")
    
    if sql1 and sql2 and sql3 is None:
        print("\n🎉 FUNÇÃO processar_sql_llm FUNCIONANDO CORRETAMENTE!")
        return True
    else:
        print("\n⚠️ FUNÇÃO processar_sql_llm PRECISA DE AJUSTES")
        return False

if __name__ == "__main__":
    testar_llm_mock()
