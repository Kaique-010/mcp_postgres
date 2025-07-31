"""
Debug direto do LLM para investigar por que está gerando SQL corrompido
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mcp_postgres_sps.settings')
django.setup()

def testar_llm_direto():
    """Testa o LLM diretamente para ver o que está acontecendo"""
    
    try:
        # Importar o LLM do sistema
        from .models import ModelFactory
        from langchain_openai import ChatOpenAI
        
        # Tentar obter a configuração do LLM
        print("🔍 INVESTIGANDO CONFIGURAÇÃO DO LLM")
        print("=" * 50)
        
        # Verificar se há variáveis de ambiente
        openai_key = os.environ.get('OPENAI_API_KEY')
        print(f"OPENAI_API_KEY definida: {'Sim' if openai_key else 'Não'}")
        if openai_key:
            print(f"Primeiros 10 chars: {openai_key[:10]}...")
        
        # Tentar criar LLM
        try:
            llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0.1,
                max_tokens=500
            )
            print("✅ LLM criado com sucesso")
        except Exception as e:
            print(f"❌ Erro ao criar LLM: {e}")
            return
        
        # Teste simples
        print("\n🧪 TESTE SIMPLES DO LLM")
        print("-" * 30)
        
        prompt_simples = "Responda apenas: SELECT 1"
        
        try:
            print(f"Enviando prompt: '{prompt_simples}'")
            resposta = llm.invoke(prompt_simples)
            print(f"Tipo da resposta: {type(resposta)}")
            print(f"Resposta completa: {resposta}")
            
            if hasattr(resposta, 'content'):
                print(f"Content: '{resposta.content}'")
                print(f"Content type: {type(resposta.content)}")
                print(f"Content length: {len(resposta.content)}")
                
                # Verificar caracteres
                content = resposta.content
                print("\n🔍 ANÁLISE DE CARACTERES:")
                for i, char in enumerate(content[:50]):  # Primeiros 50 chars
                    print(f"  [{i}]: '{char}' (ord: {ord(char)})")
                    
        except Exception as e:
            print(f"❌ Erro ao chamar LLM: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            
        # Teste com prompt SQL
        print("\n🧪 TESTE COM PROMPT SQL")
        print("-" * 30)
        
        prompt_sql = """
Você é um especialista em SQL PostgreSQL. Gere APENAS o código SQL para a pergunta.

TABELAS DISPONÍVEIS:
- public.pedidosvenda (pv) - campos: pedi_nume, pedi_tota, pedi_data, pedi_empr

REGRAS:
1. SEMPRE use WHERE pv.pedi_empr = 1
2. Para soma: SUM(campo)

PERGUNTA: total faturado

Resposta (APENAS SQL):"""
        
        try:
            print("Enviando prompt SQL...")
            resposta_sql = llm.invoke(prompt_sql)
            print(f"Resposta SQL: {resposta_sql}")
            
            if hasattr(resposta_sql, 'content'):
                content_sql = resposta_sql.content
                print(f"SQL Content: '{content_sql}'")
                
                # Verificar se há caracteres corrompidos
                print("\n🔍 VERIFICAÇÃO DE CORRUPÇÃO:")
                caracteres_suspeitos = ['ú', 'ó', 'ã', 'subooo', 'ssso']
                for suspeito in caracteres_suspeitos:
                    if suspeito in content_sql.lower():
                        print(f"  ⚠️ Encontrado: '{suspeito}'")
                
                # Verificar encoding
                try:
                    encoded = content_sql.encode('utf-8')
                    decoded = encoded.decode('utf-8')
                    print(f"  ✅ Encoding UTF-8 OK")
                except Exception as enc_error:
                    print(f"  ❌ Problema de encoding: {enc_error}")
                    
        except Exception as e:
            print(f"❌ Erro no teste SQL: {e}")
            
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    testar_llm_direto()
