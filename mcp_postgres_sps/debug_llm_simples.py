"""
Debug simples do LLM para investigar por que está gerando SQL corrompido
"""

import os

def testar_llm_simples():
    """Testa o LLM diretamente sem depender do Django"""
    
    print("🔍 INVESTIGANDO PROBLEMA DO LLM")
    print("=" * 50)
    
    # Verificar variáveis de ambiente
    openai_key = os.environ.get('OPENAI_API_KEY')
    print(f"OPENAI_API_KEY definida: {'Sim' if openai_key else 'Não'}")
    
    if not openai_key:
        print("❌ OPENAI_API_KEY não definida!")
        print("   Isso pode explicar por que o LLM está gerando respostas corrompidas.")
        print("   O LLM pode estar usando um modelo local ou mock que gera texto aleatório.")
        return
    
    print(f"Primeiros 10 chars da key: {openai_key[:10]}...")
    
    # Tentar importar e testar LLM
    try:
        from langchain_openai import ChatOpenAI
        print("✅ langchain_openai importado com sucesso")
        
        # Criar LLM
        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.1,
            max_tokens=100
        )
        print("✅ LLM criado com sucesso")
        
        # Teste simples
        print("\n🧪 TESTE SIMPLES")
        print("-" * 30)
        
        prompt_teste = "Responda apenas: SELECT 1"
        print(f"Prompt: '{prompt_teste}'")
        
        resposta = llm.invoke(prompt_teste)
        print(f"Tipo resposta: {type(resposta)}")
        
        if hasattr(resposta, 'content'):
            content = resposta.content
            print(f"Content: '{content}'")
            print(f"Length: {len(content)}")
            
            # Verificar caracteres suspeitos
            suspeitos = ['ú', 'ó', 'ã', 'subooo', 'ssso', 'uuosbsusb']
            encontrados = []
            for suspeito in suspeitos:
                if suspeito in content.lower():
                    encontrados.append(suspeito)
            
            if encontrados:
                print(f"⚠️ CARACTERES SUSPEITOS ENCONTRADOS: {encontrados}")
                print("   Isso confirma que o LLM está gerando texto corrompido!")
            else:
                print("✅ Nenhum caractere suspeito encontrado neste teste")
                
            # Análise de caracteres
            print("\n🔍 ANÁLISE DE CARACTERES (primeiros 20):")
            for i, char in enumerate(content[:20]):
                ascii_val = ord(char)
                status = "OK" if 32 <= ascii_val <= 126 else "SUSPEITO"
                print(f"  [{i}]: '{char}' (ASCII: {ascii_val}) - {status}")
        
        # Teste com prompt SQL
        print("\n🧪 TESTE COM PROMPT SQL")
        print("-" * 30)
        
        prompt_sql = """Gere SQL para: total faturado
        
Tabela: public.pedidosvenda (pv)
Campos: pedi_tota, pedi_empr

Resposta:"""
        
        print("Enviando prompt SQL...")
        resposta_sql = llm.invoke(prompt_sql)
        
        if hasattr(resposta_sql, 'content'):
            sql_content = resposta_sql.content
            print(f"SQL gerado: '{sql_content}'")
            
            # Verificar se é SQL válido ou corrompido
            if any(suspeito in sql_content.lower() for suspeito in suspeitos):
                print("❌ SQL CORROMPIDO DETECTADO!")
                print("   O LLM está definitivamente gerando texto corrompido.")
            elif 'select' in sql_content.lower():
                print("✅ SQL aparentemente válido gerado")
            else:
                print("⚠️ Resposta não parece ser SQL")
                
    except ImportError as e:
        print(f"❌ Erro ao importar langchain_openai: {e}")
        print("   Verifique se a biblioteca está instalada.")
    except Exception as e:
        print(f"❌ Erro ao testar LLM: {e}")
        print("   Isso pode explicar por que o LLM gera respostas corrompidas.")

def analisar_logs_sistema():
    """Analisa possíveis causas do problema"""
    print("\n🔍 ANÁLISE DE POSSÍVEIS CAUSAS")
    print("=" * 50)
    
    causas_possiveis = [
        "1. OPENAI_API_KEY inválida ou expirada",
        "2. Problema de rede/conectividade com OpenAI",
        "3. Modelo LLM configurado incorretamente",
        "4. Problema de encoding na comunicação",
        "5. LLM usando modelo local/mock que gera texto aleatório",
        "6. Limite de tokens/rate limit atingido",
        "7. Versão incompatível da biblioteca langchain"
    ]
    
    for causa in causas_possiveis:
        print(f"  {causa}")
    
    print("\n💡 RECOMENDAÇÕES:")
    print("  • Verificar se OPENAI_API_KEY está correta")
    print("  • Testar conectividade com OpenAI")
    print("  • Verificar logs de erro do Django")
    print("  • Considerar usar modelo local como fallback")

if __name__ == "__main__":
    testar_llm_simples()
    analisar_logs_sistema()
